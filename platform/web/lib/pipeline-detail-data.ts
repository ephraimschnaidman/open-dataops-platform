import { pipelines, type Pipeline } from "@/lib/pipelines-data";
import type { OperationalResult } from "@/lib/operational-status";

export type PipelineDetailStatus = "Healthy" | "Warning" | "Failed" | "Running" | "Disabled";
export type PipelineRunStatus = "Success" | "Running" | "Failed" | "Cancelled";

export interface PipelineEndpoint {
    name: string;
    type: string;
    status: "Healthy" | "Warning";
    sourceId?: string;
}

export interface PipelineRun {
    id: string;
    status: PipelineRunStatus;
    started: string;
    duration: string;
    trigger: "Scheduled" | "Manual";
    records: string;
}

export interface ActivePipelineRun {
    started: string;
    currentStage: "Extract" | "Transform" | "Validate" | "Load";
    stages: Array<{ name: "Extract" | "Transform" | "Validate" | "Load"; state: "complete" | "active" | "pending" }>;
}

export interface PipelineValidation {
    activeChecks: number;
    passing: number;
    failed: number;
    lastEvaluated: string;
    platformCode?: string;
}

export interface PipelineDependency {
    name: string;
    relationship: "Upstream" | "Downstream";
    status: "Healthy" | "Warning";
}

export interface PipelineActivity {
    id: string;
    time: string;
    title: string;
    code: string;
    tone: "success" | "warning" | "error" | "neutral";
}

export interface PipelineDetail {
    id: string;
    name: string;
    status: PipelineDetailStatus;
    environment: string;
    schedule: string;
    source: PipelineEndpoint;
    destination: PipelineEndpoint;
    latestRun: { value: string; detail: string };
    nextRun: string;
    duration: string;
    successRate: string;
    health: OperationalResult;
    healthDetails: Array<{ label: string; value: string }>;
    recentRuns: PipelineRun[];
    activeRun?: ActivePipelineRun;
    validation?: PipelineValidation;
    configuration: Array<{ label: string; value: string; mono?: boolean }>;
    dependencies: PipelineDependency[];
    monitoring: Array<{ label: string; value: string }>;
    activity: PipelineActivity[];
    runStartOutcome: "success" | "failure";
}

const destinationTypes: Record<string, string> = { "Customer Lakehouse": "Snowflake", "Finance Warehouse": "Snowflake", "Events Warehouse": "Snowflake", "Reporting Store": "PostgreSQL", "Reporting Archive": "Amazon S3", "Secure Export Bucket": "Amazon S3", "Identity Store": "PostgreSQL", "Operations Warehouse": "Snowflake", "Analytics Warehouse": "Snowflake", "Production Warehouse": "PostgreSQL", "Development Warehouse": "Snowflake", "Archive Bucket": "Amazon S3" };

const defaultRuns: PipelineRun[] = [
    { id: "run-1042", status: "Success", started: "8 min ago", duration: "2m 14s", trigger: "Scheduled", records: "124,892" },
    { id: "run-1041", status: "Success", started: "1 hr ago", duration: "2m 09s", trigger: "Scheduled", records: "123,771" },
    { id: "run-1040", status: "Failed", started: "2 hr ago", duration: "34s", trigger: "Scheduled", records: "—" },
    { id: "run-1039", status: "Success", started: "3 hr ago", duration: "2m 18s", trigger: "Manual", records: "122,913" },
];

const defaultActivity: PipelineActivity[] = [
    { id: "activity-1", time: "10:43 AM", title: "Pipeline run completed successfully", code: "RUN_COMPLETED", tone: "success" },
    { id: "activity-2", time: "9:43 AM", title: "Pipeline run completed successfully", code: "RUN_COMPLETED", tone: "success" },
    { id: "activity-3", time: "8:43 AM", title: "Pipeline execution failed", code: "PIPELINE_EXECUTION_FAILED", tone: "error" },
    { id: "activity-4", time: "8:45 AM", title: "Pipeline manually retried by user", code: "PIPELINE_RETRY_STARTED", tone: "warning" },
    { id: "activity-5", time: "Yesterday", title: "Schedule updated from every 2 hours to hourly", code: "PIPELINE_CONFIGURATION_UPDATED", tone: "neutral" },
];

function statusFor(pipeline: Pipeline): PipelineDetailStatus {
    if (pipeline.id === "customer-profile-merge") return "Running";
    return pipeline.status;
}

