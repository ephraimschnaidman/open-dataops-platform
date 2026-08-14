import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import psycopg
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.config import Settings  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
INIT_DIR = REPO_ROOT / "platform" / "warehouse" / "init"
SCHEMA_SQL = (INIT_DIR / "11_create_corvetra_canonical_model.sql").read_text(encoding="utf-8")
SEED_SQL = (INIT_DIR / "12_seed_corvetra_round1.sql").read_text(encoding="utf-8")
PER_DATABASE_PRE_CANONICAL_SCRIPTS = (
    "01_create_schemas.sql",
    "03_create_metadata_tables.sql",
    "04_create_data_health_tables.sql",
    "05_create_data_incidents.sql",
    "06_create_grafana_reader.sql",
    "07_create_incident_context.sql",
    "08_add_schema_change_context.sql",
    "09_add_null_values_context.sql",
    "10_create_security_tables.sql",
)


@unittest.skipUnless(
    os.getenv("RUN_CANONICAL_DB_INTEGRATION") == "1",
    "Set RUN_CANONICAL_DB_INTEGRATION=1 to run canonical PostgreSQL tests",
)
class CanonicalDatabaseIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = Settings.from_environment()
        suffix = f"{os.getpid()}_{uuid4().hex[:8]}"
        cls.fresh_db = f"canonical_fresh_{suffix}"
        cls.existing_db = f"canonical_existing_{suffix}"
        cls._create_database(cls.fresh_db)
        cls._create_database(cls.existing_db)
        try:
            cls._apply_precanonical_scripts(cls.fresh_db)
            cls._execute_file(cls.fresh_db, SCHEMA_SQL)
            cls._execute_file(cls.fresh_db, SEED_SQL)

            cls._apply_precanonical_scripts(cls.existing_db)
            cls.legacy_rows = cls._insert_legacy_runs(cls.existing_db)
            cls._execute_file(cls.existing_db, SCHEMA_SQL)
            cls._execute_file(cls.existing_db, SEED_SQL)
        except Exception:
            cls._drop_database(cls.fresh_db)
            cls._drop_database(cls.existing_db)
            raise

    @classmethod
    def tearDownClass(cls):
        cls._drop_database(cls.fresh_db)
        cls._drop_database(cls.existing_db)

    @classmethod
    def _kwargs(cls, database):
        values = cls.settings.database_connection_kwargs()
        values["dbname"] = database
        return values

    @classmethod
    def _admin_connection(cls):
        connection = psycopg.connect(**cls._kwargs("postgres"))
        connection.autocommit = True
        return connection

    @classmethod
    def _create_database(cls, database):
        with cls._admin_connection() as connection:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))

    @classmethod
    def _drop_database(cls, database):
        with cls._admin_connection() as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database,),
            )
            connection.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database)))

    @classmethod
    def _execute_file(cls, database, contents):
        with psycopg.connect(**cls._kwargs(database), autocommit=True) as connection:
            connection.execute(contents)

    @classmethod
    def _apply_precanonical_scripts(cls, database):
        # 02 creates the cluster-level Airflow database. These isolated databases
        # exercise every dataops-database script around it without touching Airflow.
        for filename in PER_DATABASE_PRE_CANONICAL_SCRIPTS:
            cls._execute_file(database, (INIT_DIR / filename).read_text(encoding="utf-8"))

    @classmethod
    def _insert_legacy_runs(cls, database):
        rows = []
        base = datetime(2026, 7, 1, tzinfo=timezone.utc)
        for index in range(41):
            rows.append((
                uuid5(NAMESPACE_URL, f"canonical-existing-run-{index}"),
                "ecommerce_pipeline",
                f"scheduled__legacy_{index:02d}",
                base + timedelta(hours=index),
                base + timedelta(hours=index, minutes=5),
                "SUCCESS",
                base + timedelta(hours=index, minutes=6),
            ))
        with psycopg.connect(**cls._kwargs(database)) as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO metadata.pipeline_runs
                        (pipeline_run_id, dag_id, airflow_run_id, started_at,
                         completed_at, run_status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    rows,
                )
        return rows

    def connect(self, database=None, *, autocommit=False):
        return psycopg.connect(
            **self._kwargs(database or self.fresh_db),
            autocommit=autocommit,
        )

    def test_fresh_database_contains_existing_and_canonical_models(self):
        with self.connect() as connection:
            schemas = {row[0] for row in connection.execute(
                "SELECT schema_name FROM information_schema.schemata"
            ).fetchall()}
            metadata_tables = {row[0] for row in connection.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'metadata'"
            ).fetchall()}
            roles = connection.execute(
                "SELECT name FROM security.roles ORDER BY name"
            ).fetchall()
        self.assertTrue({"raw", "staging", "marts", "metadata", "security"} <= schemas)
        self.assertTrue({
            "pipeline_runs", "dbt_node_results", "table_health_metrics",
            "table_schema_snapshots", "data_incidents", "incident_context",
            "environments", "data_sources", "pipelines", "validation_checks",
            "validation_executions", "operational_alerts", "technical_events",
        } <= metadata_tables)
        self.assertEqual(roles, [("Admin",), ("Operator",), ("ReadOnly",)])

    def test_exact_deterministic_seed_identities_and_counts(self):
        expected = {
            "environments": (2, "acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6"),
            "data_sources": (4, "b8548a45-da0b-5539-9886-6f25e572e3e7"),
            "pipelines": (3, "38cfb7c0-9a96-5ce2-9631-8e5632fa6142"),
            "validation_checks": (4, "e408fd55-1a14-5b44-9eb5-8eb6b97b8d62"),
            "validation_executions": (4, "41801d5b-ae43-5da5-8d11-6934430eeaeb"),
            "operational_alerts": (3, "fe6dc079-ef9e-52e6-b819-5252c8f4b5b8"),
            "technical_events": (6, "8420c60b-0951-5442-b172-527c704b90ea"),
        }
        id_columns = {
            "environments": "environment_id",
            "data_sources": "data_source_id",
            "pipelines": "pipeline_id",
            "validation_checks": "validation_check_id",
            "validation_executions": "validation_execution_id",
            "operational_alerts": "alert_id",
            "technical_events": "technical_event_id",
        }
        with self.connect() as connection:
            for table, (count, sample_id) in expected.items():
                with self.subTest(table=table):
                    actual = connection.execute(
                        sql.SQL("SELECT COUNT(*), bool_or({} = %s) FROM metadata.{}").format(
                            sql.Identifier(id_columns[table]), sql.Identifier(table)
                        ),
                        (sample_id,),
                    ).fetchone()
                    self.assertEqual(actual, (count, True))
            runs = connection.execute(
                "SELECT corvetra_run_id, pipeline_run_id::text FROM metadata.pipeline_runs "
                "ORDER BY corvetra_run_id"
            ).fetchall()
        self.assertEqual(len(runs), 5)
        self.assertIn(("run_01J94EVT18", "7214b5a0-8e87-52c2-a5e0-0cc69a5b8a2d"), runs)

    def test_existing_41_runs_are_byte_for_byte_preserved(self):
        with self.connect(self.existing_db) as connection:
            rows = connection.execute(
                """
                SELECT pipeline_run_id, dag_id, airflow_run_id, started_at,
                       completed_at, run_status, created_at,
                       corvetra_run_id, pipeline_id, stage_name,
                       platform_code, vendor_code, rule_code
                FROM metadata.pipeline_runs
                WHERE corvetra_run_id IS NULL
                ORDER BY airflow_run_id
                """
            ).fetchall()
            total = connection.execute("SELECT COUNT(*) FROM metadata.pipeline_runs").fetchone()[0]
        expected = sorted(self.legacy_rows, key=lambda row: row[2])
        self.assertEqual(total, 46)
        self.assertEqual(len(rows), 41)
        for actual, original in zip(rows, expected, strict=True):
            self.assertEqual(actual[:7], original)
            self.assertEqual(actual[7:], (None, None, None, None, None, None))

    def test_events_story_integrity(self):
        query = """
            SELECT s.source_name, p.pipeline_name, r.corvetra_run_id,
                   r.stage_name, r.run_status, r.platform_code, r.vendor_code,
                   a.alert_key, a.alert_status,
                   array_agg(e.event_key ORDER BY e.occurred_at)
            FROM metadata.pipeline_runs r
            JOIN metadata.pipelines p USING (pipeline_id)
            JOIN metadata.data_sources s USING (data_source_id)
            JOIN metadata.operational_alerts a USING (pipeline_run_id)
            JOIN metadata.technical_events e USING (pipeline_run_id)
            WHERE r.corvetra_run_id = 'run_01J94EVT18'
            GROUP BY s.source_name, p.pipeline_name, r.corvetra_run_id,
                     r.stage_name, r.run_status, r.platform_code, r.vendor_code,
                     a.alert_key, a.alert_status
        """
        with self.connect() as connection:
            row = connection.execute(query).fetchone()
        self.assertEqual(row, (
            "Events Kafka", "Events Processing", "run_01J94EVT18",
            "EXTRACT", "FAILED", "PIPELINE_EXECUTION_FAILED",
            "SASL_AUTHENTICATION_FAILED", "ALT-1042", "OPEN",
            ["evt-005", "evt-004", "evt-003", "evt-002", "evt-001"],
        ))

    def test_billing_story_integrity(self):
        query = """
            SELECT s.source_name, p.pipeline_name, r.corvetra_run_id,
                   c.check_name, x.result_status, x.effective_severity,
                   x.platform_code, x.rule_code, x.actual_value, x.expected_value,
                   a.alert_key, e.event_key
            FROM metadata.validation_executions x
            JOIN metadata.validation_checks c USING (validation_check_id)
            JOIN metadata.pipeline_runs r USING (pipeline_run_id)
            JOIN metadata.pipelines p ON p.pipeline_id = r.pipeline_id
            JOIN metadata.data_sources s ON s.data_source_id = p.data_source_id
            JOIN metadata.operational_alerts a USING (validation_execution_id)
            JOIN metadata.technical_events e USING (validation_execution_id)
            WHERE r.corvetra_run_id = 'run_01J97BIL02'
              AND c.check_key = 'order-id-unique'
        """
        with self.connect() as connection:
            row = connection.execute(query).fetchone()
        self.assertEqual(row, (
            "Billing PostgreSQL", "Billing Reconciliation", "run_01J97BIL02",
            "Order ID unique", "FAILED", "BLOCKING", "VALIDATION_CHECK_FAILED",
            "CHECK_UNIQUENESS_VIOLATION", "318 duplicates", "0 duplicates",
            "ALT-1040", "evt-007",
        ))

    def test_three_customer_ingestion_stories(self):
        with self.connect() as connection:
            runs = connection.execute(
                """
                SELECT r.corvetra_run_id, r.run_status, r.stage_name,
                       r.platform_code, r.vendor_code, r.rule_code
                FROM metadata.pipeline_runs r
                JOIN metadata.pipelines p USING (pipeline_id)
                WHERE p.pipeline_key = 'customer-ingestion'
                ORDER BY r.corvetra_run_id
                """
            ).fetchall()
            validations = connection.execute(
                """
                SELECT r.corvetra_run_id, c.check_key, x.result_status,
                       x.effective_severity, x.actual_value, x.expected_value
                FROM metadata.validation_executions x
                JOIN metadata.pipeline_runs r USING (pipeline_run_id)
                JOIN metadata.validation_checks c USING (validation_check_id)
                WHERE r.corvetra_run_id IN ('run_01J92CING8', 'run_01J92CVAL9')
                ORDER BY r.corvetra_run_id
                """
            ).fetchall()
        self.assertEqual(len(runs), 3)
        self.assertIn(("run_01J92CING8", "SUCCESS", "LOAD", "RUN_COMPLETED", None, None), runs)
        self.assertIn(("run_01J92CVAL9", "SUCCESS", "LOAD", "RUN_COMPLETED_WITH_WARNINGS", None, "CHECK_NULL_RATE_THRESHOLD"), runs)
        self.assertIn(("run_01JA7OLD40", "FAILED", "EXTRACT", "PIPELINE_EXECUTION_FAILED", "SNOWFLAKE_CONNECTION_RESET", None), runs)
        self.assertEqual(validations, [
            ("run_01J92CING8", "customer-id-not-null", "PASSED", "BLOCKING", "0 nulls", "0 nulls"),
            ("run_01J92CVAL9", "customer-email-null-rate", "FAILED", "WARNING", "3.7% null", "< 2% null"),
        ])

    def test_schema_and_seed_are_repeatable_and_preserve_mutable_state(self):
        with self.connect(autocommit=True) as connection:
            before = connection.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM metadata.pipeline_runs),
                  (SELECT COUNT(*) FROM metadata.validation_executions),
                  (SELECT COUNT(*) FROM metadata.technical_events),
                  (SELECT created_at FROM metadata.pipeline_runs
                   WHERE corvetra_run_id = 'run_01J94EVT18')
                """
            ).fetchone()
            connection.execute("UPDATE metadata.data_sources SET operational_status = 'HEALTHY' WHERE source_key = 'events-kafka'")
            connection.execute("UPDATE metadata.pipelines SET is_enabled = FALSE WHERE pipeline_key = 'events-processing'")
            connection.execute("UPDATE metadata.validation_checks SET is_enabled = FALSE, default_severity = 'WARNING' WHERE check_key = 'order-id-unique'")
            connection.execute(
                "UPDATE metadata.operational_alerts SET alert_status = 'ACKNOWLEDGED', "
                "acknowledged_at = '2026-08-10T14:44:00Z' WHERE alert_key = 'ALT-1042'"
            )
            connection.execute(SCHEMA_SQL)
            connection.execute(SEED_SQL)
            after = connection.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM metadata.pipeline_runs),
                  (SELECT COUNT(*) FROM metadata.validation_executions),
                  (SELECT COUNT(*) FROM metadata.technical_events),
                  (SELECT created_at FROM metadata.pipeline_runs
                   WHERE corvetra_run_id = 'run_01J94EVT18'),
                  (SELECT operational_status FROM metadata.data_sources WHERE source_key = 'events-kafka'),
                  (SELECT is_enabled FROM metadata.pipelines WHERE pipeline_key = 'events-processing'),
                  (SELECT (is_enabled, default_severity) FROM metadata.validation_checks WHERE check_key = 'order-id-unique'),
                  (SELECT (alert_status, acknowledged_at IS NOT NULL) FROM metadata.operational_alerts WHERE alert_key = 'ALT-1042')
                """
            ).fetchone()
            self.assertEqual(after[:4], before)
            self.assertEqual(
                after[4:],
                ("HEALTHY", False, ("f", "WARNING"), ("ACKNOWLEDGED", "t")),
            )
            connection.execute("UPDATE metadata.data_sources SET operational_status = 'DISCONNECTED' WHERE source_key = 'events-kafka'")
            connection.execute("UPDATE metadata.pipelines SET is_enabled = TRUE WHERE pipeline_key = 'events-processing'")
            connection.execute("UPDATE metadata.validation_checks SET is_enabled = TRUE, default_severity = 'BLOCKING' WHERE check_key = 'order-id-unique'")
            connection.execute(
                "UPDATE metadata.operational_alerts SET alert_status = 'OPEN', acknowledged_at = NULL "
                "WHERE alert_key = 'ALT-1042'"
            )

    def test_representative_constraints_reject_invalid_data(self):
        cases = (
            (
                "invalid source status",
                "UPDATE metadata.data_sources SET operational_status = 'BROKEN' WHERE source_key = 'events-kafka'",
                (),
            ),
            (
                "cross-environment pipeline source",
                """
                INSERT INTO metadata.pipelines
                    (pipeline_id, pipeline_key, pipeline_name, environment_id,
                     data_source_id, airflow_dag_id)
                VALUES (%s, 'invalid-environment-pipeline', 'Invalid',
                        '00b7a432-4e39-544a-9fdf-c990442446be',
                        'b8548a45-da0b-5539-9886-6f25e572e3e7', 'invalid_dag')
                """,
                (uuid4(),),
            ),
            (
                "malformed product run id",
                """
                INSERT INTO metadata.pipeline_runs
                    (pipeline_run_id, dag_id, airflow_run_id, started_at,
                     run_status, corvetra_run_id, pipeline_id)
                VALUES (%s, 'invalid_dag', %s, CURRENT_TIMESTAMP,
                        'FAILED', 'bad-run-id',
                        '38cfb7c0-9a96-5ce2-9631-8e5632fa6142')
                """,
                (uuid4(), f"invalid_{uuid4()}"),
            ),
            (
                "invalid validation outcome",
                """
                UPDATE metadata.validation_executions
                SET result_status = 'NOT_EVALUATED'
                WHERE validation_execution_id = '41801d5b-ae43-5da5-8d11-6934430eeaeb'
                """,
                (),
            ),
            (
                "invalid alert lifecycle",
                """
                UPDATE metadata.operational_alerts
                SET resolved_at = CURRENT_TIMESTAMP
                WHERE alert_key = 'ALT-1042'
                """,
                (),
            ),
            (
                "non-object event details",
                "UPDATE metadata.technical_events SET event_details = '[]'::jsonb WHERE event_key = 'evt-001'",
                (),
            ),
            (
                "orphaned run pipeline",
                "UPDATE metadata.pipeline_runs SET pipeline_id = %s WHERE corvetra_run_id = 'run_01J94EVT18'",
                (uuid4(),),
            ),
            (
                "duplicate alert key",
                """
                INSERT INTO metadata.operational_alerts
                    (alert_id, alert_key, pipeline_run_id, alert_title, severity,
                     alert_status, platform_code, alert_message, detected_at, last_seen_at)
                VALUES (%s, 'ALT-1042', '7214b5a0-8e87-52c2-a5e0-0cc69a5b8a2d',
                        'Duplicate', 'WARNING', 'OPEN', 'DUPLICATE', 'Duplicate',
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (uuid4(),),
            ),
        )
        for label, statement, parameters in cases:
            with self.subTest(label=label):
                with self.connect() as connection:
                    with self.assertRaises(psycopg.Error):
                        with connection.transaction():
                            connection.execute(statement, parameters)


if __name__ == "__main__":
    unittest.main()
