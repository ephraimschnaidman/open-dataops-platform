import logging
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform" / "jobs"))
sys.path.insert(0, str(ROOT / "platform" / "context"))

from render_incident_context import (  # noqa: E402
    render_recommended_next_step, render_what_happened, render_why_it_matters,
)
from generate_incident_context import (  # noqa: E402
    IncidentNotFoundError, UnsupportedIncidentTypeError, configure_logging,
    generate_contexts, persist_context,
)
from incident_context_rules import (  # noqa: E402
    IncidentContextRuleError, IncidentMetadata, RECOMMENDED_ACTION_CODE,
    evaluate_freshness, generate_stale_data_context, parse_freshness_hours,
)

NOW = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
INCIDENT_ID = uuid.UUID("4b675a14-44c6-4836-8dc5-e16befc2f6e7")


def stale_incident(**overrides):
    values = dict(incident_type="STALE_DATA", severity="HIGH", table_schema="raw",
                  table_name="orders", expected_value="<= 48 hours",
                  observed_value="11425.30 hours", incident_status="OPEN")
    values.update(overrides)
    return IncidentMetadata(**values)


def incident_row(**overrides):
    i = stale_incident(**overrides)
    return (INCIDENT_ID, i.incident_type, i.severity, i.table_schema, i.table_name,
            i.expected_value, i.observed_value, i.incident_status)


class FakeResult:
    def __init__(self, rows): self.rows = rows
    def fetchall(self): return self.rows
    def fetchone(self): return self.rows[0] if self.rows else (True,)


class FakeConnection:
    def __init__(self, rows=None):
        self.rows = [] if rows is None else rows
        self.executions = []
    def execute(self, statement, parameters):
        self.executions.append((statement, parameters))
        return FakeResult(self.rows if statement.lstrip().startswith("SELECT") else [])


class RuleTests(unittest.TestCase):
    def test_parsing(self):
        self.assertEqual(parse_freshness_hours("<= 48 hours"), Decimal("48"))
        self.assertEqual(parse_freshness_hours("12388.62 hours"), Decimal("12388.62"))
        for malformed in (None, "", "yesterday", "-2 hours", "48 days"):
            self.assertIsNone(parse_freshness_hours(malformed))

    def test_statuses(self):
        self.assertEqual(evaluate_freshness(Decimal("48"), Decimal("49")), "EXCEEDED_THRESHOLD")
        self.assertEqual(evaluate_freshness(Decimal("48"), Decimal("48")), "WITHIN_THRESHOLD")
        self.assertEqual(evaluate_freshness(None, Decimal("48")), "UNKNOWN")

    def test_structured_context(self):
        context = generate_stale_data_context(stale_incident())
        self.assertEqual(context.qualified_table, "raw.orders")
        self.assertEqual(context.evaluation_status, "EXCEEDED_THRESHOLD")
        self.assertEqual(context.recommended_action_code, RECOMMENDED_ACTION_CODE)
        self.assertEqual(context, generate_stale_data_context(stale_incident()))

    def test_required_metadata_and_type_are_validated(self):
        with self.assertRaisesRegex(IncidentContextRuleError, "Unsupported incident type"):
            generate_stale_data_context(stale_incident(incident_type="COLUMN_ADDED"))
        with self.assertRaisesRegex(IncidentContextRuleError, "table_schema"):
            generate_stale_data_context(stale_incident(table_schema=""))


class RendererTests(unittest.TestCase):
    def test_deterministic_safe_rendering(self):
        context = generate_stale_data_context(stale_incident())
        rendered = (render_what_happened(context), render_why_it_matters(context),
                    render_recommended_next_step(context))
        self.assertEqual(rendered, (render_what_happened(context), render_why_it_matters(context),
                                    render_recommended_next_step(context)))
        self.assertEqual(rendered[0], "The freshness threshold for raw.orders was exceeded. Expected <= 48 hours; observed 11425.30 hours.")
        combined = " ".join(rendered).lower()
        for claim in ("root cause", "owner", "business impact", "downstream"):
            self.assertNotIn(claim, combined)


class JobTests(unittest.TestCase):
    def test_missing_and_unsupported_incidents(self):
        with self.assertRaises(IncidentNotFoundError):
            generate_contexts(FakeConnection(), INCIDENT_ID, NOW)
        with self.assertRaises(UnsupportedIncidentTypeError):
            generate_contexts(FakeConnection([incident_row(incident_type="COLUMN_ADDED")]), INCIDENT_ID, NOW)

    def test_persist_is_structured_and_idempotent(self):
        connection = FakeConnection()
        context = generate_stale_data_context(stale_incident())
        first = persist_context(connection, INCIDENT_ID, context, NOW)
        second = persist_context(connection, INCIDENT_ID, context, NOW)
        self.assertEqual(first, second)
        sql, params = connection.executions[0]
        self.assertIn("ON CONFLICT (incident_id, context_version)", sql)
        self.assertIn("generated_at = EXCLUDED.generated_at", sql)
        self.assertIn("updated_at = CURRENT_TIMESTAMP", sql)
        self.assertNotIn("created_at =", sql)
        self.assertNotIn("what_happened", sql)
        self.assertEqual(params[3:9], ("raw.orders", "EXCEEDED_THRESHOLD", "HIGH",
                                      Decimal("48"), Decimal("11425.30"), RECOMMENDED_ACTION_CODE))

    def test_bulk_load_filter(self):
        connection = FakeConnection([incident_row()])
        generate_contexts(connection, None, NOW)
        self.assertEqual(connection.executions[0][1], ("STALE_DATA", "OPEN"))

    def test_rotating_logging_configuration(self):
        root = logging.getLogger()
        old_handlers = root.handlers[:]
        root.handlers.clear()
        try:
            with tempfile.TemporaryDirectory() as directory:
                configure_logging(Path(directory) / "incident_context.log")
                handler = next(h for h in root.handlers if isinstance(h, TimedRotatingFileHandler))
                self.assertEqual(handler.backupCount, 30)
                self.assertEqual(handler.encoding.lower().replace("-", ""), "utf8")
        finally:
            for handler in root.handlers: handler.close()
            root.handlers[:] = old_handlers


if __name__ == "__main__":
    unittest.main()