function healthFor(status: PipelineDetailStatus): { result: OperationalResult; details: Array<{ label: string; value: string }> } {
    if (status === "Warning") return { result: { status: "Warning", platformCode: "VALIDATION_CHECK_FAILED", vendorCode: "CHECK_NULL_RATE_THRESHOLD", message: "The latest run completed, but one validation check failed.", recommendedAction: "Review the failed validation check and confirm whether the output is safe to consume." }, details: [{ label: "Checks passed", value: "11" }, { label: "Checks failed", value: "1" }, { label: "Output", value: "Produced" }, { label: "Detected", value: "8 min ago" }] };
    if (status === "Failed") return { result: { status: "Error", platformCode: "PIPELINE_EXECUTION_FAILED", vendorCode: "SQLSTATE 08006", message: "The pipeline failed during extraction because the database connection was interrupted.", recommendedAction: "Inspect the failed extraction run and retry after source connectivity is restored." }, details: [{ label: "Failed stage", value: "Extract" }, { label: "Failed at", value: "10:42 AM" }, { label: "Last successful run", value: "1 hr ago" }, { label: "Duration before failure", value: "34s" }] };
    if (status === "Running") return { result: { status: "Running", platformCode: "PIPELINE_RUNNING", message: "A pipeline execution is currently in progress.", recommendedAction: "Monitor the active run until all stages complete." }, details: [{ label: "Started", value: "3m 41s ago" }, { label: "Current stage", value: "Transform" }, { label: "Trigger", value: "Scheduled" }, { label: "Source health", value: "Healthy" }] };
    if (status === "Disabled") return { result: { status: "Neutral", platformCode: "PIPELINE_DISABLED", message: "Scheduled execution is intentionally disabled for this pipeline.", recommendedAction: "Enable the pipeline when scheduled processing should resume." }, details: [{ label: "Next run", value: "—" }, { label: "Run Now", value: "Unavailable" }, { label: "Last run", value: "4 days ago" }, { label: "Schedule", value: "Paused" }] };
    return { result: { status: "Success", platformCode: "PIPELINE_OK", message: "Latest execution completed successfully and no operational issues are currently detected.", recommendedAction: "No remediation is required. Review the latest run for execution details." }, details: [{ label: "Last successful run", value: "8 min ago" }, { label: "Last failure", value: "12 days ago" }, { label: "Source health", value: "Healthy" }, { label: "Validation", value: "12/12 passing" }, { label: "Schedule", value: "On time" }] };
}

function createDetail(pipeline: Pipeline): PipelineDetail {
    const status = statusFor(pipeline);
    const health = healthFor(status);
    const destinationName = pipeline.id === "customer-ingestion" ? "Analytics Warehouse" : pipeline.destination ?? "Analytics Warehouse";
    const sourceId = pipeline.source.name === "Analytics Warehouse" ? "analytics-warehouse" : undefined;
    const destinationId = destinationName === "Analytics Warehouse" ? "analytics-warehouse" : undefined;
    const validation = pipeline.id === "product-analytics" ? undefined : { activeChecks: 12, passing: status === "Warning" ? 11 : 12, failed: status === "Warning" ? 1 : 0, lastEvaluated: "8 min ago", platformCode: status === "Warning" ? "VALIDATION_CHECK_FAILED" : undefined };
    const recentRuns = pipeline.id === "product-analytics" ? [] : status === "Running" ? [{ id: "run-active", status: "Running" as const, started: "3m 41s ago", duration: "Running · 3m 41s", trigger: "Scheduled" as const, records: "—" }, ...defaultRuns] : defaultRuns;
    return {
        id: pipeline.id, name: pipeline.name, status, environment: pipeline.environment, schedule: pipeline.schedule,
        source: { name: pipeline.source.name, type: pipeline.source.technology, status: "Healthy", sourceId },
        destination: { name: destinationName, type: destinationTypes[destinationName] ?? "Snowflake", status: status === "Warning" ? "Warning" : "Healthy", sourceId: destinationId },
        latestRun: status === "Failed" ? { value: "Failed", detail: "18 min ago" } : status === "Running" ? { value: "Running", detail: "Started 3m 41s ago" } : { value: "Successful", detail: status === "Disabled" ? "4 days ago" : "8 min ago" },
        nextRun: status === "Disabled" ? "—" : status === "Running" ? "In progress" : pipeline.nextRun,
        duration: status === "Running" ? "Running · 3m 41s" : pipeline.duration,
        successRate: status === "Failed" ? "96.7%" : status === "Warning" ? "98.4%" : "99.2%",
        health: health.result, healthDetails: health.details, recentRuns,
        activeRun: status === "Running" ? { started: "3m 41s ago", currentStage: "Transform", stages: [{ name: "Extract", state: "complete" }, { name: "Transform", state: "active" }, { name: "Validate", state: "pending" }, { name: "Load", state: "pending" }] } : undefined,
        validation,
        configuration: [{ label: "Pipeline ID", value: pipeline.technicalId, mono: true }, { label: "Environment", value: pipeline.environment }, { label: "Schedule", value: pipeline.schedule }, { label: "Source", value: pipeline.source.name }, { label: "Destination", value: destinationName }, { label: "Execution Mode", value: pipeline.scheduleMode }, { label: "Created", value: "March 14, 2025" }, { label: "Last Modified", value: "August 8, 2026 at 4:18 PM" }, { label: "Enabled", value: status === "Disabled" ? "No" : "Yes" }],
        dependencies: pipeline.id === "product-analytics" ? [] : [{ name: pipeline.source.name, relationship: "Upstream", status: "Healthy" }, { name: "Revenue Reporting", relationship: "Downstream", status: "Healthy" }, { name: "Customer Analytics", relationship: "Downstream", status: status === "Warning" ? "Warning" : "Healthy" }],
        monitoring: [{ label: "Average runtime", value: "2m 11s" }, { label: "Runs in last 24h", value: "24" }, { label: "Failures in last 24h", value: status === "Failed" ? "2" : "1" }, { label: "Schedule adherence", value: "23 / 24 on time" }],
        activity: defaultActivity,
        runStartOutcome: status === "Failed" ? "failure" : "success",
    };
}

export const pipelineDetails = pipelines.map(createDetail);

export function getPipelineDetail(pipelineId: string) {
    return pipelineDetails.find((pipeline) => pipeline.id === pipelineId);
}
