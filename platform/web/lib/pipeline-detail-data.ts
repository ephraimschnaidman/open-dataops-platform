import { pipelineIds, sourceIds } from "@/lib/canonical-demo";
import type { OperationalResult } from "@/lib/operational-status";
import { pipelineRunDetails } from "@/lib/pipeline-run-detail-data";
import { pipelines, type Pipeline } from "@/lib/pipelines-data";

export type PipelineDetailStatus = "Healthy" | "Warning" | "Failed" | "Running" | "Disabled";
export type PipelineRunStatus = "Success" | "Running" | "Failed" | "Cancelled";
export interface PipelineEndpoint { name: string; type: string; status: "Healthy" | "Warning"; sourceId?: string; }
export interface PipelineRun { id: string; status: PipelineRunStatus; started: string; duration: string; trigger: "Scheduled" | "Manual" | "Retry" | "Event"; records: string; }
export interface ActivePipelineRun { started: string; currentStage: "Extract" | "Transform" | "Validate" | "Load"; stages: Array<{ name: "Extract" | "Transform" | "Validate" | "Load"; state: "complete" | "active" | "pending" }>; }
export interface PipelineValidation { activeChecks: number; passing: number; failed: number; lastEvaluated: string; platformCode?: string; }
export interface PipelineDependency { name: string; relationship: "Upstream" | "Downstream"; status: "Healthy" | "Warning"; }
export interface PipelineActivity { id: string; time: string; title: string; code: string; tone: "success" | "warning" | "error" | "neutral"; }
export interface PipelineDetail { id: string; name: string; status: PipelineDetailStatus; environment: string; schedule: string; source: PipelineEndpoint; destination: PipelineEndpoint; latestRun: { value: string; detail: string }; nextRun: string; duration: string; successRate: string; health: OperationalResult; healthDetails: Array<{ label: string; value: string }>; recentRuns: PipelineRun[]; activeRun?: ActivePipelineRun; validation?: PipelineValidation; configuration: Array<{ label: string; value: string; mono?: boolean }>; dependencies: PipelineDependency[]; monitoring: Array<{ label: string; value: string }>; activity: PipelineActivity[]; runStartOutcome: "success" | "failure"; }

const destinationTypes: Record<string, string> = { "Customer Lakehouse": "Snowflake", "Finance Warehouse": "Snowflake", "Events Warehouse": "Snowflake", "Reporting Store": "PostgreSQL", "Reporting Archive": "Amazon S3", "Secure Export Bucket": "Amazon S3", "Identity Store": "PostgreSQL", "Operations Warehouse": "Snowflake", "Analytics Warehouse": "Snowflake", "Production Warehouse": "Snowflake", "Development Warehouse": "Snowflake", "Archive Bucket": "Amazon S3" };
const sourceRouteIds: Record<string, string> = { "Production Warehouse": sourceIds.productionWarehouse, "Billing PostgreSQL": sourceIds.billingPostgres, "Events Kafka": sourceIds.eventsKafka, "Legacy SQL Server": sourceIds.legacySqlServer };

function statusFor(pipeline: Pipeline): PipelineDetailStatus { return pipeline.id === "customer-profile-merge" ? "Running" : pipeline.status; }

function healthFor(pipeline: Pipeline, status: PipelineDetailStatus): { result: OperationalResult; details: Array<{ label: string; value: string }> } {
    if (pipeline.operationalIssue) {
        const details = pipeline.id === pipelineIds.eventsProcessing
            ? [{ label: "Failed stage", value: "Extract" }, { label: "Failed at", value: "10:42:38 AM" }, { label: "Related source", value: "Events Kafka" }, { label: "Duration before failure", value: "1m 35s" }]
            : pipeline.id === pipelineIds.billingReconciliation
                ? [{ label: "Validation check", value: "Order ID unique" }, { label: "Actual", value: "318 duplicates" }, { label: "Expected", value: "0 duplicates" }, { label: "Pipeline effect", value: "Stopped during Validate" }]
                : [{ label: "Schedule", value: pipeline.schedule }, { label: "Status", value: status }];
        return { result: pipeline.operationalIssue, details };
    }
    if (status === "Running") return { result: { status: "Running", platformCode: "PIPELINE_RUNNING", message: "A pipeline execution is currently in progress.", recommendedAction: "Monitor the active run until all stages complete." }, details: [{ label: "Started", value: "18m 42s ago" }, { label: "Current stage", value: "Transform" }] };
    if (status === "Disabled") return { result: { status: "Neutral", platformCode: "PIPELINE_DISABLED", message: "Scheduled execution is intentionally disabled for this pipeline.", recommendedAction: "Enable the pipeline when scheduled processing should resume." }, details: [{ label: "Schedule", value: "Paused" }] };
    return { result: { status: "Success", platformCode: "PIPELINE_OK", message: "Latest execution completed successfully and no operational issues are currently detected.", recommendedAction: "No remediation is required." }, details: [{ label: "Source health", value: "Healthy" }, { label: "Validation", value: "12/12 passing" }, { label: "Schedule", value: "On time" }] };
}

