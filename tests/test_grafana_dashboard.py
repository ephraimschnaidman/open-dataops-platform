import json
import unittest
from pathlib import Path


DASHBOARD_PATH = (
    Path(__file__).resolve().parents[1]
    / "platform"
    / "grafana"
    / "dashboards"
    / "open-dataops-platform-health.json"
)
PIPELINE_FILTER = (
    "(${pipeline_run:sqlstring} = 'all' OR "
    "pipeline_run_id::text = ${pipeline_run:sqlstring})"
)


class GrafanaDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))

    def test_pipeline_run_variable_has_stable_all_value(self):
        variables = {
            variable["name"]: variable
            for variable in self.dashboard["templating"]["list"]
        }
        pipeline_run = variables["pipeline_run"]

        self.assertTrue(pipeline_run["includeAll"])
        self.assertEqual(pipeline_run["allValue"], "all")
        self.assertFalse(pipeline_run["multi"])

    def test_every_pipeline_run_filter_uses_sqlstring_formatting(self):
        filtered_panels = []
        for panel in self.dashboard["panels"]:
            for target in panel.get("targets", []):
                sql = target.get("rawSql", "")
                if "pipeline_run" not in sql:
                    continue
                filtered_panels.append(panel["title"])
                self.assertIn(PIPELINE_FILTER, sql, panel["title"])
                self.assertNotIn("'$pipeline_run'", sql, panel["title"])

        self.assertEqual(
            filtered_panels,
            [
                "Latest pipeline status",
                "Open incidents",
                "Open incidents by severity",
                "Open incidents by type",
                "Incidents",
                "Row-count trends",
                "Latest table freshness",
                "dbt run/test status counts",
                "Slowest dbt nodes",
                "Recent failed dbt nodes and tests",
                "Latest schema changes",
            ],
        )

    def test_sqlstring_interpolation_quotes_uuid_and_all_once(self):
        uuid = "33261023-a24e-5914-8961-5d36963718a7"

        for selected_value in ("all", uuid):
            rendered_filter = PIPELINE_FILTER.replace(
                "${pipeline_run:sqlstring}", f"'{selected_value}'"
            )
            self.assertNotIn("''", rendered_filter)
            self.assertIn(f"pipeline_run_id::text = '{selected_value}'", rendered_filter)


if __name__ == "__main__":
    unittest.main()
