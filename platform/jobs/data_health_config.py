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
    "NULL_VALUES": "HIGH",
}


# Columns whose data contract requires every row to contain a value. This is
# intentionally explicit: many monitored columns are legitimately nullable.
NULL_VALUE_COLUMNS_BY_TABLE = {
    ("raw", "customers"): ("customer_id",),
    ("raw", "orders"): ("order_id", "customer_id"),
    ("raw", "payments"): ("payment_id", "order_id"),
    ("raw", "web_events"): ("event_id",),
    ("staging", "stg_customers"): ("customer_id",),
    ("staging", "stg_orders"): ("order_id", "customer_id"),
    ("staging", "stg_payments"): ("payment_id", "order_id"),
    ("staging", "stg_web_events"): ("event_id",),
    ("marts", "fct_orders"): (
        "order_id", "customer_key", "order_date_key", "order_status",
        "merchandise_subtotal", "order_discount_amount", "shipping_amount",
        "tax_amount", "order_total_amount",
    ),
    ("marts", "fct_payments"): (
        "payment_id", "order_id", "payment_date_key", "payment_amount",
    ),
    ("marts", "fct_web_events"): ("event_id", "event_date_key"),
    ("marts", "daily_sales"): (
        "daily_sales_key", "sales_date", "order_count", "order_total_amount",
    ),
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
