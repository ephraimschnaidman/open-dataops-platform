import type {
    AlertSummary,
    DataSourceDetail,
    DataSourceListItem,
    PipelineDetail,
    PipelineListItem,
    PipelineRunDetail,
    PipelineRunListItem,
    AlertDetail,
    AlertListItem,
    LogEventDetail,
    LogEventListItem,
    RunSummary,
    TechnicalEvidenceSummary,
    ValidationExecutionDetail,
    ValidationListItem,
    ValidationExecutionSummary,
} from "./api-contract.ts";
import { enumDisplayLabel, formatDuration, formatTimestamp } from "./api-adapters.ts";

export const NOT_AVAILABLE = "Not available";

export function sourceStatusDisplay(value: DataSourceListItem["operational_status"]): "Healthy" | "Warning" | "Disconnected" | "Disabled" { return value === "HEALTHY" ? "Healthy" : value === "WARNING" ? "Warning" : value === "DISCONNECTED" ? "Disconnected" : "Disabled"; }
export function pipelineStatusDisplay(value: PipelineListItem["operational_status"]): "Healthy" | "Warning" | "Failed" | "Running" | "Disabled" { return value === "HEALTHY" ? "Healthy" : value === "WARNING" ? "Warning" : value === "FAILED" ? "Failed" : value === "RUNNING" ? "Running" : "Disabled"; }
export function runStatusDisplay(value: RunSummary["status"]): "Success" | "Failed" | "Running" { return value === "SUCCESS" ? "Success" : value === "FAILED" ? "Failed" : "Running"; }
export function alertStatusDisplay(value: AlertSummary["status"]): "Warning" | "Success" { return value === "RESOLVED" ? "Success" : "Warning"; }

export function environmentApiValue(display: string): string | undefined {
    return display === "All" ? undefined : display.toLowerCase();
}

export function enumApiValue(display: string): string | undefined {
    return display === "All" ? undefined : display.toUpperCase().replaceAll(" ", "_");
}

export interface SourceView {
    id: string; name: string; type: string; status: string; pipelines: number;
    lastCheck: string; environment: string;
}

export function mapDataSource(item: DataSourceListItem): SourceView {
    return {
        id: item.source_key,
        name: item.name,
        type: enumDisplayLabel(item.source_type).replace("Postgresql", "PostgreSQL").replace("Sql Server", "SQL Server"),
        status: sourceStatusDisplay(item.operational_status),
        pipelines: item.connected_pipeline_count,
        lastCheck: formatTimestamp(item.last_observed_at),
        environment: item.environment.name,
    };
}

export function mapPipeline(item: PipelineListItem) {
    return {
        id: item.pipeline_key,
        name: item.name,
        technicalId: item.pipeline_key,
        status: pipelineStatusDisplay(item.operational_status),
        environment: item.environment.name,
        source: { id: item.source.source_key, name: item.source.name, technology: enumDisplayLabel(item.source.source_type).replace("Postgresql", "PostgreSQL") },
        enabled: item.is_enabled,
        schedule: NOT_AVAILABLE,
        lastRun: item.latest_run ? formatTimestamp(item.latest_run.started_at) : NOT_AVAILABLE,
        nextRun: NOT_AVAILABLE,
        duration: item.latest_run ? formatDuration(item.latest_run.duration_seconds) : NOT_AVAILABLE,
        currentIssue: item.current_issue,
    };
}

export function mapPipelineRun(item: PipelineRunListItem) {
    return {
        id: item.corvetra_run_id,
        pipelineId: item.pipeline.pipeline_key,
        pipelineName: item.pipeline.name,
        sourceId: item.source.source_key,
        sourceName: item.source.name,
        environment: item.environment.name,
        status: runStatusDisplay(item.status),
        stage: item.stage ? enumDisplayLabel(item.stage) : NOT_AVAILABLE,
        startedAt: item.started_at,
        startedDisplay: formatTimestamp(item.started_at),
        durationSeconds: item.duration_seconds,
        duration: formatDuration(item.duration_seconds),
        platformCode: item.platform_code,
        vendorCode: item.vendor_code,
        ruleCode: item.rule_code,
        activeAlertCount: item.active_alert_count,
    };
}

