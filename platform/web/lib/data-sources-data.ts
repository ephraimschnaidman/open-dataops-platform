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
    { id: "billing-postgres", name: "billing_postgres", type: "PostgreSQL", status: "Healthy", pipelines: 5, lastCheck: "2 min ago", environment: "Production" },
    { id: "analytics-warehouse", name: "analytics_warehouse", type: "Snowflake", status: "Warning", pipelines: 8, lastCheck: "18 min ago", environment: "Production" },
    { id: "orders-mysql", name: "orders_mysql", type: "MySQL", status: "Healthy", pipelines: 4, lastCheck: "6 min ago", environment: "Production" },
    { id: "events-kafka", name: "events_kafka", type: "Kafka", status: "Disconnected", pipelines: 3, lastCheck: "1 hr ago", environment: "Production" },
    { id: "raw-data-s3", name: "raw_data_s3", type: "Amazon S3", status: "Healthy", pipelines: 6, lastCheck: "4 min ago", environment: "Staging" },
    { id: "customer-sqlserver", name: "customer_sqlserver", type: "SQL Server", status: "Disabled", pipelines: 0, lastCheck: "Yesterday", environment: "Development" },
];

const attentionOrder: Record<DataSourceStatus, number> = { Disconnected: 0, Warning: 1, Healthy: 2, Disabled: 2 };

export function sortDataSources(sources: DataSource[]) {
    return [...sources].sort((a, b) => attentionOrder[a.status] - attentionOrder[b.status] || a.name.localeCompare(b.name));
}
