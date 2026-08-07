export type Status = "success" | "running" | "failed" | "warning" | "critical" | "healthy";

export interface Metric {
    label: string;
    value: string;
    detail: string;
    tone: "neutral" | "positive" | "warning";
}

export interface Issue {
    id: string;
    resource: string;
    kind: string;
    severity: "Critical" | "Warning";
    time: string;
    description: string;
    owner: string;
    nextStep: string;
}

export interface PipelineRun {
    id: string;
    pipeline: string;
    status: "Success" | "Running" | "Failed";
    started: string;
    duration: string;
    records: string;
    trigger: string;
}

export const metrics: Metric[] = [
    { label: "Pipelines", value: "12", detail: "10 scheduled · 2 manual", tone: "neutral" },
    { label: "Successful runs", value: "148", detail: "+4.2% vs. last 24h", tone: "positive" },
    { label: "Failed runs", value: "3", detail: "2 require investigation", tone: "warning" },
    { label: "Active alerts", value: "4", detail: "1 critical · 3 warning", tone: "warning" },
];

export const issues: Issue[] = [
    { id: "inc-2048", resource: "customer_daily_sync", kind: "Pipeline failed", severity: "Critical", time: "8 min ago", description: "The transform step exited after three retry attempts. The latest successful run completed yesterday at 06:13 UTC.", owner: "Data Platform", nextStep: "Inspect the failed transform task and retry from the last checkpoint." },
    { id: "inc-2047", resource: "orders_raw", kind: "Freshness threshold exceeded", severity: "Warning", time: "22 min ago", description: "Source data is 52 minutes behind the expected arrival window of 30 minutes.", owner: "Analytics Engineering", nextStep: "Check the upstream replication slot and source write activity." },
    { id: "inc-2046", resource: "payments_validation", kind: "184 invalid records", severity: "Warning", time: "41 min ago", description: "The latest batch contains null payment status values above the configured tolerance.", owner: "Finance Data", nextStep: "Review rejected records and confirm the upstream schema contract." },
    { id: "inc-2043", resource: "warehouse_connection", kind: "Connection latency elevated", severity: "Warning", time: "1 hr ago", description: "Median query connection time has exceeded 800ms for the last fifteen minutes.", owner: "Data Platform", nextStep: "Review warehouse load and connection pool saturation." },
];

export const pipelineRuns: PipelineRun[] = [
    { id: "run-9321", pipeline: "daily_finance_rollup", status: "Success", started: "Today, 09:42", duration: "4m 18s", records: "1.24M", trigger: "Scheduled" },
    { id: "run-9320", pipeline: "product_events_hourly", status: "Running", started: "Today, 09:38", duration: "6m 02s", records: "842K", trigger: "Scheduled" },
    { id: "run-9319", pipeline: "customer_daily_sync", status: "Failed", started: "Today, 09:31", duration: "2m 44s", records: "—", trigger: "Scheduled" },
    { id: "run-9318", pipeline: "orders_incremental", status: "Success", started: "Today, 09:15", duration: "1m 52s", records: "96.4K", trigger: "Event" },
    { id: "run-9317", pipeline: "inventory_snapshot", status: "Success", started: "Today, 09:00", duration: "3m 06s", records: "412K", trigger: "Manual" },
];

export const healthItems = [
    { label: "Data freshness", value: "96.8%", note: "1 source delayed", tone: "warning" as const, progress: 96.8 },
    { label: "Validation pass rate", value: "99.2%", note: "Last 24 hours", tone: "healthy" as const, progress: 99.2 },
    { label: "Pipeline success rate", value: "98.0%", note: "148 of 151 runs", tone: "healthy" as const, progress: 98 },
    { label: "Source connectivity", value: "11 / 12", note: "1 degraded", tone: "warning" as const, progress: 91.7 },
];

export const activities = [
    { id: 1, type: "failed", text: "Pipeline customer_daily_sync failed", actor: "Production", time: "8 min ago" },
    { id: 2, type: "connected", text: "Source billing_postgres connected", actor: "Maya Chen", time: "34 min ago" },
    { id: 3, type: "rule", text: "Validation rule added to orders", actor: "Jon Bell", time: "1 hr ago" },
    { id: 4, type: "success", text: "Pipeline daily_finance_rollup completed", actor: "Scheduler", time: "2 hrs ago" },
];
