export type AlertSeverity = "Critical" | "Warning";
export type AlertWorkflowStatus = "Open" | "Acknowledged" | "Resolved";
export type AlertResourceType = "Pipeline" | "Pipeline Run" | "Data Source" | "Validation" | "Platform";
export type AlertEnvironment = "Production" | "Staging" | "Development";
export type AlertsQaState = "mixed" | "critical" | "warning" | "acknowledged" | "no-active" | "no-alerts" | "resolved" | "filtered-empty" | "stale" | "error" | "partial-summary";

export interface AlertOccurrence {
    id: string;
    timestamp: string;
    event: string;
    platformCode: string;
    kind: "Detected" | "Updated" | "Acknowledged" | "Resolved" | "Reopened";
}

export interface OperationalAlert {
    id: string;
    title: string;
    severity: AlertSeverity;
    status: AlertWorkflowStatus;
    resourceType: AlertResourceType;
    resourceName: string;
    resourceId?: string;
    environment: AlertEnvironment;
    platformCode: string;
    vendorCode?: string;
    message: string;
    recommendedAction: string;
    firstDetected: string;
    lastSeen: string;
    startedLabel: string;
    lastSeenLabel: string;
    occurrences: number;
    runId?: string;
    acknowledgedAt?: string;
    resolvedAt?: string;
    resolutionType?: "Manual" | "Automatic";
    history: AlertOccurrence[];
}

