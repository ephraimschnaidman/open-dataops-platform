export type HealthStatus = "Healthy" | "Warning" | "Critical";
export type HealthTimeRange = "24h" | "7d" | "30d" | "90d";
export type HealthEnvironment = "All" | "Production" | "Staging" | "Development";
export type HealthResourceType = "All" | "Pipelines" | "Data Sources";
export type HealthQaState = "warning" | "healthy" | "critical" | "24-hour" | "7-day" | "30-day" | "pipeline-scoped" | "source-scoped" | "reliability" | "runtime" | "schedule" | "freshness" | "source-reliability" | "validation-quality" | "no-history" | "insufficient-history" | "filtered-empty" | "stale" | "data-gap" | "error" | "partial" | "loading";

export interface HealthMetric {
    key: string; label: string; value: string; previous: string; delta: string; favorable: boolean;
    status: HealthStatus; threshold: string; warning: string; critical: string;
}

export const timeRangeOptions = [
    { label: "Last 24 hours", value: "24h" }, { label: "Last 7 days", value: "7d" },
    { label: "Last 30 days", value: "30d" }, { label: "Last 90 days", value: "90d" },
];

export const healthResources = [
    { id: "customer-ingestion", name: "Customer Ingestion", type: "Pipelines", environment: "Production" },
    { id: "billing-reconciliation", name: "Billing Reconciliation", type: "Pipelines", environment: "Production" },
    { id: "events-processing", name: "Events Processing", type: "Pipelines", environment: "Production" },
    { id: "warehouse-sync", name: "Warehouse Sync", type: "Pipelines", environment: "Production" },
    { id: "analytics-warehouse", name: "Production Warehouse", type: "Data Sources", environment: "Production" },
    { id: "billing-postgres", name: "Billing PostgreSQL", type: "Data Sources", environment: "Production" },
    { id: "events-kafka", name: "Events Kafka", type: "Data Sources", environment: "Production" },
];

export const coreMetrics: HealthMetric[] = [
    { key: "reliability", label: "Pipeline Success Rate", value: "98.7%", previous: "99.3%", delta: "-0.6%", favorable: false, status: "Warning", threshold: "≥ 98%", warning: "95–97.99%", critical: "< 95%" },
    { key: "schedule", label: "Schedule Adherence", value: "99.3%", previous: "99.7%", delta: "-0.4%", favorable: false, status: "Healthy", threshold: "≥ 99%", warning: "95–98.99%", critical: "< 95%" },
    { key: "sources", label: "Source Availability", value: "99.92%", previous: "99.96%", delta: "-0.04%", favorable: false, status: "Healthy", threshold: "≥ 99.9%", warning: "99–99.89%", critical: "< 99%" },
    { key: "validation", label: "Validation Pass Rate", value: "97.8%", previous: "99.1%", delta: "-1.3%", favorable: false, status: "Warning", threshold: "≥ 98%", warning: "95–97.99%", critical: "< 95%" },
    { key: "freshness", label: "Freshness Compliance", value: "96.4%", previous: "98.2%", delta: "-1.8%", favorable: false, status: "Warning", threshold: "≥ 98%", warning: "95–97.99%", critical: "< 95%" },
    { key: "runtime", label: "Avg Pipeline Runtime", value: "2m 18s", previous: "2m 05s", delta: "+13s", favorable: false, status: "Warning", threshold: "≤ 2m 15s", warning: "2m 16s–3m", critical: "> 3m" },
];

export const trendLabels: Record<HealthTimeRange, string[]> = {
    "24h": ["12 AM", "4 AM", "8 AM", "12 PM", "4 PM", "8 PM", "Now"],
    "7d": ["Aug 5", "Aug 6", "Aug 7", "Aug 8", "Aug 9", "Aug 10", "Aug 11"],
    "30d": ["Jul 13", "Jul 18", "Jul 23", "Jul 28", "Aug 2", "Aug 7", "Aug 11"],
    "90d": ["May 13", "May 28", "Jun 12", "Jun 27", "Jul 12", "Jul 27", "Aug 11"],
};

