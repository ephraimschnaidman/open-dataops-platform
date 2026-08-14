from __future__ import annotations

from datetime import datetime, timezone

UTC = timezone.utc
NOW = datetime(2026, 8, 11, 13, 27, tzinfo=UTC)


def dt(day: int, hour: int, minute: int, second: float = 0) -> datetime:
    whole = int(second)
    return datetime(2026, 8, day, hour, minute, whole, int((second - whole) * 1_000_000), tzinfo=UTC)


ENV = {"environment_key": "production", "name": "Production"}
EVENTS_SOURCE = {"source_key": "events-kafka", "name": "Events Kafka", "source_type": "KAFKA", "operational_status": "DISCONNECTED"}
BILLING_SOURCE = {"source_key": "billing-postgres", "name": "Billing PostgreSQL", "source_type": "POSTGRESQL", "operational_status": "WARNING"}
WAREHOUSE_SOURCE = {"source_key": "analytics-warehouse", "name": "Production Warehouse", "source_type": "SNOWFLAKE", "operational_status": "HEALTHY"}


def run(run_id, pipeline_key, pipeline_name, pipeline_status, source, status, stage,
        started, completed, platform_code, vendor_code=None, rule_code=None, alerts=0):
    return {
        "corvetra_run_id": run_id,
        "pipeline": {"pipeline_key": pipeline_key, "name": pipeline_name,
                     "operational_status": pipeline_status},
        "source": source, "environment": ENV, "status": status, "stage": stage,
        "started_at": started, "completed_at": completed,
        "duration_seconds": (completed - started).total_seconds() if completed else None,
        "platform_code": platform_code, "vendor_code": vendor_code,
        "rule_code": rule_code, "active_alert_count": alerts,
        "pipeline_run_id": run_id + "-uuid",
    }


RUNS = [
    run("run_01J94EVT18", "events-processing", "Events Processing", "FAILED", EVENTS_SOURCE,
        "FAILED", "EXTRACT", dt(10, 14, 41, 3), dt(10, 14, 42, 38.412),
        "PIPELINE_EXECUTION_FAILED", "SASL_AUTHENTICATION_FAILED", alerts=1),
    run("run_01J92CING8", "customer-ingestion", "Customer Ingestion", "HEALTHY", WAREHOUSE_SOURCE,
        "SUCCESS", "LOAD", dt(10, 14, 32, 0), dt(10, 14, 34, 14), "RUN_COMPLETED"),
    run("run_01J92CVAL9", "customer-ingestion", "Customer Ingestion", "HEALTHY", WAREHOUSE_SOURCE,
        "SUCCESS", "LOAD", dt(10, 14, 5, 0), dt(10, 14, 7, 20), "RUN_COMPLETED_WITH_WARNINGS",
        rule_code="CHECK_NULL_RATE_THRESHOLD"),
    run("run_01J97BIL02", "billing-reconciliation", "Billing Reconciliation", "WARNING", BILLING_SOURCE,
        "FAILED", "VALIDATE", dt(10, 13, 28, 0), dt(10, 13, 36, 42),
        "VALIDATION_CHECK_FAILED", rule_code="CHECK_UNIQUENESS_VIOLATION", alerts=1),
    run("run_01JA7OLD40", "customer-ingestion", "Customer Ingestion", "HEALTHY", WAREHOUSE_SOURCE,
        "FAILED", "EXTRACT", dt(9, 19, 14, 0), dt(9, 19, 14, 18),
        "PIPELINE_EXECUTION_FAILED", "SNOWFLAKE_CONNECTION_RESET"),
]

