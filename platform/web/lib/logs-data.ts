export type LogLevel = "Error" | "Warning" | "Info" | "Debug";
export type LogEnvironment = "Production" | "Staging" | "Development";
export type LogScope = "all" | "pipeline" | "run" | "source" | "validation" | "platform";

export interface LogEvent {
    id: string;
    timestamp: string;
    level: LogLevel;
    message: string;
    pipeline?: string;
    pipelineId?: string;
    runId?: string;
    runLabel?: string;
    stage?: string;
    environment: LogEnvironment;
    source?: string;
    sourceId?: string;
    sourceType?: string;
    component: string;
    platformCode?: string;
    vendorCode?: string;
    interpretation?: string;
    details: Record<string, string | number | boolean>;
    stackTrace?: string;
    relatedAlert?: { id: string; status: "Open" | "Acknowledged" | "Resolved" };
}

export const logEvents: LogEvent[] = [
    { id: "evt-001", timestamp: "2026-08-10T14:42:38.412Z", level: "Error", pipeline: "Events Processing", pipelineId: "events-processing", runId: "run_01J94EVT18", runLabel: "94EVT18", stage: "Extract", environment: "Production", source: "Events Kafka", sourceId: "events-kafka", sourceType: "Kafka", component: "extractor", platformCode: "PIPELINE_EXECUTION_FAILED", vendorCode: "SASL_AUTHENTICATION_FAILED", message: "Events Kafka rejected the configured SASL credentials during extraction.", interpretation: "The extraction stopped after Events Kafka rejected all three authentication attempts.", details: { attempt: 3, max_attempts: 3, broker: "events-01.internal:9093", mechanism: "SCRAM-SHA-512", component: "extractor", credential: "[REDACTED]" }, stackTrace: "AuthenticationError: Events Kafka rejected SASL credentials\n    at KafkaConnector.connect (connector.ts:91:13)\n    at async ExtractStage.execute (stage.ts:72:9)\nCaused by: SASL_AUTHENTICATION_FAILED", relatedAlert: { id: "ALT-1042", status: "Open" } },
    { id: "evt-002", timestamp: "2026-08-10T14:42:37.981Z", level: "Warning", pipeline: "Events Processing", pipelineId: "events-processing", runId: "run_01J94EVT18", runLabel: "94EVT18", stage: "Extract", environment: "Production", source: "Events Kafka", sourceId: "events-kafka", sourceType: "Kafka", component: "extractor", platformCode: "SOURCE_CONNECTION_RETRY_FAILED", message: "Connection retry 3/3 failed.", details: { attempt: 3, max_attempts: 3, backoff_ms: 4000, component: "extractor" } },
    { id: "evt-003", timestamp: "2026-08-10T14:42:36.125Z", level: "Warning", pipeline: "Events Processing", pipelineId: "events-processing", runId: "run_01J94EVT18", runLabel: "94EVT18", stage: "Extract", environment: "Production", source: "Events Kafka", sourceId: "events-kafka", sourceType: "Kafka", component: "extractor", platformCode: "SOURCE_CONNECTION_RETRY_FAILED", message: "Connection retry 2/3 failed.", details: { attempt: 2, max_attempts: 3, backoff_ms: 2000 } },
    { id: "evt-004", timestamp: "2026-08-10T14:42:35.204Z", level: "Info", pipeline: "Events Processing", pipelineId: "events-processing", runId: "run_01J94EVT18", runLabel: "94EVT18", stage: "Extract", environment: "Production", source: "Events Kafka", sourceId: "events-kafka", sourceType: "Kafka", component: "extractor", message: "Extracting events topic.", details: { table: "events topic", batch_size: 5000 } },
    { id: "evt-005", timestamp: "2026-08-10T14:41:03.110Z", level: "Debug", pipeline: "Events Processing", pipelineId: "events-processing", runId: "run_01J94EVT18", runLabel: "94EVT18", stage: "Extract", environment: "Production", component: "extractor", message: "Extract stage started for the events topic.", details: { topic: "product-events", partition_count: 12, component: "extractor" } },
    { id: "evt-006", timestamp: "2026-08-10T14:05:39.046Z", level: "Info", pipeline: "Customer Ingestion", pipelineId: "customer-ingestion", runId: "run_01J92CVAL9", runLabel: "92CVAL9", stage: "Transform", environment: "Production", component: "transformer", platformCode: "STAGE_STARTED", message: "Beginning Transform stage.", details: { input_records: 125104, component: "transformer" } },
    { id: "evt-007", timestamp: "2026-08-10T13:36:42.000Z", level: "Error", pipeline: "Billing Reconciliation", pipelineId: "billing-reconciliation", runId: "run_01J97BIL02", runLabel: "97BIL02", stage: "Validate", environment: "Production", source: "Billing PostgreSQL", sourceId: "billing-postgres", sourceType: "PostgreSQL", component: "validator", platformCode: "VALIDATION_CHECK_FAILED", vendorCode: "CHECK_UNIQUENESS_VIOLATION", message: "Order ID unique found 318 duplicate order_id values; expected 0 duplicates. The blocking validation stopped execution before Load.", details: { check: "unique", field: "order_id", observed: "318 duplicates", threshold: "0 duplicates", evaluated_records: 118204 } },
    { id: "evt-008", timestamp: "2026-08-10T14:35:04.008Z", level: "Warning", environment: "Production", source: "Billing PostgreSQL", sourceId: "billing-postgres", sourceType: "PostgreSQL", component: "source-monitor", platformCode: "SOURCE_LATENCY_ELEVATED", message: "Source response latency exceeded the operational threshold.", details: { latency_ms: 418, threshold_ms: 300, region: "us-east-1" } },
    { id: "evt-009", timestamp: "2026-08-10T14:31:44.900Z", level: "Warning", pipeline: "Warehouse Sync", pipelineId: "warehouse-sync", environment: "Production", component: "runtime-monitor", platformCode: "PIPELINE_RUNTIME_DEGRADED", message: "Pipeline runtime is 38% above its seven-day baseline.", details: { runtime_seconds: 488, baseline_seconds: 353, deviation_percent: 38 } },
    { id: "evt-010", timestamp: "2026-08-10T14:29:11.018Z", level: "Info", pipeline: "Marketing Attribution", pipelineId: "marketing-attribution", stage: "Load", environment: "Staging", component: "loader", platformCode: "STAGE_COMPLETED", message: "Load stage completed successfully.", details: { records_written: 126011, elapsed_ms: 27384 } },
    { id: "evt-011", timestamp: "2026-08-10T14:24:52.602Z", level: "Debug", pipeline: "Product Analytics", pipelineId: "product-analytics", stage: "Transform", environment: "Development", component: "event-normalizer", message: "Normalized event fields for diagnostic sample.", details: { event_type: "page_view", fields: 18, sample: true } },
    { id: "evt-012", timestamp: "2026-08-10T14:20:00.000Z", level: "Info", environment: "Production", component: "scheduler", platformCode: "SCHEDULER_HEARTBEAT", message: "Scheduler heartbeat received.", details: { component: "scheduler", queue_depth: 2 } },
    { id: "evt-012b", timestamp: "2026-08-09T19:14:18.000Z", level: "Error", pipeline: "Customer Ingestion", pipelineId: "customer-ingestion", runId: "run_01JA7OLD40", runLabel: "JA7OLD40", stage: "Extract", environment: "Production", source: "Production Warehouse", sourceId: "analytics-warehouse", sourceType: "Snowflake", component: "connector", platformCode: "PIPELINE_EXECUTION_FAILED", vendorCode: "SNOWFLAKE_CONNECTION_RESET", message: "Production Warehouse reset the connection during extraction.", details: { account: "datum.us-east-1", warehouse: "ANALYTICS_WH", credential: "[REDACTED]" }, stackTrace: "ConnectionError: warehouse connection reset during extraction" },
    { id: "evt-013", timestamp: "2026-08-10T13:58:19.321Z", level: "Error", environment: "Production", source: "Events Kafka", sourceId: "events-kafka", sourceType: "Kafka", component: "connector", platformCode: "SOURCE_AUTHENTICATION_FAILED", vendorCode: "SASL_AUTHENTICATION_FAILED", message: "Authentication to the event broker failed.", details: { broker: "events-01.internal:9093", principal: "datum-service", password: "[REDACTED]" } },
    { id: "evt-014", timestamp: "2026-08-10T13:51:07.444Z", level: "Info", environment: "Staging", source: "Raw Data S3", sourceId: "raw-data-s3", sourceType: "Amazon S3", component: "schema-discovery", message: "Schema discovery completed for incoming customer files.", details: { objects_scanned: 42, columns_discovered: 31 } },
];

export const logPipelines = Array.from(new Map(logEvents.filter((event) => event.pipeline).map((event) => [event.pipelineId, { id: event.pipelineId!, name: event.pipeline! }])).values());
export const logSources = Array.from(new Map(logEvents.filter((event) => event.source).map((event) => [event.sourceId, { id: event.sourceId!, name: event.source! }])).values());
export const logStages = Array.from(new Set(logEvents.flatMap((event) => event.stage ? [event.stage] : [])));
export const platformCodes = Array.from(new Set(logEvents.flatMap((event) => event.platformCode ? [event.platformCode] : [])));
