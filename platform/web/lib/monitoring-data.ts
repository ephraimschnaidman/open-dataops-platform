export type MonitoringEnvironment = "All" | "Production" | "Staging" | "Development";
export type MonitoringResourceType = "All" | "Pipelines" | "Data Sources";
export type MonitoringTimeRange = "1h" | "6h" | "24h" | "7d" | "30d";
export type MonitoringHealthStatus = "Healthy" | "Warning" | "Critical";
export type MonitoringQaState = "warning" | "healthy" | "critical" | "no-issues" | "empty" | "stale" | "error" | "partial";

export interface MonitoringMetricSet {
    successRate: string;
    successful: number;
    failed: number;
    avgRuntime: string;
    adherence: string;
    healthySources: string;
    previousSuccessRate: string;
    successfulDelta: string;
}

export interface ActiveIssue {
    id: string;
    severity: "Critical" | "Warning";
    resourceType: "Pipeline" | "Data Source";
    resource: string;
    resourceId: string;
    issue: string;
    platformCode: string;
    vendorCode?: string;
    message: string;
    recommendedAction: string;
    since: string;
    minutesAgo: number;
    runId?: string;
    action: "Investigate" | "View Source" | "Review Validation";
}

export interface PipelineHealthRow {
    id: string;
    name: string;
    environment: Exclude<MonitoringEnvironment, "All">;
    status: "Healthy" | "Warning" | "Failed" | "Disabled";
    successRate: string;
    lastRun: string;
    avgRuntime: string;
    schedule: string;
    platformCode?: string;
}

export interface SourceHealthRow {
    id?: string;
    name: string;
    environment: Exclude<MonitoringEnvironment, "All">;
    status: "Healthy" | "Warning" | "Failed" | "Disabled";
    availability: string;
    latency: string;
    lastCheck: string;
    platformCode?: string;
    vendorCode?: string;
}

export interface ScheduleIssue {
    id: string;
    pipelineId?: string;
    pipeline: string;
    environment: Exclude<MonitoringEnvironment, "All">;
    status: "Late" | "Missed";
    expected: string;
    actual: string;
    delay?: string;
    platformCode: string;
}

export interface MonitoringEvent {
    id: string;
    time: string;
    resource: string;
    resourceType: "Pipeline" | "Data Source";
    resourceId: string;
    environment: Exclude<MonitoringEnvironment, "All">;
    description: string;
    platformCode: string;
    tone: "success" | "warning" | "error";
    runId?: string;
    logs?: boolean;
}

export interface TrendPoint {
    label: string;
    success: number;
    failed: number;
    runtime: number;
}

export const timeRangeOptions: Array<{ label: string; value: MonitoringTimeRange }> = [
    { label: "Last 1 hour", value: "1h" }, { label: "Last 6 hours", value: "6h" }, { label: "Last 24 hours", value: "24h" }, { label: "Last 7 days", value: "7d" }, { label: "Last 30 days", value: "30d" },
];

export const metricsByRange: Record<MonitoringTimeRange, MonitoringMetricSet> = {
    "1h": { successRate: "97.8%", successful: 45, failed: 1, avgRuntime: "2m 11s", adherence: "100%", healthySources: "7 / 8", previousSuccessRate: "98.1%", successfulDelta: "+3 vs previous hour" },
    "6h": { successRate: "98.2%", successful: 54, failed: 1, avgRuntime: "2m 15s", adherence: "99.1%", healthySources: "7 / 8", previousSuccessRate: "97.9%", successfulDelta: "+4 vs previous 6h" },
    "24h": { successRate: "98.7%", successful: 142, failed: 3, avgRuntime: "2m 18s", adherence: "99.3%", healthySources: "7 / 8", previousSuccessRate: "98.3%", successfulDelta: "+2 vs previous 24h" },
    "7d": { successRate: "98.5%", successful: 982, failed: 15, avgRuntime: "2m 16s", adherence: "99.0%", healthySources: "7 / 8", previousSuccessRate: "98.1%", successfulDelta: "+19 vs previous 7d" },
    "30d": { successRate: "98.2%", successful: 4216, failed: 77, avgRuntime: "2m 21s", adherence: "98.8%", healthySources: "7 / 8", previousSuccessRate: "98.4%", successfulDelta: "+84 vs previous 30d" },
};

