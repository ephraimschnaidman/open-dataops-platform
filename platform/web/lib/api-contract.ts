export type IsoTimestamp = string;
export type SourceType = "KAFKA" | "POSTGRESQL" | "SNOWFLAKE" | "SQL_SERVER";
export type DataSourceOperationalStatus = "HEALTHY" | "WARNING" | "DISCONNECTED" | "DISABLED";
export type PipelineOperationalStatus = "HEALTHY" | "WARNING" | "FAILED" | "RUNNING" | "DISABLED";
export type RunStatus = "SUCCESS" | "FAILED" | "RUNNING";
export type StageName = "EXTRACT" | "TRANSFORM" | "VALIDATE" | "LOAD";
export type AlertSeverity = "CRITICAL" | "WARNING";
export type AlertStatus = "OPEN" | "ACKNOWLEDGED" | "RESOLVED";
export type ValidationResult = "PASSED" | "FAILED" | "NOT_EVALUATED";
export type ValidationSeverity = "WARNING" | "BLOCKING";
export type ValidationCheckType = "NOT_NULL" | "UNIQUE" | "ACCEPTED_VALUES" | "RANGE" | "FRESHNESS" | "ROW_COUNT" | "REFERENTIAL_INTEGRITY" | "CUSTOM";
export type EventLevel = "ERROR" | "WARNING" | "INFO" | "DEBUG";
export type MetricAvailability = "AVAILABLE" | "INSUFFICIENT_DATA" | "UNSUPPORTED";
export type MetricUnit = "PERCENT" | "SECONDS" | "COUNT";
export type OperationalState = "HEALTHY" | "WARNING" | "CRITICAL";
export type StateAvailability = "AVAILABLE" | "NO_DATA";

export interface PaginationMetadata { limit: number; offset: number; total: number; returned_count: number }
export interface EnvironmentSummary { environment_key: string; name: string }
export interface DataSourceSummary { source_key: string; name: string; source_type: SourceType; operational_status: DataSourceOperationalStatus }
export interface PipelineSummary { pipeline_key: string; name: string; operational_status: PipelineOperationalStatus }
export interface RunSummary { corvetra_run_id: string; status: RunStatus; stage: StageName | null; started_at: IsoTimestamp; completed_at: IsoTimestamp | null; duration_seconds: number | null; platform_code: string | null; vendor_code: string | null; rule_code: string | null }
export interface AlertSummary { alert_key: string; title: string; severity: AlertSeverity; status: AlertStatus; platform_code: string; vendor_code: string | null; rule_code: string | null; message: string; detected_at: IsoTimestamp; last_seen_at: IsoTimestamp; acknowledged_at: IsoTimestamp | null; resolved_at: IsoTimestamp | null }
export interface ValidationSummary { total: number; passed: number; failed: number; not_evaluated: number; blocking_failed: number; warning_failed: number; last_evaluated_at: IsoTimestamp | null }
export interface ValidationExecutionSummary { check_key: string; name: string; type: ValidationCheckType; dataset_name: string; column_name: string | null; result: ValidationResult; severity: ValidationSeverity; platform_code: string; rule_code: string | null; vendor_code: string | null; actual: string | null; expected: string | null; message: string; evaluated_at: IsoTimestamp }
export interface TechnicalEvidenceSummary { event_key: string; occurred_at: IsoTimestamp; level: EventLevel; stage: StageName | null; platform_code: string | null; vendor_code: string | null; rule_code: string | null; message: string }

export interface DataSourceListItem { source_key: string; name: string; source_type: SourceType; environment: EnvironmentSummary; operational_status: DataSourceOperationalStatus; connected_pipeline_count: number; last_observed_at: IsoTimestamp | null }
export interface ConnectedPipelineSummary { pipeline_key: string; name: string; is_enabled: boolean; operational_status: PipelineOperationalStatus; latest_run: RunSummary | null }
export interface DataSourceDetail extends DataSourceListItem { connected_pipelines: ConnectedPipelineSummary[]; validation_summary: ValidationSummary; active_alert_count: number; recent_evidence: TechnicalEvidenceSummary[] }
export interface DataSourceListResponse { items: DataSourceListItem[]; pagination: PaginationMetadata }

