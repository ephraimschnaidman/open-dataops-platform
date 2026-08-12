import { DEMO_NOW, incidentCodes, incidentTimes, pipelineIds, runIds } from "@/lib/canonical-demo";

export type PipelineRunStatus = "Running" | "Success" | "Failed" | "Cancelled";
export type PipelineRunStage = "Extract" | "Transform" | "Validate" | "Load";
export type PipelineRunTrigger = "Scheduled" | "Manual" | "Retry" | "Event";
export type PipelineRunTimeRange = "hour" | "day" | "week" | "month";

export interface PipelineRun {
    id: string;
    pipelineId: string;
    pipelineName: string;
    status: PipelineRunStatus;
    stage: PipelineRunStage;
    trigger: PipelineRunTrigger;
    startedAt: string;
    durationSeconds?: number;
    records?: number;
    platformCode: string;
    vendorCode?: string;
    message: string;
    recommendedAction: string;
    retryOf?: string;
}

export const pipelineRunsReferenceTime = Date.parse(DEMO_NOW);

const minutesAgo = (minutes: number) => new Date(pipelineRunsReferenceTime - minutes * 60_000).toISOString();

export const pipelineRuns: PipelineRun[] = [
    { id: "run_01J91CPM41", pipelineId: "customer-profile-merge", pipelineName: "Customer Profile Merge", status: "Running", stage: "Transform", trigger: "Scheduled", startedAt: minutesAgo(18.7), platformCode: "PIPELINE_RUNNING", message: "The pipeline is currently transforming customer profiles.", recommendedAction: "No action is required while execution continues." },
    { id: runIds.customerIngestionSuccess, pipelineId: pipelineIds.customerIngestion, pipelineName: "Customer Ingestion", status: "Success", stage: "Load", trigger: "Scheduled", startedAt: incidentTimes.customerSuccess.runStarted, durationSeconds: 134, records: 124892, platformCode: "RUN_COMPLETED", message: "The pipeline completed successfully and all validation checks passed.", recommendedAction: "No action is required." },
    { id: runIds.customerIngestionValidationWarning, pipelineId: pipelineIds.customerIngestion, pipelineName: "Customer Ingestion", status: "Success", stage: "Load", trigger: "Scheduled", startedAt: incidentTimes.customerValidation.runStarted, durationSeconds: 140, records: 123704, platformCode: "RUN_COMPLETED", message: "The pipeline completed with a non-blocking customer email null-rate warning.", recommendedAction: "Review the validation warning before the next scheduled execution." },
    { id: "run_01J93MKT06", pipelineId: "marketing-attribution", pipelineName: "Marketing Attribution", status: "Success", stage: "Load", trigger: "Event", startedAt: minutesAgo(16), durationSeconds: 107, records: 68231, platformCode: "RUN_COMPLETED", message: "The pipeline completed successfully.", recommendedAction: "No action is required." },
    { id: runIds.eventsProcessingFailure, pipelineId: pipelineIds.eventsProcessing, pipelineName: "Events Processing", status: "Failed", stage: "Extract", trigger: "Event", startedAt: incidentTimes.events.runStarted, durationSeconds: 95, platformCode: incidentCodes.pipelineExecutionFailed, vendorCode: incidentCodes.eventsKafkaAuthenticationFailed, message: "Kafka broker authentication failed during extraction.", recommendedAction: "Review the Events Kafka authentication/connection configuration and retry the failed execution after the source condition is corrected." },
    { id: "run_01J95INV42", pipelineId: "inventory-snapshot", pipelineName: "Inventory Snapshot", status: "Success", stage: "Load", trigger: "Scheduled", startedAt: minutesAgo(42), durationSeconds: 56, records: 412038, platformCode: "RUN_COMPLETED", message: "The pipeline completed successfully.", recommendedAction: "No action is required." },
    { id: "run_01J96ORD57", pipelineId: "orders-incremental", pipelineName: "Orders Incremental", status: "Success", stage: "Load", trigger: "Retry", startedAt: minutesAgo(57), durationSeconds: 112, records: 96412, platformCode: "RUN_COMPLETED", message: "The retry execution completed successfully.", recommendedAction: "No action is required.", retryOf: "run_01J86ORDFL" },
    { id: runIds.billingValidationFailure, pipelineId: pipelineIds.billingReconciliation, pipelineName: "Billing Reconciliation", status: "Failed", stage: "Validate", trigger: "Scheduled", startedAt: incidentTimes.billing.runStarted, durationSeconds: 522, records: 118204, platformCode: incidentCodes.validationCheckFailed, vendorCode: incidentCodes.orderIdUniqueFailed, message: "The Order ID unique check found 318 duplicate order IDs during validation.", recommendedAction: "Review duplicate order records before retrying the pipeline." },
    { id: "run_01J98WAR03", pipelineId: "warehouse-sync", pipelineName: "Warehouse Sync", status: "Cancelled", stage: "Transform", trigger: "Manual", startedAt: minutesAgo(185), durationSeconds: 71, platformCode: "PIPELINE_RUN_CANCELLED", message: "Execution was cancelled by the user.", recommendedAction: "Retry when it is operationally safe to continue." },
    { id: runIds.warehouseValidationFailure, pipelineId: pipelineIds.warehouseSync, pipelineName: "Warehouse Sync", status: "Failed", stage: "Validate", trigger: "Scheduled", startedAt: "2026-08-10T12:40:00.000Z", durationSeconds: 132, records: 84091, platformCode: "VALIDATION_EXECUTION_FAILED", vendorCode: "SNOWFLAKE_QUERY_CONNECTION_RESET", message: "A validation query connection reset after the account freshness warning was recorded.", recommendedAction: "Restore Production Warehouse connectivity and rerun validation." },
    { id: "run_01J99RAW05", pipelineId: "raw-data-archive", pipelineName: "Raw Data Archive", status: "Success", stage: "Load", trigger: "Scheduled", startedAt: minutesAgo(305), durationSeconds: 379, records: 834190, platformCode: "RUN_COMPLETED", message: "The pipeline completed successfully.", recommendedAction: "No action is required." },
    { id: "run_01JA0CUS08", pipelineId: "customer-ingestion", pipelineName: "Customer Ingestion", status: "Success", stage: "Load", trigger: "Scheduled", startedAt: minutesAgo(488), durationSeconds: 129, records: 121047, platformCode: "RUN_COMPLETED", message: "The pipeline completed successfully.", recommendedAction: "No action is required." },
    { id: "run_01JA1MAN12", pipelineId: "manual-customer-export", pipelineName: "Manual Customer Export", status: "Success", stage: "Load", trigger: "Manual", startedAt: minutesAgo(735), durationSeconds: 266, records: 50122, platformCode: "RUN_COMPLETED", message: "The pipeline completed successfully.", recommendedAction: "No action is required." },
    { id: "run_01JA2ORD18", pipelineId: "orders-incremental", pipelineName: "Orders Incremental", status: "Success", stage: "Load", trigger: "Scheduled", startedAt: minutesAgo(1080), durationSeconds: 49, records: 95118, platformCode: "RUN_COMPLETED", message: "The pipeline completed successfully.", recommendedAction: "No action is required." },
    { id: "run_01JA3INV26", pipelineId: "inventory-snapshot", pipelineName: "Inventory Snapshot", status: "Success", stage: "Load", trigger: "Scheduled", startedAt: minutesAgo(1560), durationSeconds: 59, records: 409872, platformCode: "RUN_COMPLETED", message: "The pipeline completed successfully.", recommendedAction: "No action is required." },
    { id: "run_01JA4MKT04", pipelineId: "marketing-attribution", pipelineName: "Marketing Attribution", status: "Success", stage: "Load", trigger: "Event", startedAt: minutesAgo(4 * 1440), durationSeconds: 118, records: 70192, platformCode: "RUN_COMPLETED", message: "The pipeline completed successfully.", recommendedAction: "No action is required." },
    { id: "run_01JA5BIL09", pipelineId: "billing-reconciliation", pipelineName: "Billing Reconciliation", status: "Success", stage: "Load", trigger: "Scheduled", startedAt: minutesAgo(9 * 1440), durationSeconds: 663, records: 116903, platformCode: "RUN_COMPLETED", message: "The pipeline completed successfully.", recommendedAction: "No action is required." },
    { id: "run_01JA6RAW24", pipelineId: "raw-data-archive", pipelineName: "Raw Data Archive", status: "Success", stage: "Load", trigger: "Scheduled", startedAt: minutesAgo(24 * 1440), durationSeconds: 391, records: 810445, platformCode: "RUN_COMPLETED", message: "The pipeline completed successfully.", recommendedAction: "No action is required." },
    { id: runIds.customerIngestionHistoricalFailure, pipelineId: pipelineIds.customerIngestion, pipelineName: "Customer Ingestion", status: "Failed", stage: "Extract", trigger: "Scheduled", startedAt: incidentTimes.customerHistoricalFailure.runStarted, durationSeconds: 18, platformCode: incidentCodes.pipelineExecutionFailed, vendorCode: "SNOWFLAKE_CONNECTION_RESET", message: "The Production Warehouse connection was interrupted during extraction.", recommendedAction: "Verify Production Warehouse connectivity and retry the run." },
];