PIPELINES = [
    {"pipeline_key": "events-processing", "name": "Events Processing", "environment": ENV,
     "source": EVENTS_SOURCE, "is_enabled": True, "operational_status": "FAILED",
     "latest_run": {key: RUNS[0][key] for key in ("corvetra_run_id", "status", "stage", "started_at", "completed_at", "duration_seconds", "platform_code", "vendor_code", "rule_code")},
     "current_issue": {"alert_key": "ALT-1042", "title": "Pipeline execution failing", "severity": "CRITICAL", "status": "OPEN", "platform_code": "PIPELINE_EXECUTION_FAILED", "vendor_code": "SASL_AUTHENTICATION_FAILED", "rule_code": None, "message": "Events failure", "detected_at": dt(10,14,42,38.412), "last_seen_at": dt(10,14,43), "acknowledged_at": None, "resolved_at": None},
     "pipeline_id": "events-p", "data_source_id": "events-s", "latest_run_uuid": RUNS[0]["pipeline_run_id"]},
    {"pipeline_key": "billing-reconciliation", "name": "Billing Reconciliation", "environment": ENV,
     "source": BILLING_SOURCE, "is_enabled": True, "operational_status": "WARNING",
     "latest_run": {key: RUNS[3][key] for key in ("corvetra_run_id", "status", "stage", "started_at", "completed_at", "duration_seconds", "platform_code", "vendor_code", "rule_code")},
     "current_issue": {"alert_key": "ALT-1040", "title": "Order ID unique failed", "severity": "WARNING", "status": "OPEN", "platform_code": "VALIDATION_CHECK_FAILED", "vendor_code": None, "rule_code": "CHECK_UNIQUENESS_VIOLATION", "message": "318 duplicates", "detected_at": dt(10,13,36,42), "last_seen_at": dt(10,13,36,42), "acknowledged_at": None, "resolved_at": None},
     "pipeline_id": "billing-p", "data_source_id": "billing-s", "latest_run_uuid": RUNS[3]["pipeline_run_id"]},
    {"pipeline_key": "customer-ingestion", "name": "Customer Ingestion", "environment": ENV,
     "source": WAREHOUSE_SOURCE, "is_enabled": True, "operational_status": "HEALTHY",
     "latest_run": {key: RUNS[1][key] for key in ("corvetra_run_id", "status", "stage", "started_at", "completed_at", "duration_seconds", "platform_code", "vendor_code", "rule_code")},
     "current_issue": None, "pipeline_id": "customer-p", "data_source_id": "warehouse-s",
     "latest_run_uuid": RUNS[1]["pipeline_run_id"]},
]

SOURCES = [
    {"data_source_id": "events-s", **EVENTS_SOURCE, "environment": ENV, "connected_pipeline_count": 1, "last_observed_at": dt(10,14,42,38.412)},
    {"data_source_id": "billing-s", **BILLING_SOURCE, "environment": ENV, "connected_pipeline_count": 1, "last_observed_at": dt(10,13,36,42)},
    {"data_source_id": "warehouse-s", **WAREHOUSE_SOURCE, "environment": ENV, "connected_pipeline_count": 1, "last_observed_at": None},
]

ALERTS = [
    {"alert_id": "a1", "alert_key": "ALT-1042", "title": "Pipeline execution failing", "severity": "CRITICAL", "status": "OPEN", "platform_code": "PIPELINE_EXECUTION_FAILED", "vendor_code": "SASL_AUTHENTICATION_FAILED", "rule_code": None, "message": "Events Kafka rejected credentials.", "detected_at": dt(10,14,42,38.412), "last_seen_at": dt(10,14,43), "pipeline_run_id": RUNS[0]["pipeline_run_id"], "validation_execution_id": None, "pipeline_id": "events-p", "data_source_id": "events-s", "environment": ENV, "pipeline": RUNS[0]["pipeline"], "source": EVENTS_SOURCE, "run": {key: RUNS[0][key] for key in ("corvetra_run_id", "status", "stage", "started_at", "completed_at", "duration_seconds", "platform_code", "vendor_code", "rule_code")}, "evidence_count": 5, "latest_event_key": "evt-001"},
    {"alert_id": "a2", "alert_key": "ALT-1040", "title": "Order ID unique failed", "severity": "WARNING", "status": "OPEN", "platform_code": "VALIDATION_CHECK_FAILED", "vendor_code": None, "rule_code": "CHECK_UNIQUENESS_VIOLATION", "message": "318 duplicates; expected 0 duplicates.", "detected_at": dt(10,13,36,42), "last_seen_at": dt(10,13,36,42), "pipeline_run_id": RUNS[3]["pipeline_run_id"], "validation_execution_id": "vx-order", "pipeline_id": "billing-p", "data_source_id": "billing-s", "environment": ENV, "pipeline": RUNS[3]["pipeline"], "source": BILLING_SOURCE, "run": {key: RUNS[3][key] for key in ("corvetra_run_id", "status", "stage", "started_at", "completed_at", "duration_seconds", "platform_code", "vendor_code", "rule_code")}, "evidence_count": 1, "latest_event_key": "evt-007"},
]