export interface PipelineListItem { pipeline_key: string; name: string; environment: EnvironmentSummary; source: DataSourceSummary; is_enabled: boolean; operational_status: PipelineOperationalStatus; latest_run: RunSummary | null; current_issue: AlertSummary | null }
export interface PipelineDetail extends PipelineListItem { airflow_dag_id: string; recent_runs: RunSummary[]; validation_summary: ValidationSummary; active_alerts: AlertSummary[]; technical_evidence_count: number }
export interface PipelineListResponse { items: PipelineListItem[]; pagination: PaginationMetadata }

export interface PipelineRunListItem { corvetra_run_id: string; pipeline: PipelineSummary; source: DataSourceSummary; environment: EnvironmentSummary; status: RunStatus; stage: StageName | null; started_at: IsoTimestamp; completed_at: IsoTimestamp | null; duration_seconds: number | null; platform_code: string | null; vendor_code: string | null; rule_code: string | null; active_alert_count: number }
export interface AirflowIdentity { dag_id: string; airflow_run_id: string }
export interface PipelineRunDetail extends PipelineRunListItem { airflow: AirflowIdentity; alerts: AlertSummary[]; validation_summary: ValidationSummary; validation_executions: ValidationExecutionSummary[]; technical_evidence_count: number; technical_evidence: TechnicalEvidenceSummary[] }
export interface PipelineRunListResponse { items: PipelineRunListItem[]; pagination: PaginationMetadata }

export interface ValidationExecutionReference { check_key: string; name: string; result: ValidationResult; severity: ValidationSeverity; evaluated_at: IsoTimestamp }
export interface AlertListItem extends AlertSummary { pipeline: PipelineSummary; run: RunSummary; source: DataSourceSummary; environment: EnvironmentSummary; validation_execution: ValidationExecutionReference | null }
export interface AlertDetail extends Omit<AlertListItem, "validation_execution"> { validation_execution: ValidationExecutionSummary | null; technical_evidence_count: number; recent_technical_evidence: TechnicalEvidenceSummary[] }
export interface AlertListResponse { items: AlertListItem[]; pagination: PaginationMetadata }

export interface ValidationListItem extends ValidationExecutionSummary { stage: StageName; run: RunSummary; pipeline: PipelineSummary; source: DataSourceSummary; environment: EnvironmentSummary }
export interface ValidationExecutionHistoryItem { corvetra_run_id: string; result: ValidationResult; severity: ValidationSeverity; actual: string | null; expected: string | null; platform_code: string; vendor_code: string | null; rule_code: string | null; evaluated_at: IsoTimestamp }
export interface ValidationExecutionDetail extends ValidationListItem { related_alerts: AlertSummary[]; technical_evidence_count: number; technical_evidence: TechnicalEvidenceSummary[]; recent_executions: ValidationExecutionHistoryItem[] }
export interface ValidationListResponse { items: ValidationListItem[]; pagination: PaginationMetadata }

export interface RelatedAlertReference { alert_key: string; status: AlertStatus }
export interface LogEventListItem { event_key: string; occurred_at: IsoTimestamp; level: EventLevel; message: string; environment: EnvironmentSummary; pipeline: PipelineSummary | null; run: RunSummary | null; source: DataSourceSummary | null; stage: StageName | null; platform_code: string | null; vendor_code: string | null; rule_code: string | null; related_alert: RelatedAlertReference | null; related_validation: ValidationExecutionReference | null }
export interface LogEventDetail extends LogEventListItem { details: Record<string, unknown>; interpretation: string | null; stack_trace: string | null; alert: AlertSummary | null; validation_execution: ValidationExecutionSummary | null }
export interface LogEventListResponse { items: LogEventListItem[]; pagination: PaginationMetadata }

