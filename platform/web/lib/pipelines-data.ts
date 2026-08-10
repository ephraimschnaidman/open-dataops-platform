import type { OperationalResult } from "@/lib/operational-status";

export type PipelineStatus = "Healthy" | "Warning" | "Failed" | "Running" | "Disabled";
export type PipelineEnvironment = "Production" | "Staging" | "Development";
export type PipelineScheduleMode = "Scheduled" | "Manual";

export interface PipelineSource {
    name: string;
    technology: string;
}

export interface Pipeline {
    id: string;
    name: string;
    technicalId: string;
    status: PipelineStatus;
    environment: PipelineEnvironment;
    source: PipelineSource;
    destination?: string;
    schedule: string;
    scheduleMode: PipelineScheduleMode;
    lastRun: string;
    nextRun: string;
    duration: string;
    operationalIssue?: OperationalResult;
}

export const pipelines: Pipeline[] = [
    { id: "customer-ingestion", name: "Customer Ingestion", technicalId: "customer_ingestion", status: "Healthy", environment: "Production", source: { name: "Production Warehouse", technology: "PostgreSQL" }, destination: "Customer Lakehouse", schedule: "Hourly", scheduleMode: "Scheduled", lastRun: "8 min ago", nextRun: "In 52 min", duration: "2m 14s" },
    { id: "billing-reconciliation", name: "Billing Reconciliation", technicalId: "billing_reconciliation", status: "Warning", environment: "Production", source: { name: "Billing Database", technology: "PostgreSQL" }, destination: "Finance Warehouse", schedule: "Daily at 06:00", scheduleMode: "Scheduled", lastRun: "2 hr ago", nextRun: "Tomorrow at 06:00", duration: "11m 03s", operationalIssue: { status: "Warning", platformCode: "VALIDATION_CHECK_FAILED", message: "Three billing records failed the configured reconciliation checks.", recommendedAction: "Review rejected records before the next scheduled run." } },
    { id: "events-processing", name: "Events Processing", technicalId: "events_processing", status: "Failed", environment: "Production", source: { name: "Product Events", technology: "Kafka" }, destination: "Events Warehouse", schedule: "Continuous", scheduleMode: "Scheduled", lastRun: "18 min ago", nextRun: "Continuous", duration: "34s", operationalIssue: { status: "Error", platformCode: "PIPELINE_EXECUTION_FAILED", vendorCode: "Kafka NETWORK_EXCEPTION", message: "Broker connection was interrupted during event consumption.", recommendedAction: "Verify broker connectivity and restart the pipeline when the cluster is available." } },
    { id: "warehouse-sync", name: "Warehouse Sync", technicalId: "warehouse_sync", status: "Healthy", environment: "Production", source: { name: "Analytics Warehouse", technology: "Snowflake" }, destination: "Reporting Store", schedule: "Every 15 min", scheduleMode: "Scheduled", lastRun: "12 min ago", nextRun: "In 3 min", duration: "1m 08s" },
    { id: "legacy-reporting", name: "Legacy Reporting", technicalId: "legacy_reporting", status: "Disabled", environment: "Development", source: { name: "Legacy ERP", technology: "SQL Server" }, destination: "Reporting Archive", schedule: "Daily at 06:00", scheduleMode: "Scheduled", lastRun: "4 days ago", nextRun: "—", duration: "8m 42s" },
    { id: "manual-customer-export", name: "Manual Customer Export", technicalId: "manual_customer_export", status: "Healthy", environment: "Staging", source: { name: "Customer Warehouse", technology: "Snowflake" }, destination: "Secure Export Bucket", schedule: "Manual", scheduleMode: "Manual", lastRun: "Yesterday", nextRun: "Manual", duration: "4m 26s" },
    { id: "customer-profile-merge", name: "Customer Profile Merge", technicalId: "customer_profile_merge", status: "Running", environment: "Production", source: { name: "Customer Lakehouse", technology: "Amazon S3" }, destination: "Identity Store", schedule: "Weekdays at 02:00", scheduleMode: "Scheduled", lastRun: "7 hr ago", nextRun: "Tomorrow at 02:00", duration: "Running · 3m 41s" },
    { id: "inventory-snapshot", name: "Inventory Snapshot", technicalId: "inventory_snapshot", status: "Healthy", environment: "Production", source: { name: "Orders Database", technology: "MySQL" }, destination: "Operations Warehouse", schedule: "Hourly", scheduleMode: "Scheduled", lastRun: "42 min ago", nextRun: "In 18 min", duration: "56s" },
    { id: "marketing-attribution", name: "Marketing Attribution", technicalId: "marketing_attribution", status: "Healthy", environment: "Staging", source: { name: "Campaign Events", technology: "Kafka" }, destination: "Analytics Warehouse", schedule: "Every 15 min", scheduleMode: "Scheduled", lastRun: "6 min ago", nextRun: "In 9 min", duration: "1m 47s" },
    { id: "orders-incremental", name: "Orders Incremental", technicalId: "orders_incremental", status: "Healthy", environment: "Production", source: { name: "Orders Database", technology: "MySQL" }, destination: "Production Warehouse", schedule: "Every 15 min", scheduleMode: "Scheduled", lastRun: "5 min ago", nextRun: "In 10 min", duration: "48s" },
    { id: "product-analytics", name: "Product Analytics", technicalId: "product_analytics", status: "Healthy", environment: "Development", source: { name: "Product Events", technology: "Kafka" }, destination: "Development Warehouse", schedule: "Manual", scheduleMode: "Manual", lastRun: "Never", nextRun: "Manual", duration: "—" },
    { id: "raw-data-archive", name: "Raw Data Archive", technicalId: "raw_data_archive", status: "Healthy", environment: "Production", source: { name: "Raw Data Bucket", technology: "Amazon S3" }, destination: "Archive Bucket", schedule: "Daily at 06:00", scheduleMode: "Scheduled", lastRun: "Yesterday", nextRun: "Today at 18:00", duration: "6m 19s" },
];

const statusOrder: Record<PipelineStatus, number> = { Failed: 0, Warning: 1, Running: 2, Healthy: 3, Disabled: 4 };

export function sortPipelines(items: Pipeline[]) {
    return [...items].sort((a, b) => statusOrder[a.status] - statusOrder[b.status] || a.name.localeCompare(b.name));
}

export const pipelineMetrics = {
    total: pipelines.length,
    healthy: pipelines.filter((pipeline) => pipeline.status === "Healthy").length,
    attention: pipelines.filter((pipeline) => pipeline.status === "Warning" || pipeline.status === "Failed").length,
    failed: pipelines.filter((pipeline) => pipeline.status === "Failed").length,
};