function evidenceTone(level: TechnicalEvidenceSummary["level"]) {
    return level === "ERROR" ? "error" as const : level === "WARNING" ? "warning" as const : level === "INFO" ? "success" as const : "neutral" as const;
}

export function mapDataSourceDetail(item: DataSourceDetail) {
    const source = mapDataSource(item);
    const evidence = item.recent_evidence[0];
    return {
        ...source,
        description: NOT_AVAILABLE,
        owner: NOT_AVAILABLE,
        createdAt: NOT_AVAILABLE,
        health: {
            status: item.operational_status === "HEALTHY" ? "Success" as const : item.operational_status === "DISCONNECTED" ? "Error" as const : item.operational_status === "WARNING" ? "Warning" as const : "Neutral" as const,
            platformCode: evidence?.platform_code ?? `SOURCE_${item.operational_status}`,
            ...(evidence?.vendor_code ? { vendorCode: evidence.vendor_code } : {}),
            message: evidence?.message ?? "No recent technical evidence is available.",
            recommendedAction: NOT_AVAILABLE,
            lastChecked: source.lastCheck,
            latency: NOT_AVAILABLE,
        },
        configuration: [
            { label: "Source key", value: item.source_key, mono: true },
            { label: "Environment", value: item.environment.name },
            { label: "Connection type", value: source.type },
            { label: "Active alerts", value: String(item.active_alert_count) },
        ],
        connectedPipelines: item.connected_pipelines.map((pipeline) => ({
            id: pipeline.pipeline_key,
            name: pipeline.name,
            status: pipelineStatusDisplay(pipeline.operational_status),
            schedule: NOT_AVAILABLE,
            lastRun: pipeline.latest_run ? formatTimestamp(pipeline.latest_run.started_at) : NOT_AVAILABLE,
        })),
        validation: {
            status: item.validation_summary.failed ? "Error" as const : item.validation_summary.warning_failed ? "Warning" as const : "Success" as const,
            passed: item.validation_summary.passed,
            warnings: item.validation_summary.warning_failed,
            failed: item.validation_summary.failed,
            lastRun: formatTimestamp(item.validation_summary.last_evaluated_at),
        },
        recentActivity: item.recent_evidence.map((entry) => ({ id: entry.event_key, tone: evidenceTone(entry.level), title: entry.message, detail: [entry.platform_code, entry.vendor_code, entry.rule_code].filter(Boolean).join(" · ") || NOT_AVAILABLE, actor: "System", time: formatTimestamp(entry.occurred_at) })),
    };
}

function runSummaryView(run: RunSummary) {
    return { id: run.corvetra_run_id, status: runStatusDisplay(run.status), started: formatTimestamp(run.started_at), duration: formatDuration(run.duration_seconds), trigger: NOT_AVAILABLE, records: NOT_AVAILABLE };
}

function alertHealth(alert: AlertSummary | null, status: string) {
    if (alert) return { status: alert.severity === "CRITICAL" ? "Error" as const : "Warning" as const, platformCode: alert.platform_code, ...(alert.vendor_code ? { vendorCode: alert.vendor_code } : {}), ruleCode: alert.rule_code, message: alert.message, recommendedAction: NOT_AVAILABLE };
    return { status: status === "Healthy" ? "Success" as const : status === "Running" ? "Running" as const : status === "Failed" ? "Error" as const : status === "Disabled" ? "Neutral" as const : "Warning" as const, platformCode: `PIPELINE_${status.toUpperCase()}`, message: "No active alert details are available.", recommendedAction: NOT_AVAILABLE };
}

