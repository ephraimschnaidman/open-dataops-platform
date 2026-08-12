import { incidentCodes, incidentTimes, pipelineIds, runIds } from "@/lib/canonical-demo";
import type { PipelineRunStatus, PipelineRunTrigger } from "@/lib/pipeline-runs-data";

export type ExecutionStageState = "Completed" | "Running" | "Failed" | "Pending" | "Cancelled";

export interface ExecutionStage {
    name: "Extract" | "Transform" | "Validate" | "Load";
    state: ExecutionStageState;
    duration?: string;
    recordDetail?: string;
    platformCode?: string;
    vendorCode?: string;
    message?: string;
}

export interface RunValidationResult {
    checks: number;
    passing: number;
    failed: number;
    evaluatedAt?: string;
    platformCode?: string;
    vendorCode?: string;
    failure?: { check: string; field: string; observed: string; threshold: string };
}

export interface RelatedRun {
    id: string;
    status: PipelineRunStatus;
    startedAt: string;
    duration: string;
    trigger: PipelineRunTrigger;
}

export interface RunEvent {
    id: string;
    timestamp: string;
    title: string;
    code: string;
    tone: "success" | "running" | "error" | "neutral";
}

export interface PipelineRunDetail {
    id: string;
    pipelineId: string;
    pipelineName: string;
    environment: "Production" | "Staging" | "Development";
    status: PipelineRunStatus;
    trigger: PipelineRunTrigger;
    startedAt: string;
    finishedAt?: string;
    duration: string;
    records?: number;
    platformCode: string;
    vendorCode?: string;
    message: string;
    recommendedAction: string;
    stages: ExecutionStage[];
    validation: RunValidationResult;
    relatedRuns: RelatedRun[];
    events: RunEvent[];
}

const successfulCustomerStages: ExecutionStage[] = [
    { name: "Extract", state: "Completed", duration: "38s", recordDetail: "125,104 records read" },
    { name: "Transform", state: "Completed", duration: "52s", recordDetail: "124,892 records produced" },
    { name: "Validate", state: "Completed", duration: "18s", recordDetail: "12 checks passed" },
    { name: "Load", state: "Completed", duration: "26s", recordDetail: "124,892 records written" },
];

