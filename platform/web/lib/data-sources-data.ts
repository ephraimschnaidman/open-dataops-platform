import { sourceIds } from "@/lib/canonical-demo";

export type DataSourceStatus = "Healthy" | "Warning" | "Disconnected" | "Disabled";
export type DataSourceEnvironment = "Production" | "Staging" | "Development";
export type DataSourceType = "PostgreSQL" | "Snowflake" | "MySQL" | "Kafka" | "Amazon S3" | "SQL Server";

export interface DataSource {
    id: string;
    name: string;
    type: DataSourceType;
    status: DataSourceStatus;
    pipelines: number;
    lastCheck: string;
    environment: DataSourceEnvironment;
}

export const dataSources: DataSource[] = [
    { id: sourceIds.billingPostgres, name: "Billing PostgreSQL", type: "PostgreSQL", status: "Warning", pipelines: 1, lastCheck: "5 min ago", environment: "Production" },
    { id: sourceIds.productionWarehouse, name: "Production Warehouse", type: "Snowflake", status: "Healthy", pipelines: 3, lastCheck: "2 min ago", environment: "Production" },
    { id: "orders-mysql", name: "Orders Database", type: "MySQL", status: "Healthy", pipelines: 2, lastCheck: "6 min ago", environment: "Production" },
    { id: sourceIds.eventsKafka, name: "Events Kafka", type: "Kafka", status: "Disconnected", pipelines: 1, lastCheck: "2 min ago", environment: "Production" },
    { id: "raw-data-s3", name: "Raw Data S3", type: "Amazon S3", status: "Healthy", pipelines: 1, lastCheck: "4 min ago", environment: "Staging" },
    { id: sourceIds.legacySqlServer, name: "Legacy SQL Server", type: "SQL Server", status: "Disabled", pipelines: 1, lastCheck: "Yesterday", environment: "Development" },
];

const attentionOrder: Record<DataSourceStatus, number> = { Disconnected: 0, Warning: 1, Healthy: 2, Disabled: 2 };

export function sortDataSources(sources: DataSource[]) {
    return [...sources].sort((a, b) => attentionOrder[a.status] - attentionOrder[b.status] || a.name.localeCompare(b.name));
}