export function mapPipelineDetail(item: PipelineDetail) {
    const pipeline = mapPipeline(item);
    return {
        ...pipeline,
        schedule: NOT_AVAILABLE,
        destination: { name: NOT_AVAILABLE, type: NOT_AVAILABLE, status: "Healthy" as const },
        source: { ...pipeline.source, type: pipeline.source.technology, status: item.source.operational_status === "HEALTHY" ? "Healthy" as const : "Warning" as const, sourceId: item.source.source_key },
        latestRun: item.latest_run ? { value: runStatusDisplay(item.latest_run.status), detail: formatTimestamp(item.latest_run.started_at) } : { value: NOT_AVAILABLE, detail: NOT_AVAILABLE },
        nextRun: NOT_AVAILABLE,
        duration: item.latest_run ? formatDuration(item.latest_run.duration_seconds) : NOT_AVAILABLE,
        successRate: NOT_AVAILABLE,
        health: alertHealth(item.current_issue, pipeline.status),
        healthDetails: [
            { label: "Airflow DAG ID", value: item.airflow_dag_id },
            { label: "Technical evidence", value: String(item.technical_evidence_count) },
            ...(item.current_issue?.rule_code ? [{ label: "Rule code", value: item.current_issue.rule_code }] : []),
        ],
        recentRuns: item.recent_runs.map(runSummaryView),
        validation: { activeChecks: item.validation_summary.total, passing: item.validation_summary.passed, failed: item.validation_summary.failed, lastEvaluated: formatTimestamp(item.validation_summary.last_evaluated_at), ...(item.current_issue?.platform_code === "VALIDATION_CHECK_FAILED" ? { platformCode: item.current_issue.platform_code } : {}) },
        configuration: [
            { label: "Pipeline key", value: item.pipeline_key, mono: true },
            { label: "Airflow DAG ID", value: item.airflow_dag_id, mono: true },
            { label: "Environment", value: item.environment.name },
            { label: "Source", value: item.source.name },
            { label: "Enabled", value: item.is_enabled ? "Yes" : "No" },
        ],
        dependencies: [],
        monitoring: [{ label: "Technical evidence", value: String(item.technical_evidence_count) }],
        activity: item.recent_runs.map((run) => ({ id: run.corvetra_run_id, time: formatTimestamp(run.started_at), title: `${enumDisplayLabel(run.status)} pipeline run`, code: run.platform_code ?? NOT_AVAILABLE, tone: run.status === "FAILED" ? "error" as const : run.status === "SUCCESS" ? "success" as const : "neutral" as const })),
        runStartOutcome: "failure" as const,
    };
}

function validationView(executions: ValidationExecutionSummary[], total: number, passed: number, failed: number) {
    const failedExecution = executions.find((execution) => execution.result === "FAILED");
    return {
        checks: total, passing: passed, failed,
        evaluatedAt: failedExecution?.evaluated_at ?? executions[0]?.evaluated_at,
        platformCode: failedExecution?.platform_code,
        vendorCode: failedExecution?.vendor_code,
        ruleCode: failedExecution?.rule_code,
        failure: failedExecution ? { check: failedExecution.name, field: failedExecution.column_name ?? NOT_AVAILABLE, observed: failedExecution.actual ?? NOT_AVAILABLE, threshold: failedExecution.expected ?? NOT_AVAILABLE } : undefined,
    };
}

export function mapPipelineRunDetail(item: PipelineRunDetail) {
    const evidence = item.technical_evidence[0];
    const currentStage = item.stage;
    return {
        id: item.corvetra_run_id,
        pipelineId: item.pipeline.pipeline_key,
        pipelineName: item.pipeline.name,
        sourceId: item.source.source_key,
        sourceName: item.source.name,
        environment: item.environment.name,
        status: runStatusDisplay(item.status),
        trigger: NOT_AVAILABLE,
        startedAt: item.started_at,
        finishedAt: item.completed_at ?? undefined,
        duration: formatDuration(item.duration_seconds),
        platformCode: item.platform_code ?? evidence?.platform_code ?? NOT_AVAILABLE,
        vendorCode: item.vendor_code ?? evidence?.vendor_code ?? undefined,
        ruleCode: item.rule_code ?? evidence?.rule_code ?? undefined,
        message: evidence?.message ?? "No technical execution message is available.",
        recommendedAction: NOT_AVAILABLE,
        airflow: item.airflow,
        alerts: item.alerts,
        stages: currentStage ? [{ name: enumDisplayLabel(currentStage), state: item.status === "FAILED" ? "Failed" as const : item.status === "RUNNING" ? "Running" as const : "Completed" as const, duration: formatDuration(item.duration_seconds), platformCode: item.platform_code ?? undefined, vendorCode: item.vendor_code ?? undefined, ruleCode: item.rule_code ?? undefined, message: evidence?.message }] : [],
        validation: validationView(item.validation_executions, item.validation_summary.total, item.validation_summary.passed, item.validation_summary.failed),
        relatedRuns: [],
        events: item.technical_evidence.map((entry) => ({ id: entry.event_key, timestamp: entry.occurred_at, title: entry.message, code: entry.platform_code ?? entry.rule_code ?? entry.vendor_code ?? NOT_AVAILABLE, tone: entry.level === "ERROR" ? "error" as const : entry.level === "INFO" ? "success" as const : "neutral" as const })),
    };
}

