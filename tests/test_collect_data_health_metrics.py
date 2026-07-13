import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform" / "jobs"))

from collect_data_health_metrics import (  # noqa: E402
    ColumnSnapshot,
    FreshnessColumnNotFoundError,
    MonitoredTableNotFoundError,
    TableMeasurement,
    measure_table,
    parse_schema_rows,
    persist_measurements,
)
from data_health_config import MONITORED_TABLES, MonitoredTable  # noqa: E402


class FakeCursor:
    def __init__(self, *, rows=None, row=None):
        self.rows = rows or []
        self.row = row

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.row


class MeasurementConnection:
    def __init__(self, schema_rows, measurement_row=(10, None)):
        self.schema_rows = schema_rows
        self.measurement_row = measurement_row
        self.executions = []

    def execute(self, statement, parameters=None):
        self.executions.append((statement, parameters))
        if isinstance(statement, str) and "information_schema.columns" in statement:
            return FakeCursor(rows=self.schema_rows)
        return FakeCursor(row=self.measurement_row)


class PersistConnection:
    def __init__(self):
        self.executions = []

    def execute(self, statement, parameters):
        self.executions.append((statement, parameters))
        return FakeCursor()


class DataHealthMetricsTests(unittest.TestCase):
    def test_freshness_configuration_covers_required_tables(self):
        configured = {(table.schema, table.name): table.freshness_column
                      for table in MONITORED_TABLES}
        self.assertEqual(len(configured), 12)
        self.assertEqual(configured[("raw", "orders")], "order_ts")
        self.assertEqual(configured[("marts", "fct_orders")], "ordered_at")
        self.assertEqual(configured[("marts", "daily_sales")], "sales_date")

    def test_parses_schema_snapshot_rows(self):
        snapshots = parse_schema_rows([
            ("order_id", 1, "text", "NO"),
            ("ordered_at", 2, "timestamp with time zone", "YES"),
        ])
        self.assertEqual(snapshots[0], ColumnSnapshot("order_id", 1, "text", False))
        self.assertTrue(snapshots[1].is_nullable)

    def test_missing_table_raises_meaningful_error(self):
        with self.assertRaisesRegex(MonitoredTableNotFoundError, "raw.orders"):
            measure_table(MeasurementConnection([]), MonitoredTable("raw", "orders", "order_ts"))

    def test_missing_freshness_column_raises_meaningful_error(self):
        rows = [("order_id", 1, "text", "NO")]
        with self.assertRaisesRegex(FreshnessColumnNotFoundError, "order_ts"):
            measure_table(
                MeasurementConnection(rows),
                MonitoredTable("raw", "orders", "order_ts"),
            )

    def test_retry_uses_stable_ids_and_upserts(self):
        connection = PersistConnection()
        pipeline_run_id = uuid.uuid4()
        measured_at = datetime(2026, 7, 13, tzinfo=timezone.utc)
        measurement = TableMeasurement(
            MonitoredTable("raw", "orders", "order_ts"), 10, measured_at,
            (ColumnSnapshot("order_id", 1, "text", False),),
        )

        persist_measurements(connection, pipeline_run_id=pipeline_run_id,
                             measurements=[measurement], measured_at=measured_at)
        persist_measurements(connection, pipeline_run_id=pipeline_run_id,
                             measurements=[measurement], measured_at=measured_at)

        first_metric = connection.executions[0][1][0]
        second_metric = connection.executions[3][1][0]
        first_snapshot = connection.executions[2][1][0]
        second_snapshot = connection.executions[5][1][0]
        self.assertEqual(first_metric, second_metric)
        self.assertEqual(first_snapshot, second_snapshot)
        self.assertIn("ON CONFLICT", connection.executions[0][0])
        self.assertIn("ON CONFLICT", connection.executions[2][0])


if __name__ == "__main__":
    unittest.main()
