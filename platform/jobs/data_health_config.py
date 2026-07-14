from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MonitoredTable:
    schema: str
    name: str
    freshness_column: str | None
    freshness_threshold_hours: float = 48.0
    row_count_change_threshold_percent: float = 25.0
    schema_drift_enabled: bool = True


SEVERITY_BY_INCIDENT_TYPE = {
    "STALE_DATA": "HIGH",
    "ROW_COUNT_INCREASE": "MEDIUM",
    "ROW_COUNT_DECREASE": "HIGH",
    "COLUMN_ADDED": "LOW",
    "COLUMN_REMOVED": "HIGH",
    "DATA_TYPE_CHANGED": "HIGH",
    "NULLABILITY_CHANGED": "MEDIUM",
}


MONITORED_TABLES = (
    MonitoredTable("raw", "customers", "created_at"),
    MonitoredTable("raw", "orders", "order_ts"),
    MonitoredTable("raw", "payments", "payment_ts"),
    MonitoredTable("raw", "web_events", "event_ts"),
    MonitoredTable("staging", "stg_customers", "created_at"),
    MonitoredTable("staging", "stg_orders", "order_ts"),
    MonitoredTable("staging", "stg_payments", "payment_ts"),
    MonitoredTable("staging", "stg_web_events", "event_ts"),
    MonitoredTable("marts", "fct_orders", "ordered_at"),
    MonitoredTable("marts", "fct_payments", "paid_at"),
    MonitoredTable("marts", "fct_web_events", "occurred_at"),
    MonitoredTable("marts", "daily_sales", "sales_date"),
)