export const trends = {
    reliability: [99.4, 99.1, 98.9, 97.4, 99.2, 98.6, 98.7],
    runtime: [121, 124, 126, 132, 129, 135, 138],
    schedule: [99.8, 99.7, 99.5, 98.8, 99.6, 99.4, 99.3],
    freshness: [98.5, 98.1, 97.9, 96.8, 97.2, 96.7, 96.4],
    availability: [99.98, 99.96, 99.94, 99.72, 99.9, 99.88, 99.92],
    failures: [0, 1, 2, 7, 1, 1, 0],
    validation: [99.3, 99.1, 98.8, 98.5, 98.2, 97.9, 97.8],
};

export const reliabilityRows = [
    { id: "events-processing", name: "Events Processing", current: "88.4%", previous: "94.1%", failures: "8 failed", status: "Critical" as const },
    { id: "billing-reconciliation", name: "Billing Reconciliation", current: "96.2%", previous: "98.7%", failures: "5 failed", status: "Warning" as const },
    { id: "customer-ingestion", name: "Customer Ingestion", current: "99.6%", previous: "99.1%", failures: "2 failed", status: "Healthy" as const },
    { id: "warehouse-sync", name: "Warehouse Sync", current: "100%", previous: "99.8%", failures: "0 failed", status: "Healthy" as const },
];

export const runtimeRows = [
    { id: "billing-reconciliation", name: "Billing Reconciliation", current: "8m 42s", previous: "5m 55s", change: "+47%", status: "Warning" as const },
    { id: "warehouse-sync", name: "Warehouse Sync", current: "4m 02s", previous: "3m 58s", change: "+2%", status: "Healthy" as const },
    { id: "customer-ingestion", name: "Customer Ingestion", current: "2m 14s", previous: "2m 11s", change: "+2%", status: "Healthy" as const },
];

export const scheduleRows = [
    { id: "warehouse-sync", name: "Risk Reporting", adherence: "91.7%", late: "1", missed: "1", status: "Warning" as const },
    { id: "manual-customer-export", name: "Customer Export", adherence: "96.4%", late: "5", missed: "1", status: "Warning" as const },
];

export const freshnessRows = [
    { id: "warehouse-sync", dataset: "accounts", pipeline: "Risk Reporting", expected: "< 2h", age: "3h 14m", status: "Warning" as const },
    { id: "customer-ingestion", dataset: "customers", pipeline: "Customer Ingestion", expected: "< 1h", age: "18m", status: "Healthy" as const },
];

export const sourceRows = [
    { id: "billing-postgres", name: "Billing PostgreSQL", availability: "98.7%", latency: "418 ms", failures: "11 failures", status: "Warning" as const },
    { id: "analytics-warehouse", name: "Production Warehouse", availability: "99.99%", latency: "84 ms", failures: "1 failure", status: "Healthy" as const },
    { id: "events-kafka", name: "Events Kafka", availability: "100%", latency: "21 ms", failures: "0 failures", status: "Healthy" as const },
    { id: "customer-sqlserver", name: "Legacy SQL Server", availability: "—", latency: "—", failures: "—", status: "Disabled" as const },
];

export const validationRows = [
    { id: "customer-email-null-rate", name: "Customer email null rate", rate: "8.4%", failures: "42", severity: "Warning", status: "Warning" as const },
    { id: "order-id-unique", name: "Order ID unique", rate: "2.1%", failures: "13", severity: "Blocking", status: "Critical" as const },
    { id: "account-data-freshness", name: "Account freshness", rate: "3.7%", failures: "17", severity: "Warning", status: "Warning" as const },
];

export const reviewRows = [
    { id: "events-processing", resource: "Events Processing", type: "Pipeline", signal: "Success Rate", current: "88.4%", previous: "94.1%", status: "Critical" as const },
    { id: "billing-reconciliation", resource: "Billing Reconciliation", type: "Pipeline", signal: "Runtime", current: "8m 42s", previous: "5m 55s", status: "Warning" as const },
    { id: "billing-postgres", resource: "Billing PostgreSQL", type: "Data Source", signal: "Availability", current: "98.7%", previous: "99.9%", status: "Warning" as const },
    { id: "warehouse-sync", resource: "Risk Reporting", type: "Pipeline", signal: "Freshness", current: "3h 14m", previous: "52m", status: "Warning" as const },
];