export const activeIssues: ActiveIssue[] = [
    { id: "issue-events", severity: "Critical", resourceType: "Pipeline", resource: "Events Processing", resourceId: "events-processing", issue: "Pipeline execution failing", platformCode: "PIPELINE_EXECUTION_FAILED", vendorCode: "SASL_AUTHENTICATION_FAILED", message: "Events Kafka authentication failed during Extract.", recommendedAction: "Review the Events Kafka authentication and connection configuration, then retry after the source condition is corrected.", since: "Since 2 min ago", minutesAgo: 2, runId: "run_01J94EVT18", action: "Investigate" },
    { id: "issue-billing-source", severity: "Warning", resourceType: "Data Source", resource: "Billing PostgreSQL", resourceId: "billing-postgres", issue: "Elevated connection latency", platformCode: "SOURCE_LATENCY_ELEVATED", message: "Connection latency is above the configured operational threshold.", recommendedAction: "Review source health and database load.", since: "Since 42 min ago", minutesAgo: 42, action: "View Source" },
    { id: "issue-billing-validation", severity: "Warning", resourceType: "Pipeline", resource: "Billing Reconciliation", resourceId: "billing-reconciliation", issue: "Validation check failed", platformCode: "VALIDATION_CHECK_FAILED", vendorCode: "CHECK_UNIQUENESS_VIOLATION", message: "Order ID unique found 318 duplicates; expected 0 duplicates.", recommendedAction: "Review duplicate order records before retrying the pipeline.", since: "Since 1 hr ago", minutesAgo: 60, runId: "run_01J97BIL02", action: "Review Validation" },
];

export const pipelineHealth: PipelineHealthRow[] = [
    { id: "events-processing", name: "Events Processing", environment: "Production", status: "Failed", successRate: "82.4%", lastRun: "2 min ago", avgRuntime: "41s", schedule: "Continuous", platformCode: "PIPELINE_EXECUTION_FAILED" },
    { id: "billing-reconciliation", name: "Billing Reconciliation", environment: "Production", status: "Warning", successRate: "96.2%", lastRun: "1 hr ago", avgRuntime: "8m 41s", schedule: "Daily at 06:00", platformCode: "VALIDATION_CHECK_FAILED" },
    { id: "customer-ingestion", name: "Customer Ingestion", environment: "Production", status: "Healthy", successRate: "99.6%", lastRun: "11 min ago", avgRuntime: "2m 14s", schedule: "Hourly" },
    { id: "warehouse-sync", name: "Warehouse Sync", environment: "Production", status: "Healthy", successRate: "100%", lastRun: "12 min ago", avgRuntime: "4m 02s", schedule: "Every 15 min" },
    { id: "marketing-attribution", name: "Marketing Attribution", environment: "Staging", status: "Healthy", successRate: "99.1%", lastRun: "6 min ago", avgRuntime: "1m 47s", schedule: "Every 15 min" },
    { id: "legacy-reporting", name: "Legacy Reporting", environment: "Development", status: "Disabled", successRate: "—", lastRun: "4 days ago", avgRuntime: "—", schedule: "Paused" },
];

export const sourceHealth: SourceHealthRow[] = [
    { id: "analytics-warehouse", name: "Production Warehouse", environment: "Production", status: "Healthy", availability: "99.99%", latency: "84 ms", lastCheck: "2 min ago" },
    { id: "billing-postgres", name: "Billing PostgreSQL", environment: "Production", status: "Warning", availability: "99.4%", latency: "418 ms", lastCheck: "5 min ago", platformCode: "SOURCE_LATENCY_ELEVATED" },
    { id: "events-kafka", name: "Events Kafka", environment: "Production", status: "Failed", availability: "99.2%", latency: "—", lastCheck: "2 min ago", platformCode: "SOURCE_AUTHENTICATION_FAILED", vendorCode: "SASL_AUTHENTICATION_FAILED" },
    { id: "customer-sqlserver", name: "Legacy SQL Server", environment: "Development", status: "Disabled", availability: "—", latency: "—", lastCheck: "4 days ago" },
];