LATEST_VALIDATIONS = [{
    "validation_execution_id": "vx-order", "pipeline_run_id": RUNS[3]["pipeline_run_id"],
    "check_key": "order-id-unique", "name": "Order ID unique", "type": "UNIQUE",
    "result": "FAILED", "severity": "BLOCKING", "platform_code": "VALIDATION_CHECK_FAILED",
    "rule_code": "CHECK_UNIQUENESS_VIOLATION", "vendor_code": None,
    "actual": "318 duplicates", "expected": "0 duplicates", "message": "318 duplicate order IDs.",
    "evaluated_at": dt(10,13,36,42), "environment": ENV, "pipeline": RUNS[3]["pipeline"],
    "source": BILLING_SOURCE, "run": {key: RUNS[3][key] for key in ("corvetra_run_id", "status", "stage", "started_at", "completed_at", "duration_seconds", "platform_code", "vendor_code", "rule_code")},
    "alert_key": "ALT-1040", "evidence_count": 1, "latest_event_key": "evt-007",
}]

VALIDATION_HISTORY = [
    {"validation_execution_id": "vx-order", "result_status": "FAILED", "effective_severity": "BLOCKING", "evaluated_at": dt(10,13,36,42), "check_key": "order-id-unique", "check_name": "Order ID unique", "validation_check_id": "c1", "pipeline_key": "billing-reconciliation", "pipeline_name": "Billing Reconciliation", "operational_status": "WARNING"},
    {"validation_execution_id": "vx-payment", "result_status": "PASSED", "effective_severity": "WARNING", "evaluated_at": dt(10,13,36,42), "check_key": "payment-status-accepted-values", "check_name": "Payment status accepted values", "validation_check_id": "c2", "pipeline_key": "billing-reconciliation", "pipeline_name": "Billing Reconciliation", "operational_status": "WARNING"},
    {"validation_execution_id": "vx-customer", "result_status": "PASSED", "effective_severity": "BLOCKING", "evaluated_at": dt(10,14,33,48), "check_key": "customer-id-not-null", "check_name": "Customer ID not null", "validation_check_id": "c3", "pipeline_key": "customer-ingestion", "pipeline_name": "Customer Ingestion", "operational_status": "HEALTHY"},
    {"validation_execution_id": "vx-email", "result_status": "FAILED", "effective_severity": "WARNING", "evaluated_at": dt(10,14,6,45), "check_key": "customer-email-null-rate", "check_name": "Customer email null rate", "validation_check_id": "c4", "pipeline_key": "customer-ingestion", "pipeline_name": "Customer Ingestion", "operational_status": "HEALTHY"},
]

EVENTS = [{"event_key": "evt-001", "occurred_at": dt(10,14,42,38.412), "level": "ERROR", "stage": "EXTRACT", "platform_code": "PIPELINE_EXECUTION_FAILED", "vendor_code": "SASL_AUTHENTICATION_FAILED", "rule_code": None, "message": "Events Kafka rejected credentials.", "environment": ENV, "pipeline": RUNS[0]["pipeline"], "source": EVENTS_SOURCE, "run": {key: RUNS[0][key] for key in ("corvetra_run_id", "status", "stage", "started_at", "completed_at", "duration_seconds", "platform_code", "vendor_code", "rule_code")}}]


class StubAggregationRepository:
    def __init__(self):
        self.error = None

    def _raise(self):
        if self.error:
            raise self.error

    async def get_pipelines(self, filters):
        self._raise(); return list(PIPELINES)

    async def get_sources(self, filters):
        self._raise(); return list(SOURCES)

    async def get_active_alerts(self, filters):
        self._raise(); return list(ALERTS)

    async def get_latest_failed_validations(self, filters):
        self._raise(); return list(LATEST_VALIDATIONS)

    async def get_runs(self, filters, *, started_from=None, started_to=None, failed_only=False, limit=None):
        self._raise()
        rows = [row for row in RUNS if (started_from is None or row["started_at"] >= started_from)
                and (started_to is None or row["started_at"] < started_to)
                and (not failed_only or row["status"] == "FAILED")]
        return rows[:limit] if limit else rows

    async def get_validation_history(self, filters, *, evaluated_from, evaluated_to):
        self._raise()
        return [row for row in VALIDATION_HISTORY if evaluated_from <= row["evaluated_at"] < evaluated_to]

    async def get_events(self, filters, *, occurred_from=None, occurred_to=None, limit=None):
        self._raise()
        rows = [row for row in EVENTS if (occurred_from is None or row["occurred_at"] >= occurred_from)
                and (occurred_to is None or row["occurred_at"] < occurred_to)]
        return rows[:limit] if limit else rows
