import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform" / "jobs"))

from generate_incident_context import (  # noqa: E402
    IncidentNotFoundError,
    UnsupportedIncidentTypeError,
    generate_contexts,
    persist_context,
)
from incident_context_rules import (  # noqa: E402
    IncidentContextRuleError,
    IncidentMetadata,
    generate_stale_data_context,
)

NOW = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
INCIDENT_ID = uuid.UUID("4b675a14-44c6-4836-8dc5-e16befc2f6e7")


def stale_incident(**overrides):
    values = {
        "incident_type": "STALE_DATA",
        "severity": "HIGH",
        "table_schema": "raw",
        "table_name": "orders",
        "expected_value": "<= 48 hours",
        "observed_value": "11425.30 hours",
        "incident_status": "OPEN",
    }
    values.update(overrides)
    return IncidentMetadata(**values)


def incident_row(**overrides):
    incident = stale_incident(**overrides)
    return (
        INCIDENT_ID, incident.incident_type, incident.severity, incident.table_schema,
        incident.table_name, incident.expected_value, incident.observed_value,
        incident.incident_status,
    )


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows=None):
        self.rows = [] if rows is None else rows
        self.executions = []

    def execute(self, statement, parameters):
        self.executions.append((statement, parameters))
        return FakeResult(self.rows if statement.lstrip().startswith("SELECT") else [])


class IncidentContextRuleTests(unittest.TestCase):
    def test_stale_data_context_generation_is_deterministic(self):
        first = generate_stale_data_context(stale_incident())
        second = generate_stale_data_context(stale_incident())
        self.assertEqual(first, second)
        self.assertEqual(first.context_version, "stale_data_v1")

    def test_context_contains_values_severity_and_safe_language(self):
        context = generate_stale_data_context(stale_incident())
        self.assertIn("Expected <= 48 hours", context.what_happened)
        self.assertIn("observed 11425.30 hours", context.what_happened)
        self.assertIn("HIGH severity", context.why_it_matters)
        self.assertIn("raw.orders", context.what_happened)
        combined = " ".join((context.what_happened, context.why_it_matters,
                             context.recommended_next_step)).lower()
        for unsupported_claim in ("root cause", "owner", "business impact", "downstream"):
            self.assertNotIn(unsupported_claim, combined)
        self.assertTrue(context.recommended_next_step.startswith("Investigate"))

    def test_unsupported_incident_type_is_rejected(self):
        with self.assertRaisesRegex(IncidentContextRuleError, "Unsupported incident type"):
            generate_stale_data_context(stale_incident(incident_type="ROW_COUNT_DECREASE"))


class IncidentContextJobTests(unittest.TestCase):
    def test_missing_incident_is_rejected(self):
        with self.assertRaisesRegex(IncidentNotFoundError, "was not found"):
            generate_contexts(FakeConnection(), INCIDENT_ID, NOW)

    def test_requested_unsupported_incident_is_rejected(self):
        connection = FakeConnection([incident_row(incident_type="COLUMN_ADDED")])
        with self.assertRaisesRegex(UnsupportedIncidentTypeError, "unsupported type"):
            generate_contexts(connection, INCIDENT_ID, NOW)

    def test_generation_persists_context(self):
        connection = FakeConnection([incident_row()])
        context_ids = generate_contexts(connection, INCIDENT_ID, NOW)
        self.assertEqual(len(context_ids), 1)
        insert = connection.executions[1]
        self.assertIn("INSERT INTO metadata.incident_context", insert[0])
        self.assertIn("HIGH severity", insert[1][4])

    def test_retry_uses_stable_id_and_upsert(self):
        connection = FakeConnection()
        context = generate_stale_data_context(stale_incident())
        first = persist_context(connection, INCIDENT_ID, context, NOW)
        second = persist_context(connection, INCIDENT_ID, context, NOW)
        self.assertEqual(first, second)
        self.assertIn("ON CONFLICT (incident_id, context_version)", connection.executions[0][0])

    def test_no_id_loads_only_open_stale_data(self):
        connection = FakeConnection([incident_row()])
        generate_contexts(connection, None, NOW)
        select, parameters = connection.executions[0]
        self.assertIn("incident_type = %s AND incident_status = %s", select)
        self.assertEqual(parameters, ("STALE_DATA", "OPEN"))


if __name__ == "__main__":
    unittest.main()