export const scheduleIssues: ScheduleIssue[] = [
    { id: "schedule-export", pipelineId: "manual-customer-export", pipeline: "Manual Customer Export", environment: "Staging", status: "Late", expected: "9:00 AM", actual: "9:08 AM", delay: "8m", platformCode: "PIPELINE_SCHEDULE_DELAYED" },
    { id: "schedule-risk", pipelineId: "risk-reporting", pipeline: "Risk Reporting", environment: "Production", status: "Missed", expected: "8:00 AM", actual: "—", platformCode: "PIPELINE_SCHEDULE_MISSED" },
];

export const recentEvents: MonitoringEvent[] = [
    { id: "event-1", time: "10:34 AM", resource: "Customer Ingestion", resourceType: "Pipeline", resourceId: "customer-ingestion", environment: "Production", description: "completed successfully", platformCode: "RUN_COMPLETED", tone: "success", runId: "run_01J92CING8" },
    { id: "event-2", time: "10:42 AM", resource: "Events Processing", resourceType: "Pipeline", resourceId: "events-processing", environment: "Production", description: "execution failed", platformCode: "PIPELINE_EXECUTION_FAILED", tone: "error", runId: "run_01J94EVT18", logs: true },
    { id: "event-3", time: "10:19 AM", resource: "Billing PostgreSQL", resourceType: "Data Source", resourceId: "billing-postgres", environment: "Production", description: "latency exceeded threshold", platformCode: "SOURCE_LATENCY_ELEVATED", tone: "warning" },
    { id: "event-4", time: "9:36 AM", resource: "Billing Reconciliation", resourceType: "Pipeline", resourceId: "billing-reconciliation", environment: "Production", description: "Order ID unique failed with 318 duplicates", platformCode: "VALIDATION_CHECK_FAILED", tone: "warning", runId: "run_01J97BIL02" },
    { id: "event-5", time: "10:07 AM", resource: "Customer Ingestion", resourceType: "Pipeline", resourceId: "customer-ingestion", environment: "Production", description: "completed with a customer email validation warning", platformCode: "RUN_COMPLETED", tone: "success", runId: "run_01J92CVAL9" },
    { id: "event-6", time: "9:08 AM", resource: "Manual Customer Export", resourceType: "Pipeline", resourceId: "manual-customer-export", environment: "Staging", description: "started outside its schedule window", platformCode: "PIPELINE_SCHEDULE_DELAYED", tone: "warning" },
];

const labels: Record<MonitoringTimeRange, string[]> = {
    "1h": ["9:50", "10:00", "10:10", "10:20", "10:30", "10:40"],
    "6h": ["5 AM", "6 AM", "7 AM", "8 AM", "9 AM", "10 AM"],
    "24h": ["12 AM", "4 AM", "8 AM", "12 PM", "4 PM", "8 PM"],
    "7d": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "30d": ["Jul 12", "Jul 17", "Jul 22", "Jul 27", "Aug 1", "Aug 6", "Aug 10"],
};

export const trendsByRange = Object.fromEntries((Object.keys(labels) as MonitoringTimeRange[]).map((range) => [range, labels[range].map((label, index) => ({ label, success: [97.8, 99.1, 98.5, 97.2, 98.8, 98.7, 99.0][index], failed: [1.8, 0.6, 1.1, 2.2, 0.8, 1.0, 0.5][index], runtime: [121, 126, 129, 134, 137, 138, 136][index] }))])) as Record<MonitoringTimeRange, TrendPoint[]>;

const severityOrder = { Critical: 0, Warning: 1 };
export function sortActiveIssues(issues: ActiveIssue[]) {
    return [...issues].sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity] || a.minutesAgo - b.minutesAgo);
}
