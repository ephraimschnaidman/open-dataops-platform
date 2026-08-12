import { dataSources, type DataSource } from "@/lib/data-sources-data";
import type { OperationalResult } from "@/lib/operational-status";
import { pipelines, type PipelineStatus } from "@/lib/pipelines-data";

export interface ConfigurationField {
    label: string;
    value: string;
    mono?: boolean;
}

export interface ConnectedPipeline {
    id: string;
    name: string;
    status: PipelineStatus;
    schedule: string;
    lastRun: string;
}

export interface ValidationSummary {
    status: "Success" | "Warning" | "Error";
    passed: number;
    warnings: number;
    failed: number;
    lastRun: string;
}

export interface SourceActivity {
    id: string;
    tone: "success" | "warning" | "error" | "neutral";
    title: string;
    detail: string;
    actor: string;
    time: string;
}

export interface DataSourceDetail extends DataSource {
    description: string;
    owner: string;
    createdAt: string;
    health: OperationalResult & { lastChecked: string; latency: string };
    configuration: ConfigurationField[];
    connectedPipelines: ConnectedPipeline[];
    validation: ValidationSummary;
    recentActivity: SourceActivity[];
}

const healthByStatus: Record<DataSource["status"], OperationalResult & { lastChecked: string; latency: string }> = {
    Healthy: { status: "Success", platformCode: "SOURCE_CONNECTION_HEALTHY", message: "Connection established and responding normally.", recommendedAction: "No action required. Continue monitoring on the configured schedule.", lastChecked: "2 min ago", latency: "84 ms" },
    Warning: { status: "Warning", platformCode: "SOURCE_LATENCY_ELEVATED", message: "Connection succeeded, but response latency is above the expected threshold.", recommendedAction: "Review database load and network routing, then test the connection again.", lastChecked: "5 min ago", latency: "418 ms" },
    Disconnected: { status: "Error", platformCode: "SOURCE_AUTHENTICATION_FAILED", vendorCode: "SASL_AUTHENTICATION_FAILED", message: "The platform could not authenticate with the source.", recommendedAction: "Review the Events Kafka authentication/connection configuration before retrying the failed execution.", lastChecked: "2 min ago", latency: "—" },
    Disabled: { status: "Warning", platformCode: "SOURCE_MONITORING_DISABLED", message: "Connection checks are disabled for this source.", recommendedAction: "Enable the source when it should resume providing data to pipelines.", lastChecked: "Yesterday", latency: "—" },
};

function configurationFor(source: DataSource): ConfigurationField[] {
    const common = [{ label: "Environment", value: source.environment }, { label: "Connection type", value: source.type }, { label: "Authentication", value: "Managed secret" }, { label: "TLS / SSL", value: "Required" }];
    if (source.type === "Amazon S3") return [{ label: "Bucket", value: "datum-raw-data-prod", mono: true }, { label: "Region", value: "us-east-1", mono: true }, { label: "Path prefix", value: "incoming/", mono: true }, ...common];
    if (source.type === "Kafka") return [{ label: "Bootstrap servers", value: "events-01.internal:9093", mono: true }, { label: "Security protocol", value: "SASL_SSL", mono: true }, { label: "Consumer group", value: "datum-production", mono: true }, ...common];
    if (source.type === "Snowflake") return [{ label: "Account", value: "datum.us-east-1", mono: true }, { label: "Warehouse", value: "ANALYTICS_WH", mono: true }, { label: "Database", value: "ANALYTICS", mono: true }, { label: "Schema", value: "PUBLIC", mono: true }, ...common];
    return [{ label: "Host", value: `${source.name.replaceAll("_", "-")}.internal`, mono: true }, { label: "Port", value: source.type === "MySQL" ? "3306" : source.type === "SQL Server" ? "1433" : "5432", mono: true }, { label: "Database", value: source.name.split("_")[0], mono: true }, { label: "Username", value: "datum_service", mono: true }, ...common];
}

function pipelinesFor(source: DataSource): ConnectedPipeline[] {
    return pipelines.filter((pipeline) => pipeline.source.name === source.name).map((pipeline) => ({
        id: pipeline.id,
        name: pipeline.name,
        status: pipeline.status,
        schedule: pipeline.schedule,
        lastRun: pipeline.lastRun,
    }));
}

function activityFor(source: DataSource): SourceActivity[] {
    const health = healthByStatus[source.status];
    const firstTone = health.status === "Success" ? "success" : health.status === "Warning" ? "warning" : "error";
    return [
        { id: `${source.id}-activity-1`, tone: firstTone, title: health.status === "Success" ? "Connection check succeeded" : health.status === "Warning" ? "Connection check completed with a warning" : "Connection check failed", detail: health.message, actor: "System", time: source.lastCheck },
        { id: `${source.id}-activity-2`, tone: "success", title: "Pipeline read completed", detail: "The latest scheduled extraction completed successfully.", actor: "Scheduler", time: "3 hrs ago" },
        { id: `${source.id}-activity-3`, tone: "neutral", title: "Connection configuration updated", detail: "The managed credential reference was refreshed.", actor: "Maya Chen", time: "2 days ago" },
    ];
}

export const dataSourceDetails: DataSourceDetail[] = dataSources.map((source) => {
    const health = { ...healthByStatus[source.status], lastChecked: source.lastCheck };
    const validation: ValidationSummary = source.status === "Disconnected" ? { status: "Error", passed: 18, warnings: 0, failed: 4, lastRun: "1 hr ago" } : source.status === "Warning" ? { status: "Warning", passed: 26, warnings: 2, failed: 0, lastRun: "18 min ago" } : { status: "Success", passed: 24, warnings: 0, failed: 0, lastRun: source.lastCheck };
    return { ...source, description: `Managed ${source.type} source for ${source.environment.toLowerCase()} data workloads.`, owner: source.environment === "Production" ? "Data Platform" : "Analytics Engineering", createdAt: "Mar 14, 2025", health, configuration: configurationFor(source), connectedPipelines: pipelinesFor(source), validation, recentActivity: activityFor(source) };
});

export function getDataSourceDetail(sourceId: string) {
    return dataSourceDetails.find((source) => source.id === sourceId);
}