export function mapAlert(item: AlertListItem | AlertDetail) {
    return {
        id: item.alert_key,
        title: item.title,
        severity: enumDisplayLabel(item.severity),
        status: enumDisplayLabel(item.status),
        message: item.message,
        environment: item.environment.name,
        pipelineId: item.pipeline.pipeline_key,
        pipelineName: item.pipeline.name,
        runId: item.run.corvetra_run_id,
        sourceId: item.source.source_key,
        sourceName: item.source.name,
        platformCode: item.platform_code,
        vendorCode: item.vendor_code,
        ruleCode: item.rule_code,
        detectedAt: formatTimestamp(item.detected_at),
        lastSeenAt: formatTimestamp(item.last_seen_at),
        acknowledgedAt: formatTimestamp(item.acknowledged_at),
        resolvedAt: formatTimestamp(item.resolved_at),
        validation: item.validation_execution ? {
            ...item.validation_execution,
            platform_code: "platform_code" in item.validation_execution ? item.validation_execution.platform_code : NOT_AVAILABLE,
            vendor_code: "vendor_code" in item.validation_execution ? item.validation_execution.vendor_code : null,
            rule_code: "rule_code" in item.validation_execution ? item.validation_execution.rule_code : null,
        } : null,
    };
}

export function mapValidation(item: ValidationListItem | ValidationExecutionDetail) {
    return {
        checkKey: item.check_key,
        runId: item.run.corvetra_run_id,
        name: item.name,
        checkType: enumDisplayLabel(item.type),
        datasetName: item.dataset_name,
        columnName: item.column_name ?? NOT_AVAILABLE,
        result: enumDisplayLabel(item.result),
        severity: enumDisplayLabel(item.severity),
        stage: enumDisplayLabel(item.stage),
        pipelineId: item.pipeline.pipeline_key,
        pipelineName: item.pipeline.name,
        sourceId: item.source.source_key,
        sourceName: item.source.name,
        environment: item.environment.name,
        platformCode: item.platform_code,
        vendorCode: item.vendor_code,
        ruleCode: item.rule_code,
        actual: item.actual ?? NOT_AVAILABLE,
        expected: item.expected ?? NOT_AVAILABLE,
        message: item.message,
        evaluatedAt: formatTimestamp(item.evaluated_at),
    };
}

export function mapLogEvent(item: LogEventListItem | LogEventDetail) {
    return {
        id: item.event_key,
        timestamp: formatTimestamp(item.occurred_at),
        occurredAt: item.occurred_at,
        level: enumDisplayLabel(item.level),
        message: item.message,
        environment: item.environment.name,
        pipelineId: item.pipeline?.pipeline_key ?? null,
        pipelineName: item.pipeline?.name ?? null,
        runId: item.run?.corvetra_run_id ?? null,
        sourceId: item.source?.source_key ?? null,
        sourceName: item.source?.name ?? null,
        stage: item.stage ? enumDisplayLabel(item.stage) : null,
        platformCode: item.platform_code,
        vendorCode: item.vendor_code,
        ruleCode: item.rule_code,
        alertId: item.related_alert?.alert_key ?? null,
        validationCheckKey: item.related_validation?.check_key ?? null,
    };
}
