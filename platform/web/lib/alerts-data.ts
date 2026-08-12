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
        id: "ALT-1042", title: "Pipeline execution failing", severity: "Critical", status: "Open", resourceType: "Pipeline", resourceName: "Events Processing", resourceId: "events-processing", environment: "Production", platformCode: "PIPELINE_EXECUTION_FAILED", vendorCode: "SASL_AUTHENTICATION_FAILED", message: "Events Kafka rejected the configured SASL credentials during Extract.", recommendedAction: "Review the Events Kafka authentication and connection configuration, then retry after the source condition is corrected.", firstDetected: "Aug 10, 2026 · 10:42:38 AM", lastSeen: "Aug 10, 2026 · 10:43:00 AM", startedLabel: "2 min ago", lastSeenLabel: "2 min ago", occurrences: 1, runId: "run_01J94EVT18",
        history: [{ id: "1042-2", timestamp: "10:43:00 AM", event: "Authentication failure remained active", platformCode: "PIPELINE_EXECUTION_FAILED", kind: "Updated" }, { id: "1042-1", timestamp: "10:42:38 AM", event: "Alert opened after Events Kafka authentication failure", platformCode: "PIPELINE_EXECUTION_FAILED", kind: "Detected" }],
    },
    {
        id: "ALT-1041", title: "Elevated connection latency", severity: "Warning", status: "Acknowledged", resourceType: "Data Source", resourceName: "Billing PostgreSQL", resourceId: "billing-postgres", environment: "Production", platformCode: "SOURCE_LATENCY_ELEVATED", message: "Average database connection latency exceeded the configured operational threshold.", recommendedAction: "Review source health and database load before latency affects scheduled pipelines.", firstDetected: "Aug 10, 2026 · 10:01:00 AM", lastSeen: "Aug 10, 2026 · 10:40:11 AM", startedLabel: "42 min ago", lastSeenLabel: "5 min ago", occurrences: 7, acknowledgedAt: "Aug 10, 2026 · 10:21:16 AM",
        history: [{ id: "1041-3", timestamp: "10:40:11 AM", event: "Latency remained above threshold", platformCode: "SOURCE_LATENCY_ELEVATED", kind: "Updated" }, { id: "1041-2", timestamp: "10:21:16 AM", event: "Alert acknowledged", platformCode: "ALERT_ACKNOWLEDGED", kind: "Acknowledged" }, { id: "1041-1", timestamp: "10:01:00 AM", event: "Latency threshold exceeded", platformCode: "SOURCE_LATENCY_ELEVATED", kind: "Detected" }],
    },
    {
        id: "ALT-1040", title: "Order ID unique failed", severity: "Warning", status: "Open", resourceType: "Validation", resourceName: "Billing Reconciliation", resourceId: "billing-reconciliation", environment: "Production", platformCode: "VALIDATION_CHECK_FAILED", vendorCode: "CHECK_UNIQUENESS_VIOLATION", message: "The blocking Order ID unique check found 318 duplicates; expected 0 duplicates.", recommendedAction: "Review duplicate order records before retrying the pipeline.", firstDetected: "Aug 10, 2026 · 9:36:42 AM", lastSeen: "Aug 10, 2026 · 9:36:42 AM", startedLabel: "1 hr ago", lastSeenLabel: "1 hr ago", occurrences: 1, runId: "run_01J97BIL02",
        history: [{ id: "1040-1", timestamp: "9:36:42 AM", event: "Order ID unique failed with 318 duplicates", platformCode: "VALIDATION_CHECK_FAILED", kind: "Detected" }],
    },
    {
        id: "ALT-1039", title: "Source connection failed", severity: "Critical", status: "Resolved", resourceType: "Data Source", resourceName: "Production Warehouse", resourceId: "analytics-warehouse", environment: "Production", platformCode: "SOURCE_CONNECTION_FAILED", vendorCode: "SQLSTATE 08001", message: "The platform could not establish a connection to Production Warehouse.", recommendedAction: "Test the source connection and verify network availability.", firstDetected: "Aug 10, 2026 · 9:37:00 AM", lastSeen: "Aug 10, 2026 · 10:35:04 AM", startedLabel: "1 hr ago", lastSeenLabel: "8 min ago", occurrences: 5, resolvedAt: "Aug 10, 2026 · 10:36:00 AM", resolutionType: "Automatic",
        history: [{ id: "1039-2", timestamp: "10:35:04 AM", event: "Connection check failed again", platformCode: "SOURCE_CONNECTION_FAILED", kind: "Updated" }, { id: "1039-1", timestamp: "9:37:00 AM", event: "Source connection alert opened", platformCode: "SOURCE_CONNECTION_FAILED", kind: "Detected" }],
    },
    {
        id: "ALT-1038", title: "Scheduled execution missed", severity: "Warning", status: "Acknowledged", resourceType: "Pipeline", resourceName: "Risk Reporting", resourceId: "risk-reporting", environment: "Production", platformCode: "PIPELINE_SCHEDULE_MISSED", message: "The expected 8:00 AM execution did not start within the accepted schedule window.", recommendedAction: "Review the pipeline schedule and orchestration availability.", firstDetected: "Aug 10, 2026 · 8:10:00 AM", lastSeen: "Aug 10, 2026 · 10:30:00 AM", startedLabel: "2 hr ago", lastSeenLabel: "13 min ago", occurrences: 1, acknowledgedAt: "Aug 10, 2026 · 8:18:00 AM",
        history: [{ id: "1038-2", timestamp: "8:18:00 AM", event: "Alert acknowledged", platformCode: "ALERT_ACKNOWLEDGED", kind: "Acknowledged" }, { id: "1038-1", timestamp: "8:10:00 AM", event: "Missed schedule alert opened", platformCode: "PIPELINE_SCHEDULE_MISSED", kind: "Detected" }],
    },
    {
        id: "ALT-1037", title: "Extraction connection interrupted", severity: "Warning", status: "Resolved", resourceType: "Pipeline Run", resourceName: "Customer Ingestion", resourceId: "customer-ingestion", environment: "Production", platformCode: "PIPELINE_EXECUTION_FAILED", vendorCode: "SNOWFLAKE_CONNECTION_RESET", message: "Production Warehouse reset the connection during a historical extraction run.", recommendedAction: "No further action is required after the later successful execution.", firstDetected: "Aug 9, 2026 · 3:14:18 PM", lastSeen: "Aug 9, 2026 · 3:14:18 PM", startedLabel: "Yesterday", lastSeenLabel: "Yesterday", occurrences: 1, runId: "run_01JA7OLD40", resolvedAt: "Aug 9, 2026 · 3:34:00 PM", resolutionType: "Manual",
        history: [{ id: "1037-2", timestamp: "Aug 9 · 3:34 PM", event: "Alert resolved by operator", platformCode: "ALERT_RESOLVED", kind: "Resolved" }, { id: "1037-1", timestamp: "Aug 9 · 3:14:18 PM", event: "Historical extraction failure detected", platformCode: "PIPELINE_EXECUTION_FAILED", kind: "Detected" }],
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