export const timeRangeOptions: Array<{ label: string; value: PipelineRunTimeRange; minutes: number }> = [
    { label: "Last hour", value: "hour", minutes: 60 },
    { label: "Last 24 hours", value: "day", minutes: 1440 },
    { label: "Last 7 days", value: "week", minutes: 10080 },
    { label: "Last 30 days", value: "month", minutes: 43200 },
];

export function sortPipelineRuns(runs: PipelineRun[]) {
    return [...runs].sort((a, b) => Number(b.status === "Running") - Number(a.status === "Running") || Date.parse(b.startedAt) - Date.parse(a.startedAt));
}

export function formatRunDuration(run: PipelineRun, now = Date.now()) {
    const seconds = run.status === "Running" ? Math.max(1, Math.floor((now - Date.parse(run.startedAt)) / 1000)) : run.durationSeconds;
    if (seconds === undefined) return "—";
    const minutes = Math.floor(seconds / 60);
    const remainder = seconds % 60;
    const value = minutes ? `${minutes}m ${remainder}s` : `${remainder}s`;
    return run.status === "Running" ? `Running · ${value}` : value;
}

export function formatStartedAt(startedAt: string, now = Date.now()) {
    const seconds = Math.max(1, Math.floor((now - Date.parse(startedAt)) / 1000));
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hr ago`;
    const days = Math.floor(hours / 24);
    return `${days} ${days === 1 ? "day" : "days"} ago`;
}
