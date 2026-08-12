export const WORKSPACE_TIME_ZONE = "America/New_York";
export const DEMO_NOW = "2026-08-10T14:45:00.000Z";

export const pipelineIds = {
    customerIngestion: "customer-ingestion",
    billingReconciliation: "billing-reconciliation",
    eventsProcessing: "events-processing",
    warehouseSync: "warehouse-sync",
    riskReporting: "risk-reporting",
    manualCustomerExport: "manual-customer-export",
} as const;

export const sourceIds = {
    productionWarehouse: "analytics-warehouse",
    billingPostgres: "billing-postgres",
    eventsKafka: "events-kafka",
    legacySqlServer: "customer-sqlserver",
} as const;

export const runIds = {
    customerIngestionSuccess: "run_01J92CING8",
    customerIngestionValidationWarning: "run_01J92CVAL9",
    customerIngestionHistoricalFailure: "run_01JA7OLD40",
    billingValidationFailure: "run_01J97BIL02",
    eventsProcessingFailure: "run_01J94EVT18",
    warehouseValidationFailure: "run_01J98WVAL4",
} as const;

export const alertIds = {
    eventsProcessingFailure: "ALT-1042",
    billingValidationFailure: "ALT-1040",
    customerIngestionHistoricalFailure: "ALT-1037",
} as const;

export const validationIds = {
    customerEmailNullRate: "customer-email-null-rate",
    orderIdUnique: "order-id-unique",
} as const;

export const canonicalPipelines = {
    [pipelineIds.customerIngestion]: { name: "Customer Ingestion", environment: "Production" },
    [pipelineIds.billingReconciliation]: { name: "Billing Reconciliation", environment: "Production" },
    [pipelineIds.eventsProcessing]: { name: "Events Processing", environment: "Production" },
    [pipelineIds.warehouseSync]: { name: "Warehouse Sync", environment: "Production" },
    [pipelineIds.riskReporting]: { name: "Risk Reporting", environment: "Production" },
    [pipelineIds.manualCustomerExport]: { name: "Manual Customer Export", environment: "Staging" },
} as const;

export const canonicalSources = {
    [sourceIds.productionWarehouse]: { name: "Production Warehouse", environment: "Production" },
    [sourceIds.billingPostgres]: { name: "Billing PostgreSQL", environment: "Production" },
    [sourceIds.eventsKafka]: { name: "Events Kafka", environment: "Production" },
    [sourceIds.legacySqlServer]: { name: "Legacy SQL Server", environment: "Development" },
} as const;

export const incidentCodes = {
    pipelineExecutionFailed: "PIPELINE_EXECUTION_FAILED",
    eventsKafkaAuthenticationFailed: "SASL_AUTHENTICATION_FAILED",
    validationCheckFailed: "VALIDATION_CHECK_FAILED",
    orderIdUniqueFailed: "CHECK_UNIQUENESS_VIOLATION",
    customerEmailNullRateFailed: "CHECK_NULL_RATE_THRESHOLD",
} as const;

export const incidentTimes = {
    events: {
        runStarted: "2026-08-10T14:41:03.000Z",
        extractStarted: "2026-08-10T14:41:03.110Z",
        retryTwoFailed: "2026-08-10T14:42:36.125Z",
        retryThreeFailed: "2026-08-10T14:42:37.981Z",
        failed: "2026-08-10T14:42:38.412Z",
    },
    billing: {
        runStarted: "2026-08-10T13:28:00.000Z",
        validationFailed: "2026-08-10T13:36:42.000Z",
    },
    customerSuccess: {
        runStarted: "2026-08-10T14:32:00.000Z",
        validationCompleted: "2026-08-10T14:33:48.000Z",
        completed: "2026-08-10T14:34:14.000Z",
    },
    customerValidation: {
        runStarted: "2026-08-10T14:05:00.000Z",
        validationFailed: "2026-08-10T14:06:45.000Z",
        completed: "2026-08-10T14:07:20.000Z",
    },
    customerHistoricalFailure: {
        runStarted: "2026-08-09T19:14:00.000Z",
        failed: "2026-08-09T19:14:18.000Z",
    },
} as const;