export interface AggregationPeriod { window: string; start: IsoTimestamp; end: IsoTimestamp }
export interface AggregationScope { environment: string | null; pipeline: string | null; source: string | null }
export interface MetricComparison { availability: MetricAvailability; value: number | null; sample_count: number }
export interface MetricPoint { start: IsoTimestamp; end: IsoTimestamp; value: number; sample_count: number }
export interface AggregationMetric { availability: MetricAvailability; unit: MetricUnit; value: number | null; numerator: number | null; denominator: number | null; sample_count: number; previous: MetricComparison; delta: number | null; points: MetricPoint[]; reason: string | null }
export interface RunMetricSet { pipeline_success_rate: AggregationMetric; successful_runs: AggregationMetric; failed_runs: AggregationMetric; average_runtime: AggregationMetric; schedule_adherence: AggregationMetric; healthy_sources: AggregationMetric }
export interface ValidationCondition extends Omit<ValidationExecutionSummary, "dataset_name" | "column_name"> { run: RunSummary; pipeline: PipelineSummary; source: DataSourceSummary; environment: EnvironmentSummary; represented_by_alert_key: string | null }
export interface ActiveIssue { issue_key: string; origin: "ALERT" | "SOURCE" | "PIPELINE" | "VALIDATION" | "RUN"; severity: AlertSeverity; title: string; message: string; platform_code: string | null; vendor_code: string | null; rule_code: string | null; observed_at: IsoTimestamp | null; alert_key: string | null; alert_status: AlertStatus | null; environment: EnvironmentSummary; pipeline: PipelineSummary | null; source: DataSourceSummary | null; run: RunSummary | null; validation: ValidationCondition | null; technical_evidence_count: number; latest_event_key: string | null }
export interface PipelineHealthItem extends PipelineListItem { period_success_rate: AggregationMetric; period_average_runtime: AggregationMetric; successful_runs: number; failed_runs: number; running_runs: number; active_issue_keys: string[] }
export interface ActivityItem { kind: "RUN" | "TECHNICAL_EVENT"; occurred_at: IsoTimestamp; environment: EnvironmentSummary; pipeline: PipelineSummary | null; source: DataSourceSummary | null; run: RunSummary | null; event_key: string | null; level: EventLevel | null; stage: StageName | null; platform_code: string | null; vendor_code: string | null; rule_code: string | null; message: string }
export interface Collection<T> { items: T[]; total: number; truncated: boolean }
export interface MonitoringResponse { generated_at: IsoTimestamp; period: AggregationPeriod; scope: AggregationScope; state_availability: StateAvailability; overall_state: OperationalState | null; metrics: RunMetricSet; active_issues: Collection<ActiveIssue>; pipeline_health: Collection<PipelineHealthItem>; source_health: Collection<DataSourceListItem>; recent_failed_runs: Collection<PipelineRunListItem>; validation_conditions: Collection<ValidationCondition>; recent_activity: Collection<ActivityItem> }

export interface HistoricalMetricSet { pipeline_success_rate: AggregationMetric; average_runtime: AggregationMetric; validation_pass_rate: AggregationMetric; source_availability: AggregationMetric; freshness_compliance: AggregationMetric; schedule_adherence: AggregationMetric }
export interface PipelineReliabilityItem { pipeline: PipelineSummary; success_rate: AggregationMetric; average_runtime: AggregationMetric; successful_runs: number; failed_runs: number; running_runs: number }
export interface ValidationQualityItem { check_key: string; name: string; pipeline: PipelineSummary; severity: ValidationSeverity; pass_rate: AggregationMetric; passed: number; failed: number; not_evaluated: number; blocking_failed: number; warning_failed: number }
export interface ReviewResource { resource_key: string; resource_type: "PIPELINE" | "SOURCE" | "VALIDATION"; name: string; signal: string; severity: AlertSeverity; pipeline_key: string | null; source_key: string | null; check_key: string | null }
export interface HealthMetricsResponse { generated_at: IsoTimestamp; period: AggregationPeriod; comparison_period: AggregationPeriod; scope: AggregationScope; metrics: HistoricalMetricSet; pipeline_reliability: PipelineReliabilityItem[]; validation_quality: ValidationQualityItem[]; current_source_connectivity: DataSourceListItem[]; resources_requiring_review: ReviewResource[] }

export interface AlertCounts { total: number; critical: number; warning: number }
export interface DashboardSummary { configured_pipelines: number; enabled_pipelines: number; successful_runs: number; failed_runs: number; active_alerts: AlertCounts; sources: number; non_disabled_sources: number }
export interface DashboardHealthIndicators { pipeline_success_rate: AggregationMetric; validation_pass_rate: AggregationMetric; healthy_sources: AggregationMetric; freshness_compliance: AggregationMetric }
export interface DashboardResponse { generated_at: IsoTimestamp; period: AggregationPeriod; environment: string | null; state_availability: StateAvailability; overall_state: OperationalState | null; summary: DashboardSummary; health_indicators: DashboardHealthIndicators; active_issues: Collection<ActiveIssue>; pipelines_requiring_attention: Collection<PipelineHealthItem>; latest_runs: Collection<PipelineRunListItem>; recent_activity: Collection<ActivityItem> }