function createDetail(pipeline: Pipeline): PipelineDetail {
    const status = statusFor(pipeline);
    const health = healthFor(pipeline, status);
    const destinationName = pipeline.destination ?? "Analytics Warehouse";
    const recentRuns: PipelineRun[] = pipelineRunDetails.filter((run) => run.pipelineId === pipeline.id).map((run) => ({ id: run.id, status: run.status, started: new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" }).format(new Date(run.startedAt)), duration: run.duration, trigger: run.trigger, records: run.records?.toLocaleString() ?? "—" }));
    const latestRun = recentRuns[0];
    const billing = pipeline.id === pipelineIds.billingReconciliation;
    return {
        id: pipeline.id, name: pipeline.name, status, environment: pipeline.environment, schedule: pipeline.schedule,
        source: { name: pipeline.source.name, type: pipeline.source.technology, status: pipeline.id === pipelineIds.eventsProcessing || billing ? "Warning" : "Healthy", sourceId: sourceRouteIds[pipeline.source.name] },
        destination: { name: destinationName, type: destinationTypes[destinationName] ?? "Snowflake", status: "Healthy", sourceId: sourceRouteIds[destinationName] },
        latestRun: latestRun ? { value: latestRun.status, detail: latestRun.started } : { value: pipeline.lastRun, detail: pipeline.lastRun }, nextRun: status === "Disabled" ? "—" : status === "Running" ? "In progress" : pipeline.nextRun, duration: latestRun?.duration ?? pipeline.duration, successRate: status === "Failed" ? "96.7%" : status === "Warning" ? "98.4%" : "99.2%", health: health.result, healthDetails: health.details, recentRuns,
        activeRun: status === "Running" ? { started: "18m 42s ago", currentStage: "Transform", stages: [{ name: "Extract", state: "complete" }, { name: "Transform", state: "active" }, { name: "Validate", state: "pending" }, { name: "Load", state: "pending" }] } : undefined,
        validation: pipeline.id === "product-analytics" ? undefined : { activeChecks: 12, passing: billing ? 11 : 12, failed: billing ? 1 : 0, lastEvaluated: billing ? "1 hr ago" : "11 min ago", platformCode: billing ? "VALIDATION_CHECK_FAILED" : undefined },
        configuration: [{ label: "Pipeline ID", value: pipeline.technicalId, mono: true }, { label: "Environment", value: pipeline.environment }, { label: "Schedule", value: pipeline.schedule }, { label: "Source", value: pipeline.source.name }, { label: "Destination", value: destinationName }, { label: "Execution Mode", value: pipeline.scheduleMode }, { label: "Created", value: "March 14, 2025" }, { label: "Last Modified", value: "August 8, 2026 at 4:18 PM" }, { label: "Enabled", value: status === "Disabled" ? "No" : "Yes" }],
        dependencies: pipeline.id === "product-analytics" ? [] : [{ name: pipeline.source.name, relationship: "Upstream", status: pipeline.id === pipelineIds.eventsProcessing ? "Warning" : "Healthy" }, { name: destinationName, relationship: "Downstream", status: "Healthy" }], monitoring: [{ label: "Average runtime", value: pipeline.duration }, { label: "Runs in last 24h", value: recentRuns.length.toString() }, { label: "Failures in last 24h", value: recentRuns.filter((run) => run.status === "Failed").length.toString() }, { label: "Schedule adherence", value: pipeline.id === pipelineIds.riskReporting ? "Missed latest run" : "On time" }],
        activity: recentRuns.map((run): PipelineActivity => ({ id: `activity-${run.id}`, time: run.started, title: run.status === "Failed" ? "Pipeline execution failed" : run.status === "Cancelled" ? "Pipeline run cancelled" : "Pipeline run completed successfully", code: pipelineRunDetails.find((item) => item.id === run.id)?.platformCode ?? "RUN_COMPLETED", tone: run.status === "Failed" ? "error" : run.status === "Cancelled" ? "neutral" : "success" })).slice(0, 5), runStartOutcome: status === "Failed" ? "failure" : "success",
    };
}

export const pipelineDetails = pipelines.map(createDetail);
export function getPipelineDetail(pipelineId: string) { return pipelineDetails.find((pipeline) => pipeline.id === pipelineId); }
