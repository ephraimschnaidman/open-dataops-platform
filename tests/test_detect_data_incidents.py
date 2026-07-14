import sys
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform" / "jobs"))

from data_health_config import MonitoredTable  # noqa: E402
from detect_data_incidents import (  # noqa: E402
    ColumnShape,
    HealthMetric,
    detect_for_table,
    persist_incidents,
)


NOW = datetime(2026, 7, 14, 12, tzinfo=timezone.utc)
TABLE = MonitoredTable("marts", "orders", "ordered_at", 24, 20, True)
SCHEMA = {"order_id": ColumnShape("text", False)}


class FakeConnection:
    def __init__(self):
        self.executions = []

    def execute(self, statement, parameters):
        self.executions.append((statement, parameters))


def detect(current_count=100, previous_count=100, current_schema=None, previous_schema=None,
           freshness=None):
    current = HealthMetric(current_count, freshness or NOW)
    previous = None if previous_count is None else HealthMetric(previous_count, NOW)
    return detect_for_table(TABLE, current, previous,
                            SCHEMA if current_schema is None else current_schema,
                            previous_schema, NOW)


class IncidentDetectionTests(unittest.TestCase):
    def test_first_run_only_evaluates_freshness(self):
        self.assertEqual(detect(previous_count=None, previous_schema=None), [])

    def test_row_count_increase(self):
        self.assertEqual([i.incident_type for i in detect(130, 100, previous_schema=SCHEMA)],
                         ["ROW_COUNT_INCREASE"])

    def test_row_count_decrease(self):
        self.assertEqual([i.incident_type for i in detect(70, 100, previous_schema=SCHEMA)],
                         ["ROW_COUNT_DECREASE"])

    def test_freshness_breach(self):
        incidents = detect(previous_count=None, freshness=NOW - timedelta(hours=25))
        self.assertEqual(incidents[0].incident_type, "STALE_DATA")

    def test_added_column(self):
        schema = {**SCHEMA, "status": ColumnShape("text", True)}
        self.assertEqual([i.incident_type for i in detect(current_schema=schema, previous_schema=SCHEMA)],
                         ["COLUMN_ADDED"])

    def test_removed_column(self):
        old = {**SCHEMA, "status": ColumnShape("text", True)}
        self.assertEqual([i.incident_type for i in detect(current_schema=SCHEMA, previous_schema=old)],
                         ["COLUMN_REMOVED"])

    def test_data_type_change(self):
        changed = {"order_id": ColumnShape("uuid", False)}
        self.assertEqual([i.incident_type for i in detect(current_schema=changed, previous_schema=SCHEMA)],
                         ["DATA_TYPE_CHANGED"])

    def test_retry_uses_same_id_and_upsert(self):
        connection = FakeConnection()
        incident = detect(130, 100, previous_schema=SCHEMA)[0]
        run_id = uuid.uuid4()
        persist_incidents(connection, run_id, [incident], NOW)
        persist_incidents(connection, run_id, [incident], NOW)
        self.assertEqual(connection.executions[0][1][0], connection.executions[1][1][0])
        self.assertIn("ON CONFLICT", connection.executions[0][0])


if __name__ == "__main__":
    unittest.main()
