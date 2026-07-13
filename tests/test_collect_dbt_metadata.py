import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform" / "jobs"))

from collect_dbt_metadata import (  # noqa: E402
    ArtifactValidationError,
    main,
    parse_run_results,
    persist_metadata,
)


class FakeConnection:
    def __init__(self):
        self.executions = []

    def transaction(self):
        return nullcontext()

    def execute(self, statement, parameters):
        self.executions.append((statement, parameters))
        self.last_parameters = parameters
        return self

    def fetchone(self):
        return (self.last_parameters[0],)


class CollectDbtMetadataTests(unittest.TestCase):
    def write_artifact(self, payload):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "run_results.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.addCleanup(directory.cleanup)
        return path

    def test_parses_run_results(self):
        path = self.write_artifact({
            "metadata": {"invocation_id": "invocation-1"},
            "results": [{
                "unique_id": "model.open_dataops.stg_orders",
                "status": "success",
                "execution_time": 1.25,
                "message": "SELECT 10",
            }],
        })

        result = parse_run_results(path, "run")[0]

        self.assertEqual(result.node_name, "stg_orders")
        self.assertEqual(result.resource_type, "model")
        self.assertEqual(result.command_type, "run")

    def test_rejects_missing_required_fields(self):
        path = self.write_artifact({"metadata": {}, "results": []})
        with self.assertRaisesRegex(ArtifactValidationError, "invocation_id"):
            parse_run_results(path, "test")

    def test_retry_uses_same_ids_and_upserts(self):
        result = parse_run_results(self.write_artifact({
            "metadata": {"invocation_id": "invocation-1"},
            "results": [{
                "unique_id": "test.open_dataops.not_null_orders_id",
                "status": "pass",
                "execution_time": 0.2,
            }],
        }), "test")
        connection = FakeConnection()
        arguments = {
            "dag_id": "ecommerce_pipeline",
            "airflow_run_id": "manual__one",
            "started_at": datetime(2026, 7, 13, tzinfo=timezone.utc),
            "run_status": "success",
            "results": result,
        }

        first_id = persist_metadata(connection, **arguments)
        second_id = persist_metadata(connection, **arguments)

        self.assertEqual(first_id, second_id)
        self.assertEqual(connection.executions[1][1][0], connection.executions[3][1][0])
        self.assertTrue(all("ON CONFLICT" in statement for statement, _ in connection.executions))

    @patch("collect_dbt_metadata.collect_metadata")
    def test_no_arguments_uses_generated_manual_context(self, collect_metadata):
        collect_metadata.return_value = "pipeline-id"

        self.assertEqual(main([]), 0)

        arguments = collect_metadata.call_args.kwargs
        self.assertEqual(arguments["dag_id"], "manual")
        self.assertTrue(arguments["airflow_run_id"].startswith("manual__"))
        self.assertEqual(arguments["run_status"], "SUCCESS")
        self.assertIsNotNone(arguments["pipeline_run_id"])
        self.assertEqual(arguments["started_at"].tzinfo, timezone.utc)

    @patch("collect_dbt_metadata.collect_metadata")
    def test_airflow_arguments_preserve_deterministic_id_behavior(self, collect_metadata):
        collect_metadata.return_value = "pipeline-id"

        exit_code = main([
            "--dag-id", "ecommerce_pipeline",
            "--airflow-run-id", "scheduled__one",
            "--started-at", "2026-07-13T12:00:00+00:00",
            "--run-status", "success",
        ])

        self.assertEqual(exit_code, 0)
        arguments = collect_metadata.call_args.kwargs
        self.assertEqual(arguments["dag_id"], "ecommerce_pipeline")
        self.assertEqual(arguments["run_status"], "success")
        self.assertIsNone(arguments["pipeline_run_id"])


if __name__ == "__main__":
    unittest.main()
