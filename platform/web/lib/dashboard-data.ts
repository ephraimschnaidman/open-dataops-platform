export type Status = "success" | "running" | "failed" | "warning" | "critical" | "healthy";
export interface Metric { label: string; value: string; detail: string; tone: "neutral" | "positive" | "warning"; }
export interface Issue { id: string; resource: string; kind: string; severity: "Critical" | "Warning"; time: string; description: string; owner: string; nextStep: string; }
export interface PipelineRun { id: string; pipeline: string; status: "Success" | "Running" | "Failed"; started: string; duration: string; records: string; trigger: string; }

export const metrics: Metric[] = [
    { label: "Pipelines", value: "13", detail: "Canonical configured pipelines", tone: "neutral" },
    { label: "Successful runs", value: "148", detail: "+4.2% vs. last 24h", tone: "positive" },
    { label: "Failed runs", value: "3", detail: "2 require investigation", tone: "warning" },
    { label: "Active alerts", value: "4", detail: "1 critical · 3 warning", tone: "warning" },
];

export const issues: Issue[] = [
    { id: "ALT-1042", resource: "Events Processing", kind: "Pipeline execution failing", severity: "Critical", time: "2 min ago", description: "Events Kafka rejected the configured SASL credentials during Extract for run_01J94EVT18.", owner: "Data Platform", nextStep: "Review Events Kafka authentication, correct the source condition, and retry the run." },
    { id: "ALT-1041", resource: "Billing PostgreSQL", kind: "Elevated connection latency", severity: "Warning", time: "5 min ago", description: "Connection latency measured 418 ms, above the 300 ms operational threshold.", owner: "Data Platform", nextStep: "Review database load and network routing." },
    { id: "ALT-1040", resource: "Billing Reconciliation", kind: "Order ID unique failed", severity: "Warning", time: "1 hr ago", description: "The blocking validation found 318 duplicate order_id values; expected 0.", owner: "Finance Data", nextStep: "Review duplicate order records before retrying the pipeline." },
    { id: "ALT-1038", resource: "Risk Reporting", kind: "Scheduled execution missed", severity: "Warning", time: "2 hrs ago", description: "The expected 8:00 AM execution did not start within its schedule window.", owner: "Analytics Engineering", nextStep: "Review the pipeline schedule and orchestration availability." },
];

export const pipelineRuns: PipelineRun[] = [
    { id: "run_01J92CING8", pipeline: "Customer Ingestion", status: "Success", started: "Today, 10:32", duration: "2m 14s", records: "124,892", trigger: "Scheduled" },
    { id: "run_01J91CPM41", pipeline: "Customer Profile Merge", status: "Running", started: "Today, 10:26", duration: "Running · 18m 42s", records: "—", trigger: "Scheduled" },
    { id: "run_01J94EVT18", pipeline: "Events Processing", status: "Failed", started: "Today, 10:41", duration: "1m 35s", records: "—", trigger: "Event" },
    { id: "run_01J92CVAL9", pipeline: "Customer Ingestion", status: "Success", started: "Today, 10:05", duration: "2m 20s", records: "123,704", trigger: "Scheduled" },
    { id: "run_01J96ORD57", pipeline: "Orders Incremental", status: "Success", started: "Today, 08:33", duration: "1m 52s", records: "96,412", trigger: "Retry" },
];

export const healthItems = [
    { label: "Data freshness", value: "96.8%", note: "1 pipeline delayed", tone: "warning" as const, progress: 96.8 },
    { label: "Validation pass rate", value: "97.8%", note: "2 checks require review", tone: "warning" as const, progress: 97.8 },
    { label: "Pipeline success rate", value: "98.7%", note: "Last 24 hours", tone: "healthy" as const, progress: 98.7 },
    { label: "Source connectivity", value: "3 / 5 active", note: "Events failed · Billing warning", tone: "warning" as const, progress: 60 },
];

export const activities = [
    { id: 1, type: "failed", text: "Events Processing failed during Extract", actor: "Production", time: "2 min ago" },
    { id: 2, type: "success", text: "Customer Ingestion completed successfully", actor: "Scheduler", time: "11 min ago" },
    { id: 3, type: "rule", text: "Order ID unique blocked Billing Reconciliation", actor: "Validation", time: "1 hr ago" },
    { id: 4, type: "connected", text: "Billing PostgreSQL latency remained elevated", actor: "Source Monitor", time: "5 min ago" },
];
