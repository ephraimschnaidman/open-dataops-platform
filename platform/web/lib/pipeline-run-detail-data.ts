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

const related = (prefix: string, trigger: PipelineRunTrigger = "Scheduled"): RelatedRun[] => [
    { id: `${prefix}_PREV1`, status: "Success", startedAt: "2026-08-10T12:22:18.000Z", duration: "2m 09s", trigger },
    { id: `${prefix}_PREV2`, status: "Failed", startedAt: "2026-08-10T11:22:18.000Z", duration: "41s", trigger },
    { id: `${prefix}_PREV3`, status: "Success", startedAt: "2026-08-10T10:22:18.000Z", duration: "2m 18s", trigger: "Manual" },
];

const successStages: ExecutionStage[] = [
    { name: "Extract", state: "Completed", duration: "38s", recordDetail: "125,104 records read" },
    { name: "Transform", state: "Completed", duration: "52s", recordDetail: "124,892 records produced" },
    { name: "Validate", state: "Completed", duration: "18s", recordDetail: "12 checks passed" },
    { name: "Load", state: "Completed", duration: "26s", recordDetail: "124,892 records written" },
];

export const pipelineRunDetails: PipelineRunDetail[] = [
    {
        id: "run_01J92CING8", pipelineId: "customer-ingestion", pipelineName: "Customer Ingestion", environment: "Production", status: "Success", trigger: "Scheduled", startedAt: "2026-08-10T13:22:00.000Z", finishedAt: "2026-08-10T13:24:14.000Z", duration: "2m 14s", records: 124892, platformCode: "RUN_COMPLETED", message: "Pipeline execution completed successfully and all records were loaded.", recommendedAction: "No corrective action is required.", stages: successStages,
        validation: { checks: 12, passing: 12, failed: 0, evaluatedAt: "2026-08-10T13:23:48.000Z" }, relatedRuns: related("run_01J92CING8"),
        events: [
            { id: "s1", timestamp: "2026-08-10T13:22:00.000Z", title: "Run started", code: "RUN_STARTED", tone: "neutral" },
            { id: "s2", timestamp: "2026-08-10T13:22:38.000Z", title: "Extract stage completed", code: "STAGE_COMPLETED", tone: "success" },
            { id: "s3", timestamp: "2026-08-10T13:23:30.000Z", title: "Transform stage completed", code: "STAGE_COMPLETED", tone: "success" },
            { id: "s4", timestamp: "2026-08-10T13:23:48.000Z", title: "Validation completed", code: "STAGE_COMPLETED", tone: "success" },
            { id: "s5", timestamp: "2026-08-10T13:24:14.000Z", title: "Load stage completed", code: "STAGE_COMPLETED", tone: "success" },
            { id: "s6", timestamp: "2026-08-10T13:24:14.000Z", title: "Run completed", code: "RUN_COMPLETED", tone: "success" },
        ],
    },
    {
        id: "run_01J94EVT18", pipelineId: "events-processing", pipelineName: "Events Processing", environment: "Production", status: "Failed", trigger: "Event", startedAt: "2026-08-10T13:02:00.000Z", finishedAt: "2026-08-10T13:02:34.000Z", duration: "34s", platformCode: "PIPELINE_EXECUTION_FAILED", vendorCode: "SASL_AUTHENTICATION_FAILED", message: "Authentication to the event broker failed during extraction.", recommendedAction: "Verify broker credentials, inspect the execution logs, and retry the run.",
        stages: [{ name: "Extract", state: "Failed", duration: "34s", platformCode: "PIPELINE_EXECUTION_FAILED", vendorCode: "SASL_AUTHENTICATION_FAILED", message: "The broker rejected the configured credentials." }, { name: "Transform", state: "Pending" }, { name: "Validate", state: "Pending" }, { name: "Load", state: "Pending" }],
        validation: { checks: 0, passing: 0, failed: 0 }, relatedRuns: related("run_01J94EVT18", "Event"),
        events: [{ id: "f1", timestamp: "2026-08-10T13:02:00.000Z", title: "Run started", code: "RUN_STARTED", tone: "neutral" }, { id: "f2", timestamp: "2026-08-10T13:02:34.000Z", title: "Extract stage failed", code: "PIPELINE_EXECUTION_FAILED", tone: "error" }, { id: "f3", timestamp: "2026-08-10T13:02:34.000Z", title: "Run failed", code: "PIPELINE_EXECUTION_FAILED", tone: "error" }],
    },
    {
        id: "run_01J91CPM41", pipelineId: "customer-profile-merge", pipelineName: "Customer Profile Merge", environment: "Production", status: "Running", trigger: "Scheduled", startedAt: "2026-08-10T13:26:18.000Z", duration: "Running · 3m 41s", platformCode: "PIPELINE_RUNNING", message: "Pipeline execution is currently transforming customer profiles.", recommendedAction: "Monitor the active execution or inspect logs if progress stalls.",
        stages: [{ name: "Extract", state: "Completed", duration: "44s", recordDetail: "126,011 records read" }, { name: "Transform", state: "Running", duration: "2m 57s", recordDetail: "126,011 records in progress" }, { name: "Validate", state: "Pending" }, { name: "Load", state: "Pending" }],
        validation: { checks: 12, passing: 0, failed: 0 }, relatedRuns: related("run_01J91CPM41"),
        events: [{ id: "r1", timestamp: "2026-08-10T13:26:18.000Z", title: "Run started", code: "RUN_STARTED", tone: "neutral" }, { id: "r2", timestamp: "2026-08-10T13:27:02.000Z", title: "Extract stage completed", code: "STAGE_COMPLETED", tone: "success" }, { id: "r3", timestamp: "2026-08-10T13:27:02.000Z", title: "Transform stage started", code: "STAGE_RUNNING", tone: "running" }],
    },
    {
        id: "run_01J97BIL02", pipelineId: "billing-reconciliation", pipelineName: "Billing Reconciliation", environment: "Production", status: "Failed", trigger: "Scheduled", startedAt: "2026-08-10T11:28:00.000Z", finishedAt: "2026-08-10T11:36:42.000Z", duration: "8m 42s", records: 118204, platformCode: "VALIDATION_CHECK_FAILED", vendorCode: "CHECK_NULL_RATE_THRESHOLD", message: "Execution reached validation, where the configured null-rate threshold failed.", recommendedAction: "Review the failed validation check before retrying the run.",
        stages: [{ name: "Extract", state: "Completed", duration: "2m 03s", recordDetail: "118,736 records read" }, { name: "Transform", state: "Completed", duration: "5m 54s", recordDetail: "118,204 records produced" }, { name: "Validate", state: "Failed", duration: "45s", recordDetail: "118,204 records evaluated", platformCode: "VALIDATION_CHECK_FAILED", vendorCode: "CHECK_NULL_RATE_THRESHOLD", message: "Null values exceeded the configured threshold for payment_status." }, { name: "Load", state: "Pending" }],
        validation: { checks: 12, passing: 11, failed: 1, evaluatedAt: "2026-08-10T11:36:42.000Z", platformCode: "VALIDATION_CHECK_FAILED", vendorCode: "CHECK_NULL_RATE_THRESHOLD", failure: { check: "Null rate threshold", field: "payment_status", observed: "2.4%", threshold: "≤ 1.0%" } }, relatedRuns: related("run_01J97BIL02"),
        events: [{ id: "v1", timestamp: "2026-08-10T11:28:00.000Z", title: "Run started", code: "RUN_STARTED", tone: "neutral" }, { id: "v2", timestamp: "2026-08-10T11:30:03.000Z", title: "Extract stage completed", code: "STAGE_COMPLETED", tone: "success" }, { id: "v3", timestamp: "2026-08-10T11:35:57.000Z", title: "Transform stage completed", code: "STAGE_COMPLETED", tone: "success" }, { id: "v4", timestamp: "2026-08-10T11:36:42.000Z", title: "Validation failed", code: "VALIDATION_CHECK_FAILED", tone: "error" }, { id: "v5", timestamp: "2026-08-10T11:36:42.000Z", title: "Run failed", code: "VALIDATION_CHECK_FAILED", tone: "error" }],
    },
    {
        id: "run_01J98WAR03", pipelineId: "warehouse-sync", pipelineName: "Warehouse Sync", environment: "Production", status: "Cancelled", trigger: "Manual", startedAt: "2026-08-10T10:25:00.000Z", finishedAt: "2026-08-10T10:26:11.000Z", duration: "1m 11s", platformCode: "PIPELINE_RUN_CANCELLED", message: "Execution was cancelled by the user during transformation.", recommendedAction: "Retry only when it is operationally appropriate to continue.",
        stages: [{ name: "Extract", state: "Completed", duration: "48s", recordDetail: "84,091 records read" }, { name: "Transform", state: "Cancelled", duration: "23s", recordDetail: "Work stopped before output was committed" }, { name: "Validate", state: "Pending" }, { name: "Load", state: "Pending" }],
        validation: { checks: 8, passing: 0, failed: 0 }, relatedRuns: related("run_01J98WAR03"),
        events: [{ id: "c1", timestamp: "2026-08-10T10:25:00.000Z", title: "Run started", code: "RUN_STARTED", tone: "neutral" }, { id: "c2", timestamp: "2026-08-10T10:25:48.000Z", title: "Extract stage completed", code: "STAGE_COMPLETED", tone: "success" }, { id: "c3", timestamp: "2026-08-10T10:26:11.000Z", title: "Run cancelled by user", code: "PIPELINE_RUN_CANCELLED", tone: "neutral" }],
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