export const pipelineRunDetails: PipelineRunDetail[] = [
    {
        id: runIds.customerIngestionSuccess, pipelineId: pipelineIds.customerIngestion, pipelineName: "Customer Ingestion", environment: "Production", status: "Success", trigger: "Scheduled", startedAt: incidentTimes.customerSuccess.runStarted, finishedAt: incidentTimes.customerSuccess.completed, duration: "2m 14s", records: 124892, platformCode: "RUN_COMPLETED", message: "Pipeline execution completed successfully and all 12 validation checks passed.", recommendedAction: "No corrective action is required.", stages: successfulCustomerStages,
        validation: { checks: 12, passing: 12, failed: 0, evaluatedAt: incidentTimes.customerSuccess.validationCompleted },
        relatedRuns: [
            { id: runIds.customerIngestionValidationWarning, status: "Success", startedAt: incidentTimes.customerValidation.runStarted, duration: "2m 20s", trigger: "Scheduled" },
            { id: runIds.customerIngestionHistoricalFailure, status: "Failed", startedAt: incidentTimes.customerHistoricalFailure.runStarted, duration: "18s", trigger: "Scheduled" },
        ],
        events: [
            { id: "s1", timestamp: incidentTimes.customerSuccess.runStarted, title: "Run started", code: "RUN_STARTED", tone: "neutral" },
            { id: "s2", timestamp: "2026-08-10T14:32:38.000Z", title: "Extract stage completed", code: "STAGE_COMPLETED", tone: "success" },
            { id: "s3", timestamp: "2026-08-10T14:33:30.000Z", title: "Transform stage completed", code: "STAGE_COMPLETED", tone: "success" },
            { id: "s4", timestamp: incidentTimes.customerSuccess.validationCompleted, title: "Validation completed", code: "STAGE_COMPLETED", tone: "success" },
            { id: "s5", timestamp: incidentTimes.customerSuccess.completed, title: "Run completed", code: "RUN_COMPLETED", tone: "success" },
        ],
    },
    {
        id: runIds.customerIngestionValidationWarning, pipelineId: pipelineIds.customerIngestion, pipelineName: "Customer Ingestion", environment: "Production", status: "Success", trigger: "Scheduled", startedAt: incidentTimes.customerValidation.runStarted, finishedAt: incidentTimes.customerValidation.completed, duration: "2m 20s", records: 123704, platformCode: "RUN_COMPLETED_WITH_WARNINGS", vendorCode: incidentCodes.customerEmailNullRateFailed, message: "The run completed, but customer email null rate exceeded its warning threshold.", recommendedAction: "Review upstream email capture and remediate null customer_email values before the next scheduled run.",
        stages: [{ name: "Extract", state: "Completed", duration: "39s", recordDetail: "124,011 records read" }, { name: "Transform", state: "Completed", duration: "54s", recordDetail: "123,704 records produced" }, { name: "Validate", state: "Completed", duration: "12s", recordDetail: "11 checks passed; 1 warning", platformCode: incidentCodes.validationCheckFailed, vendorCode: incidentCodes.customerEmailNullRateFailed }, { name: "Load", state: "Completed", duration: "35s", recordDetail: "123,704 records written" }],
        validation: { checks: 12, passing: 11, failed: 1, evaluatedAt: incidentTimes.customerValidation.validationFailed, platformCode: incidentCodes.validationCheckFailed, vendorCode: incidentCodes.customerEmailNullRateFailed, failure: { check: "Customer email null rate", field: "customer_email", observed: "3.7%", threshold: "< 2.0%" } },
        relatedRuns: [{ id: runIds.customerIngestionSuccess, status: "Success", startedAt: incidentTimes.customerSuccess.runStarted, duration: "2m 14s", trigger: "Scheduled" }, { id: runIds.customerIngestionHistoricalFailure, status: "Failed", startedAt: incidentTimes.customerHistoricalFailure.runStarted, duration: "18s", trigger: "Scheduled" }],
        events: [{ id: "cw1", timestamp: incidentTimes.customerValidation.runStarted, title: "Run started", code: "RUN_STARTED", tone: "neutral" }, { id: "cw2", timestamp: incidentTimes.customerValidation.validationFailed, title: "Validation warning recorded", code: incidentCodes.validationCheckFailed, tone: "error" }, { id: "cw3", timestamp: incidentTimes.customerValidation.completed, title: "Run completed with warnings", code: "RUN_COMPLETED_WITH_WARNINGS", tone: "success" }],
    },
    {
        id: runIds.customerIngestionHistoricalFailure, pipelineId: pipelineIds.customerIngestion, pipelineName: "Customer Ingestion", environment: "Production", status: "Failed", trigger: "Scheduled", startedAt: incidentTimes.customerHistoricalFailure.runStarted, finishedAt: incidentTimes.customerHistoricalFailure.failed, duration: "18s", platformCode: incidentCodes.pipelineExecutionFailed, vendorCode: "SNOWFLAKE_CONNECTION_RESET", message: "Production Warehouse reset the connection during extraction.", recommendedAction: "Confirm warehouse connectivity and retry the historical execution if the data window is still required.",
        stages: [{ name: "Extract", state: "Failed", duration: "18s", platformCode: incidentCodes.pipelineExecutionFailed, vendorCode: "SNOWFLAKE_CONNECTION_RESET", message: "The warehouse connection was reset before extraction completed." }, { name: "Transform", state: "Pending" }, { name: "Validate", state: "Pending" }, { name: "Load", state: "Pending" }], validation: { checks: 0, passing: 0, failed: 0 },
        relatedRuns: [{ id: runIds.customerIngestionSuccess, status: "Success", startedAt: incidentTimes.customerSuccess.runStarted, duration: "2m 14s", trigger: "Scheduled" }, { id: runIds.customerIngestionValidationWarning, status: "Success", startedAt: incidentTimes.customerValidation.runStarted, duration: "2m 20s", trigger: "Scheduled" }],
        events: [{ id: "ch1", timestamp: incidentTimes.customerHistoricalFailure.runStarted, title: "Run started", code: "RUN_STARTED", tone: "neutral" }, { id: "ch2", timestamp: incidentTimes.customerHistoricalFailure.failed, title: "Extract stage failed", code: incidentCodes.pipelineExecutionFailed, tone: "error" }],
    },
    {
        id: "run_01J96ORD57", pipelineId: "orders-incremental", pipelineName: "Orders Incremental", environment: "Production", status: "Success", trigger: "Retry", startedAt: "2026-08-10T12:33:00.000Z", finishedAt: "2026-08-10T12:34:52.000Z", duration: "1m 52s", records: 96412, platformCode: "RUN_COMPLETED", message: "The retry execution completed successfully and all order records were loaded.", recommendedAction: "No corrective action is required.", stages: successfulCustomerStages, validation: { checks: 12, passing: 12, failed: 0, evaluatedAt: "2026-08-10T12:34:27.000Z" }, relatedRuns: [], events: [{ id: "o1", timestamp: "2026-08-10T12:33:00.000Z", title: "Retry started", code: "RUN_STARTED", tone: "neutral" }, { id: "o2", timestamp: "2026-08-10T12:34:52.000Z", title: "Run completed", code: "RUN_COMPLETED", tone: "success" }],
    },
    {
        id: runIds.eventsProcessingFailure, pipelineId: pipelineIds.eventsProcessing, pipelineName: "Events Processing", environment: "Production", status: "Failed", trigger: "Event", startedAt: incidentTimes.events.runStarted, finishedAt: incidentTimes.events.failed, duration: "1m 35s", platformCode: incidentCodes.pipelineExecutionFailed, vendorCode: incidentCodes.eventsKafkaAuthenticationFailed, message: "Events Kafka rejected the configured SASL credentials during Extract after three attempts.", recommendedAction: "Rotate or correct the Events Kafka SASL credentials, test the connection, then retry the run.",
        stages: [{ name: "Extract", state: "Failed", duration: "1m 35s", platformCode: incidentCodes.pipelineExecutionFailed, vendorCode: incidentCodes.eventsKafkaAuthenticationFailed, message: "Events Kafka rejected the configured SASL credentials after three attempts." }, { name: "Transform", state: "Pending" }, { name: "Validate", state: "Pending" }, { name: "Load", state: "Pending" }], validation: { checks: 0, passing: 0, failed: 0 }, relatedRuns: [],
        events: [{ id: "f1", timestamp: incidentTimes.events.runStarted, title: "Run started", code: "RUN_STARTED", tone: "neutral" }, { id: "f2", timestamp: incidentTimes.events.extractStarted, title: "Extract stage started", code: "STAGE_RUNNING", tone: "running" }, { id: "f3", timestamp: incidentTimes.events.retryTwoFailed, title: "Authentication retry 2 failed", code: incidentCodes.eventsKafkaAuthenticationFailed, tone: "error" }, { id: "f4", timestamp: incidentTimes.events.retryThreeFailed, title: "Authentication retry 3 failed", code: incidentCodes.eventsKafkaAuthenticationFailed, tone: "error" }, { id: "f5", timestamp: incidentTimes.events.failed, title: "Run failed", code: incidentCodes.pipelineExecutionFailed, tone: "error" }],
    },
    {
        id: "run_01J91CPM41", pipelineId: "customer-profile-merge", pipelineName: "Customer Profile Merge", environment: "Production", status: "Running", trigger: "Scheduled", startedAt: "2026-08-10T14:26:18.000Z", duration: "Running · 18m 42s", platformCode: "PIPELINE_RUNNING", message: "Pipeline execution is currently transforming customer profiles.", recommendedAction: "Monitor the active execution or inspect logs if progress stalls.", stages: [{ name: "Extract", state: "Completed", duration: "44s", recordDetail: "126,011 records read" }, { name: "Transform", state: "Running", duration: "17m 58s", recordDetail: "126,011 records in progress" }, { name: "Validate", state: "Pending" }, { name: "Load", state: "Pending" }], validation: { checks: 12, passing: 0, failed: 0 }, relatedRuns: [], events: [{ id: "r1", timestamp: "2026-08-10T14:26:18.000Z", title: "Run started", code: "RUN_STARTED", tone: "neutral" }, { id: "r2", timestamp: "2026-08-10T14:27:02.000Z", title: "Extract stage completed", code: "STAGE_COMPLETED", tone: "success" }],
    },
    {
        id: runIds.billingValidationFailure, pipelineId: pipelineIds.billingReconciliation, pipelineName: "Billing Reconciliation", environment: "Production", status: "Failed", trigger: "Scheduled", startedAt: incidentTimes.billing.runStarted, finishedAt: incidentTimes.billing.validationFailed, duration: "8m 42s", records: 118204, platformCode: incidentCodes.validationCheckFailed, vendorCode: incidentCodes.orderIdUniqueFailed, message: "The blocking Order ID unique check found 318 duplicate order_id values; execution stopped before Load.", recommendedAction: "Deduplicate order_id values upstream, verify the source query, then retry the run.",
        stages: [{ name: "Extract", state: "Completed", duration: "2m 03s", recordDetail: "118,736 records read" }, { name: "Transform", state: "Completed", duration: "5m 54s", recordDetail: "118,204 records produced" }, { name: "Validate", state: "Failed", duration: "45s", recordDetail: "318 duplicate order_id values", platformCode: incidentCodes.validationCheckFailed, vendorCode: incidentCodes.orderIdUniqueFailed, message: "Order ID unique failed as a blocking validation check." }, { name: "Load", state: "Pending", recordDetail: "Execution stopped before load" }],
        validation: { checks: 12, passing: 11, failed: 1, evaluatedAt: incidentTimes.billing.validationFailed, platformCode: incidentCodes.validationCheckFailed, vendorCode: incidentCodes.orderIdUniqueFailed, failure: { check: "Order ID unique", field: "order_id", observed: "318 duplicates", threshold: "0 duplicates" } }, relatedRuns: [],
        events: [{ id: "v1", timestamp: incidentTimes.billing.runStarted, title: "Run started", code: "RUN_STARTED", tone: "neutral" }, { id: "v2", timestamp: "2026-08-10T13:30:03.000Z", title: "Extract stage completed", code: "STAGE_COMPLETED", tone: "success" }, { id: "v3", timestamp: "2026-08-10T13:35:57.000Z", title: "Transform stage completed", code: "STAGE_COMPLETED", tone: "success" }, { id: "v4", timestamp: incidentTimes.billing.validationFailed, title: "Order ID unique failed", code: incidentCodes.validationCheckFailed, tone: "error" }, { id: "v5", timestamp: incidentTimes.billing.validationFailed, title: "Execution stopped before Load", code: incidentCodes.validationCheckFailed, tone: "error" }],
    },
    {
        id: "run_01J98WAR03", pipelineId: pipelineIds.warehouseSync, pipelineName: "Warehouse Sync", environment: "Production", status: "Cancelled", trigger: "Manual", startedAt: "2026-08-10T10:25:00.000Z", finishedAt: "2026-08-10T10:26:11.000Z", duration: "1m 11s", platformCode: "PIPELINE_RUN_CANCELLED", message: "Execution was cancelled by the user during transformation.", recommendedAction: "Retry only when it is operationally appropriate to continue.", stages: [{ name: "Extract", state: "Completed", duration: "48s", recordDetail: "84,091 records read" }, { name: "Transform", state: "Cancelled", duration: "23s", recordDetail: "Work stopped before output was committed" }, { name: "Validate", state: "Pending" }, { name: "Load", state: "Pending" }], validation: { checks: 8, passing: 0, failed: 0 }, relatedRuns: [], events: [{ id: "c1", timestamp: "2026-08-10T10:25:00.000Z", title: "Run started", code: "RUN_STARTED", tone: "neutral" }, { id: "c2", timestamp: "2026-08-10T10:26:11.000Z", title: "Run cancelled by user", code: "PIPELINE_RUN_CANCELLED", tone: "neutral" }],
    },
    {
        id: runIds.warehouseValidationFailure, pipelineId: pipelineIds.warehouseSync, pipelineName: "Warehouse Sync", environment: "Production", status: "Failed", trigger: "Scheduled", startedAt: "2026-08-10T12:40:00.000Z", finishedAt: "2026-08-10T12:42:12.000Z", duration: "2m 12s", records: 84091, platformCode: "VALIDATION_EXECUTION_FAILED", vendorCode: "SNOWFLAKE_QUERY_CONNECTION_RESET", message: "Account freshness exceeded its warning threshold, then a second validation query lost its Production Warehouse connection.", recommendedAction: "Restore Production Warehouse connectivity and rerun validation.",
        stages: [{ name: "Extract", state: "Completed", duration: "48s", recordDetail: "84,091 records read" }, { name: "Transform", state: "Completed", duration: "53s", recordDetail: "84,091 records produced" }, { name: "Validate", state: "Failed", duration: "31s", recordDetail: "1 warning; 1 check not evaluated", platformCode: "VALIDATION_EXECUTION_FAILED", vendorCode: "SNOWFLAKE_QUERY_CONNECTION_RESET", message: "The warehouse customer check could not be evaluated." }, { name: "Load", state: "Pending" }],
        validation: { checks: 8, passing: 6, failed: 2, evaluatedAt: "2026-08-10T12:42:12.000Z", platformCode: "VALIDATION_EXECUTION_FAILED", vendorCode: "SNOWFLAKE_QUERY_CONNECTION_RESET", failure: { check: "Warehouse customer check", field: "customer_id", observed: "Not evaluated", threshold: "0 nulls" } }, relatedRuns: [{ id: "run_01J98WAR03", status: "Cancelled", startedAt: "2026-08-10T10:25:00.000Z", duration: "1m 11s", trigger: "Manual" }],
        events: [{ id: "wv1", timestamp: "2026-08-10T12:40:00.000Z", title: "Run started", code: "RUN_STARTED", tone: "neutral" }, { id: "wv2", timestamp: "2026-08-10T12:41:58.000Z", title: "Account freshness warning recorded", code: "VALIDATION_CHECK_FAILED", tone: "error" }, { id: "wv3", timestamp: "2026-08-10T12:42:12.000Z", title: "Validation execution failed", code: "VALIDATION_EXECUTION_FAILED", tone: "error" }],
    },
];

export function getPipelineRunDetail(runId: string) {
    return pipelineRunDetails.find((run) => run.id === runId);
}

export function formatExactRunTimestamp(value?: string) {
    if (!value) return "In progress";
    const date = new Date(value);
    const datePart = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "America/New_York" }).format(date);
    const timePart = new Intl.DateTimeFormat("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "America/New_York" }).format(date);
    return `${datePart} · ${timePart}`;
}
