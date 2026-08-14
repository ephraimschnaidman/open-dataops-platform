import re
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
INIT_DIR = REPO_ROOT / "platform" / "warehouse" / "init"
SCHEMA_PATH = INIT_DIR / "11_create_corvetra_canonical_model.sql"
SEED_PATH = INIT_DIR / "12_seed_corvetra_round1.sql"
COMPOSE_PATH = REPO_ROOT / "docker-compose.yml"


class CanonicalMigrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        cls.seed_sql = SEED_PATH.read_text(encoding="utf-8")
        cls.compose_text = COMPOSE_PATH.read_text(encoding="utf-8")
        cls.compose = yaml.safe_load(cls.compose_text)

    def test_numbered_migrations_exist_in_order(self):
        numbered = sorted(path.name for path in INIT_DIR.glob("*.sql"))
        self.assertIn(SCHEMA_PATH.name, numbered)
        self.assertIn(SEED_PATH.name, numbered)
        self.assertLess(numbered.index("10_create_security_tables.sql"), numbered.index(SCHEMA_PATH.name))
        self.assertLess(numbered.index(SCHEMA_PATH.name), numbered.index(SEED_PATH.name))

    def test_schema_migration_is_transactional_locked_and_idempotent(self):
        for fragment in (
            "BEGIN;",
            "COMMIT;",
            "pg_advisory_xact_lock",
            "open-dataops-platform:canonical-schema:v1",
            "CREATE TABLE IF NOT EXISTS",
            "ADD COLUMN IF NOT EXISTS",
            "CREATE INDEX IF NOT EXISTS",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.schema_sql)

    def test_all_frozen_tables_and_run_columns_are_declared(self):
        for table in (
            "environments",
            "data_sources",
            "pipelines",
            "validation_checks",
            "validation_executions",
            "operational_alerts",
            "technical_events",
        ):
            with self.subTest(table=table):
                self.assertIn(f"CREATE TABLE IF NOT EXISTS metadata.{table}", self.schema_sql)
        for column in (
            "corvetra_run_id TEXT",
            "pipeline_id UUID",
            "stage_name TEXT",
            "platform_code TEXT",
            "vendor_code TEXT",
            "rule_code TEXT",
        ):
            with self.subTest(column=column):
                self.assertIn(f"ADD COLUMN IF NOT EXISTS {column}", self.schema_sql)

    def test_frozen_relationships_constraints_and_indexes_are_declared(self):
        fragments = (
            "pipelines_source_environment_fkey",
            "pipeline_runs_pipeline_id_fkey",
            "validation_executions_outcome_check",
            "operational_alerts_lifecycle_check",
            "technical_events_details_object_check",
            "UNIQUE NULLS NOT DISTINCT",
            "pipeline_runs_pipeline_started_idx",
            "validation_executions_run_evaluated_idx",
            "operational_alerts_status_seen_idx",
            "technical_events_run_occurred_idx",
            "ON DELETE CASCADE",
            "ON DELETE RESTRICT",
            "ON DELETE SET NULL",
            "GRANT SELECT ON TABLE",
        )
        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.schema_sql)

    def test_migrations_do_not_replace_existing_models_or_create_demo_objects(self):
        combined = f"{self.schema_sql}\n{self.seed_sql}"
        for destructive in ("DROP TABLE", "DROP SCHEMA", "TRUNCATE", "ALTER COLUMN pipeline_run_id"):
            with self.subTest(destructive=destructive):
                self.assertNotIn(destructive, combined.upper())
        self.assertIsNone(re.search(r"CREATE\s+SCHEMA[^;]*\bdemo\b", combined, re.I))
        self.assertIsNone(re.search(r"CREATE\s+TABLE[^;]*\bdemo\b", combined, re.I))
        self.assertNotIn("ALTER TABLE metadata.data_incidents", combined)
        self.assertNotIn("ALTER TABLE metadata.dbt_node_results", combined)

    def test_seed_is_transactional_locked_and_collision_checked(self):
        for fragment in (
            "BEGIN;",
            "COMMIT;",
            "open-dataops-platform:canonical-seed:round1:v1",
            "Canonical environment identity/key collision",
            "Canonical pipeline-run identity/key/Airflow collision",
            "Canonical validation-execution identity/run/check collision",
            "ON CONFLICT (source_key) DO NOTHING",
            "ON CONFLICT (pipeline_key) DO NOTHING",
            "ON CONFLICT (check_key) DO NOTHING",
            "ON CONFLICT (alert_key) DO NOTHING",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.seed_sql)

    def test_seed_contains_exact_canonical_identity_sets(self):
        expected_once = (
            "run_01J94EVT18",
            "run_01J97BIL02",
            "run_01J92CING8",
            "run_01J92CVAL9",
            "run_01JA7OLD40",
            "ALT-1042",
            "ALT-1040",
            "ALT-1037",
            "evt-001",
            "evt-002",
            "evt-003",
            "evt-004",
            "evt-005",
            "evt-007",
        )
        for identifier in expected_once:
            with self.subTest(identifier=identifier):
                self.assertIn(identifier, self.seed_sql)
        self.assertNotIn("INSERT INTO metadata.table_health_metrics", self.seed_sql)

    def test_billing_validation_contract_is_literal_and_structured(self):
        for value in (
            "Order ID unique",
            "'FAILED', 'BLOCKING', 'VALIDATION_CHECK_FAILED'",
            "CHECK_UNIQUENESS_VIOLATION",
            "318 duplicates",
            "0 duplicates",
        ):
            with self.subTest(value=value):
                self.assertIn(value, self.seed_sql)

    def test_compose_runs_explicit_migrations_in_order_and_api_waits(self):
        service = self.compose["services"]["api-db-init"]
        command = "\n".join(service["command"])
        paths = [
            "/opt/open-dataops/10_create_security_tables.sql",
            "/opt/open-dataops/11_create_corvetra_canonical_model.sql",
            "/opt/open-dataops/12_seed_corvetra_round1.sql",
        ]
        positions = [command.index(path) for path in paths]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(command.count("--set=ON_ERROR_STOP=1"), 3)
        for path in paths:
            self.assertTrue(any(path in mount for mount in service["volumes"]))
        self.assertEqual(
            self.compose["services"]["api"]["depends_on"]["api-db-init"]["condition"],
            "service_completed_successfully",
        )


if __name__ == "__main__":
    unittest.main()