export const alerts: OperationalAlert[] = [
    {
        id: "ALT-1042", title: "Pipeline execution failing", severity: "Critical", status: "Open", resourceType: "Pipeline", resourceName: "Events Processing", resourceId: "events-processing", environment: "Production", platformCode: "PIPELINE_EXECUTION_FAILED", vendorCode: "SQLSTATE 08006", message: "PostgreSQL terminated the connection during pipeline extraction.", recommendedAction: "Verify source connectivity, inspect the failed run, and retry after correcting the connection issue.", firstDetected: "Aug 10, 2026 · 10:24:02 AM", lastSeen: "Aug 10, 2026 · 10:42:17 AM", startedLabel: "18 min ago", lastSeenLabel: "1 min ago", occurrences: 4, runId: "run_01J94EVT18",
        history: [{ id: "1042-4", timestamp: "10:42:17 AM", event: "Failure detected again during extraction", platformCode: "PIPELINE_EXECUTION_FAILED", kind: "Updated" }, { id: "1042-3", timestamp: "10:36:09 AM", event: "Third occurrence detected", platformCode: "PIPELINE_EXECUTION_FAILED", kind: "Updated" }, { id: "1042-2", timestamp: "10:29:44 AM", event: "Repeated connection failure detected", platformCode: "PIPELINE_EXECUTION_FAILED", kind: "Updated" }, { id: "1042-1", timestamp: "10:24:02 AM", event: "Alert opened after execution failure", platformCode: "PIPELINE_EXECUTION_FAILED", kind: "Detected" }],
    },
    {
        id: "ALT-1041", title: "Elevated connection latency", severity: "Warning", status: "Acknowledged", resourceType: "Data Source", resourceName: "Billing PostgreSQL", resourceId: "billing-postgres", environment: "Production", platformCode: "SOURCE_LATENCY_ELEVATED", vendorCode: "418 ms", message: "Average database connection latency exceeded the configured operational threshold.", recommendedAction: "Review source health and database load before latency affects scheduled pipelines.", firstDetected: "Aug 10, 2026 · 10:01:00 AM", lastSeen: "Aug 10, 2026 · 10:40:11 AM", startedLabel: "42 min ago", lastSeenLabel: "3 min ago", occurrences: 7, acknowledgedAt: "Aug 10, 2026 · 10:21:16 AM",
        history: [{ id: "1041-3", timestamp: "10:40:11 AM", event: "Latency remained above threshold", platformCode: "SOURCE_LATENCY_ELEVATED", kind: "Updated" }, { id: "1041-2", timestamp: "10:21:16 AM", event: "Alert acknowledged", platformCode: "ALERT_ACKNOWLEDGED", kind: "Acknowledged" }, { id: "1041-1", timestamp: "10:01:00 AM", event: "Latency threshold exceeded", platformCode: "SOURCE_LATENCY_ELEVATED", kind: "Detected" }],
    },
    {
        id: "ALT-1040", title: "Validation check failed", severity: "Warning", status: "Open", resourceType: "Validation", resourceName: "Billing Reconciliation", resourceId: "billing-reconciliation", environment: "Production", platformCode: "VALIDATION_CHECK_FAILED", vendorCode: "CHECK_NULL_RATE_THRESHOLD", message: "One validation rule failed during the latest pipeline execution.", recommendedAction: "Review the failed validation result before retrying the run.", firstDetected: "Aug 10, 2026 · 9:58:00 AM", lastSeen: "Aug 10, 2026 · 10:38:21 AM", startedLabel: "1 hr ago", lastSeenLabel: "5 min ago", occurrences: 2, runId: "run_01J97BIL02",
        history: [{ id: "1040-2", timestamp: "10:38:21 AM", event: "Validation failure detected on retry", platformCode: "VALIDATION_CHECK_FAILED", kind: "Updated" }, { id: "1040-1", timestamp: "9:58:00 AM", event: "Validation alert opened", platformCode: "VALIDATION_CHECK_FAILED", kind: "Detected" }],
    },
    {
        id: "ALT-1039", title: "Source connection failed", severity: "Critical", status: "Open", resourceType: "Data Source", resourceName: "Production Warehouse", environment: "Production", platformCode: "SOURCE_CONNECTION_FAILED", vendorCode: "SQLSTATE 08001", message: "The platform could not establish a connection to Production Warehouse.", recommendedAction: "Test the source connection and verify network availability.", firstDetected: "Aug 10, 2026 · 9:37:00 AM", lastSeen: "Aug 10, 2026 · 10:35:04 AM", startedLabel: "1 hr ago", lastSeenLabel: "8 min ago", occurrences: 5,
        history: [{ id: "1039-2", timestamp: "10:35:04 AM", event: "Connection check failed again", platformCode: "SOURCE_CONNECTION_FAILED", kind: "Updated" }, { id: "1039-1", timestamp: "9:37:00 AM", event: "Source connection alert opened", platformCode: "SOURCE_CONNECTION_FAILED", kind: "Detected" }],
    },
    {
        id: "ALT-1038", title: "Scheduled execution missed", severity: "Warning", status: "Acknowledged", resourceType: "Pipeline", resourceName: "Risk Reporting", environment: "Production", platformCode: "PIPELINE_SCHEDULE_MISSED", message: "The expected 8:00 AM execution did not start within the accepted schedule window.", recommendedAction: "Review the pipeline schedule and orchestration availability.", firstDetected: "Aug 10, 2026 · 8:10:00 AM", lastSeen: "Aug 10, 2026 · 10:30:00 AM", startedLabel: "2 hr ago", lastSeenLabel: "13 min ago", occurrences: 1, acknowledgedAt: "Aug 10, 2026 · 8:18:00 AM",
        history: [{ id: "1038-2", timestamp: "8:18:00 AM", event: "Alert acknowledged", platformCode: "ALERT_ACKNOWLEDGED", kind: "Acknowledged" }, { id: "1038-1", timestamp: "8:10:00 AM", event: "Missed schedule alert opened", platformCode: "PIPELINE_SCHEDULE_MISSED", kind: "Detected" }],
    },
    {
        id: "ALT-1037", title: "Extraction connection interrupted", severity: "Warning", status: "Resolved", resourceType: "Pipeline Run", resourceName: "Customer Ingestion", resourceId: "customer-ingestion", environment: "Production", platformCode: "PIPELINE_EXECUTION_FAILED", vendorCode: "SQLSTATE 08006", message: "A transient connection interruption stopped one extraction run.", recommendedAction: "No further action is required after the successful retry.", firstDetected: "Aug 9, 2026 · 3:14:00 PM", lastSeen: "Aug 9, 2026 · 3:31:00 PM", startedLabel: "Yesterday", lastSeenLabel: "Yesterday", occurrences: 2, runId: "run_01J92CING8", resolvedAt: "Aug 9, 2026 · 3:34:00 PM", resolutionType: "Manual",
        history: [{ id: "1037-3", timestamp: "Aug 9 · 3:34 PM", event: "Alert resolved by operator", platformCode: "ALERT_RESOLVED", kind: "Resolved" }, { id: "1037-2", timestamp: "Aug 9 · 3:31 PM", event: "Retry completed successfully", platformCode: "RUN_COMPLETED", kind: "Updated" }, { id: "1037-1", timestamp: "Aug 9 · 3:14 PM", event: "Extraction failure detected", platformCode: "PIPELINE_EXECUTION_FAILED", kind: "Detected" }],
    },
    {
        id: "ALT-1036", title: "Schedule delay detected", severity: "Warning", status: "Resolved", resourceType: "Pipeline", resourceName: "Warehouse Sync", resourceId: "warehouse-sync", environment: "Production", platformCode: "PIPELINE_SCHEDULE_DELAYED", message: "One scheduled execution started eight minutes outside its expected window.", recommendedAction: "No action is required; subsequent executions returned to schedule.", firstDetected: "Aug 8, 2026 · 9:08:00 AM", lastSeen: "Aug 8, 2026 · 9:23:00 AM", startedLabel: "2 days ago", lastSeenLabel: "2 days ago", occurrences: 1, resolvedAt: "Aug 8, 2026 · 9:30:00 AM", resolutionType: "Automatic",
        history: [{ id: "1036-2", timestamp: "Aug 8 · 9:30 AM", event: "Alert resolved automatically after schedule recovery", platformCode: "ALERT_AUTO_RESOLVED", kind: "Resolved" }, { id: "1036-1", timestamp: "Aug 8 · 9:08 AM", event: "Schedule delay detected", platformCode: "PIPELINE_SCHEDULE_DELAYED", kind: "Detected" }],
    },
];

const severityOrder: Record<AlertSeverity, number> = { Critical: 0, Warning: 1 };
const workflowOrder: Record<AlertWorkflowStatus, number> = { Open: 0, Acknowledged: 1, Resolved: 2 };

export function sortAlerts(items: OperationalAlert[]) {
    return [...items].sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity] || workflowOrder[a.status] - workflowOrder[b.status] || b.lastSeen.localeCompare(a.lastSeen));
}

export function getAlert(alertId: string) {
    return alerts.find((alert) => alert.id === alertId);
}

const overrideKey = "datum-alert-status-overrides";
export function readAlertOverrides(): Record<string, AlertWorkflowStatus> {
    try { return JSON.parse(window.sessionStorage.getItem(overrideKey) ?? "{}"); } catch { return {}; }
}
export function persistAlertStatus(alertId: string, status: AlertWorkflowStatus) {
    const overrides = readAlertOverrides();
    window.sessionStorage.setItem(overrideKey, JSON.stringify({ ...overrides, [alertId]: status }));
}
