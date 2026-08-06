from __future__ import annotations

import re
from typing import Any

from .postgres import PostgresClient

RAW_KEYS = {
    "raw.customers": "customer_id", "raw.products": "product_id",
    "raw.orders": "order_id", "raw.order_items": "order_item_id",
    "raw.payments": "payment_id", "raw.web_events": "event_id",
}
MART_KEYS = {
    "marts.dim_customers": "customer_key",
    "marts.dim_products": "product_key", "marts.dim_date": "date_key",
    "marts.fct_orders": "order_id",
    "marts.fct_order_items": "order_item_id",
    "marts.fct_payments": "payment_id",
    "marts.fct_web_events": "event_id",
    "marts.daily_sales": "daily_sales_key",
    "marts.customer_lifetime_value": "customer_key",
    "marts.product_sales": "product_key",
}
METADATA_TABLES = (
    "metadata.pipeline_runs", "metadata.dbt_node_results",
    "metadata.table_health_metrics", "metadata.data_incidents",
)


def duplicate_key_checks(
    postgres: PostgresClient, table_keys: dict[str, str],
) -> dict[str, int]:
    return {
        table: int(postgres.scalar_read_only_query(
            f"SELECT count(*) - count(DISTINCT {key}) FROM {table}"
        ))
        for table, key in table_keys.items()
    }


def capture_database_snapshot(
    postgres: PostgresClient, dag_id: str,
) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", dag_id):
        raise ValueError("Invalid DAG identifier for metadata snapshot")
    counts = postgres.table_row_counts([*RAW_KEYS, *MART_KEYS])
    metadata_counts = {
        table: int(postgres.scalar_read_only_query(f"SELECT count(*) FROM {table}"))
        for table in METADATA_TABLES
    }
    metadata_counts["metadata.open_data_incidents"] = int(
        postgres.scalar_read_only_query(
            "SELECT count(*) FROM metadata.data_incidents WHERE incident_status = 'OPEN'"
        )
    )
    latest_rows = postgres.execute_read_only_query(
        "SELECT airflow_run_id FROM metadata.pipeline_runs "
        f"WHERE dag_id = '{dag_id}' AND UPPER(run_status) = 'SUCCESS' "
        "ORDER BY started_at DESC LIMIT 1"
    )
    latest = latest_rows[1][0] if len(latest_rows) > 1 else None
    return {
        "row_counts": counts,
        "raw_duplicate_checks": duplicate_key_checks(postgres, RAW_KEYS),
        "mart_duplicate_checks": duplicate_key_checks(postgres, MART_KEYS),
        "metadata_counts": metadata_counts,
        "metadata_same_run_duplicate_checks": {
            "pipeline_runs": int(postgres.scalar_read_only_query(
                "SELECT count(*) FROM (SELECT dag_id, airflow_run_id FROM metadata.pipeline_runs "
                "GROUP BY dag_id, airflow_run_id HAVING count(*) > 1) duplicates"
            )),
            "dbt_node_results": int(postgres.scalar_read_only_query(
                "SELECT count(*) FROM (SELECT pipeline_run_id, invocation_id, command_type, node_unique_id "
                "FROM metadata.dbt_node_results GROUP BY pipeline_run_id, invocation_id, command_type, "
                "node_unique_id HAVING count(*) > 1) duplicates"
            )),
            "table_health_metrics": int(postgres.scalar_read_only_query(
                "SELECT count(*) FROM (SELECT pipeline_run_id, table_schema, table_name "
                "FROM metadata.table_health_metrics GROUP BY pipeline_run_id, table_schema, table_name "
                "HAVING count(*) > 1) duplicates"
            )),
            "data_incidents": int(postgres.scalar_read_only_query(
                "SELECT count(*) FROM (SELECT pipeline_run_id, incident_type, table_schema, table_name, "
                "column_name FROM metadata.data_incidents GROUP BY pipeline_run_id, incident_type, "
                "table_schema, table_name, column_name HAVING count(*) > 1) duplicates"
            )),
        },
        "open_incident_condition_groups": int(postgres.scalar_read_only_query(
            "SELECT count(*) FROM (SELECT incident_type, table_schema, table_name, column_name "
            "FROM metadata.data_incidents WHERE incident_status = 'OPEN' GROUP BY incident_type, "
            "table_schema, table_name, column_name HAVING count(*) > 1) duplicates"
        )),
        "latest_successful_run_id": latest,
    }


def analyze_metadata_growth(
    baseline: dict[str, Any], after_first: dict[str, Any],
    after_second: dict[str, Any],
) -> dict[str, Any]:
    keys = baseline["metadata_counts"]
    first_delta = {
        key: after_first["metadata_counts"][key] - baseline["metadata_counts"][key]
        for key in keys
    }
    second_delta = {
        key: after_second["metadata_counts"][key] - after_first["metadata_counts"][key]
        for key in keys
    }
    same_run_duplicates = {
        "after_first": after_first["metadata_same_run_duplicate_checks"],
        "after_second": after_second["metadata_same_run_duplicate_checks"],
    }
    expected = (
        first_delta["metadata.pipeline_runs"] == 1
        and second_delta["metadata.pipeline_runs"] == 1
        and first_delta["metadata.dbt_node_results"] > 0
        and first_delta["metadata.dbt_node_results"] == second_delta["metadata.dbt_node_results"]
        and first_delta["metadata.table_health_metrics"] > 0
        and first_delta["metadata.table_health_metrics"] == second_delta["metadata.table_health_metrics"]
        and all(value == 0 for group in same_run_duplicates.values() for value in group.values())
    )
    return {
        "classification": "expected_append_only_history" if expected else "unexpected_growth",
        "first_run_delta": first_delta, "second_run_delta": second_delta,
        "same_run_duplicate_checks": same_run_duplicates,
        "incident_identity_design": (
            "Incidents are unique per pipeline run and condition; cross-run open groups are run-scoped history"
        ),
        "open_incident_condition_groups": {
            "baseline": baseline["open_incident_condition_groups"],
            "after_first": after_first["open_incident_condition_groups"],
            "after_second": after_second["open_incident_condition_groups"],
        },
    }
