from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from api.schemas.core_resources import (
    AlertSeverity,
    AlertStatus,
    DataSourceSummary,
    EnvironmentSummary,
    EventLevel,
    PipelineSummary,
    RunSummary,
    StageName,
    ValidationCheckType,
    ValidationResult,
    ValidationSeverity,
)
from api.schemas.data_sources import DataSourceListItem
from api.schemas.pipeline_runs import PipelineRunListItem
from api.schemas.pipelines import PipelineListItem

MonitoringWindow = Literal["1h", "6h", "24h", "7d", "30d"]
HealthWindow = Literal["24h", "7d", "30d", "90d"]
MetricAvailability = Literal["AVAILABLE", "INSUFFICIENT_DATA", "UNSUPPORTED"]
MetricUnit = Literal["PERCENT", "SECONDS", "COUNT"]
OperationalState = Literal["HEALTHY", "WARNING", "CRITICAL"]
StateAvailability = Literal["AVAILABLE", "NO_DATA"]


class AggregationPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window: str
    start: AwareDatetime
    end: AwareDatetime


class AggregationScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environment: str | None
    pipeline: str | None
    source: str | None


class MetricComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability: MetricAvailability
    value: float | None
    sample_count: int = Field(ge=0)


class MetricPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: AwareDatetime
    end: AwareDatetime
    value: float
    sample_count: int = Field(ge=1)


class AggregationMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability: MetricAvailability
    unit: MetricUnit
    value: float | None
    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, ge=0)
    sample_count: int = Field(ge=0)
    previous: MetricComparison
    delta: float | None
    points: list[MetricPoint]
    reason: str | None


class RunMetricSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_success_rate: AggregationMetric
    successful_runs: AggregationMetric
    failed_runs: AggregationMetric
    average_runtime: AggregationMetric
    schedule_adherence: AggregationMetric
    healthy_sources: AggregationMetric


class ValidationCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_key: str
    name: str
    type: ValidationCheckType
    result: ValidationResult
    severity: ValidationSeverity
    platform_code: str
    rule_code: str | None
    vendor_code: str | None
    actual: str | None
    expected: str | None
    message: str
    evaluated_at: AwareDatetime
    run: RunSummary
    pipeline: PipelineSummary
    source: DataSourceSummary
    environment: EnvironmentSummary
    represented_by_alert_key: str | None


class ActiveIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_key: str
    origin: Literal["ALERT", "SOURCE", "PIPELINE", "VALIDATION", "RUN"]
    severity: AlertSeverity
    title: str
    message: str
    platform_code: str | None
    vendor_code: str | None
    rule_code: str | None
    observed_at: AwareDatetime | None
    alert_key: str | None
    alert_status: AlertStatus | None
    environment: EnvironmentSummary
    pipeline: PipelineSummary | None
    source: DataSourceSummary | None
    run: RunSummary | None
    validation: ValidationCondition | None
    technical_evidence_count: int = Field(ge=0)
    latest_event_key: str | None


class PipelineHealthItem(PipelineListItem):
    period_success_rate: AggregationMetric
    period_average_runtime: AggregationMetric
    successful_runs: int = Field(ge=0)
    failed_runs: int = Field(ge=0)
    running_runs: int = Field(ge=0)
    active_issue_keys: list[str]


class ActivityItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["RUN", "TECHNICAL_EVENT"]
    occurred_at: AwareDatetime
    environment: EnvironmentSummary
    pipeline: PipelineSummary | None
    source: DataSourceSummary | None
    run: RunSummary | None
    event_key: str | None
    level: EventLevel | None
    stage: StageName | None
    platform_code: str | None
    vendor_code: str | None
    rule_code: str | None
    message: str


class IssueCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ActiveIssue]
    total: int = Field(ge=0)
    truncated: bool


class PipelineHealthCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[PipelineHealthItem]
    total: int = Field(ge=0)
    truncated: bool


class SourceHealthCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[DataSourceListItem]
    total: int = Field(ge=0)
    truncated: bool


class RunCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[PipelineRunListItem]
    total: int = Field(ge=0)
    truncated: bool


class ValidationConditionCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ValidationCondition]
    total: int = Field(ge=0)
    truncated: bool


class ActivityCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ActivityItem]
    total: int = Field(ge=0)
    truncated: bool


class MonitoringResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: AwareDatetime
    period: AggregationPeriod
    scope: AggregationScope
    state_availability: StateAvailability
    overall_state: OperationalState | None
    metrics: RunMetricSet
    active_issues: IssueCollection
    pipeline_health: PipelineHealthCollection
    source_health: SourceHealthCollection
    recent_failed_runs: RunCollection
    validation_conditions: ValidationConditionCollection
    recent_activity: ActivityCollection


class HistoricalMetricSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_success_rate: AggregationMetric
    average_runtime: AggregationMetric
    validation_pass_rate: AggregationMetric
    source_availability: AggregationMetric
    freshness_compliance: AggregationMetric
    schedule_adherence: AggregationMetric


class PipelineReliabilityItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline: PipelineSummary
    success_rate: AggregationMetric
    average_runtime: AggregationMetric
    successful_runs: int = Field(ge=0)
    failed_runs: int = Field(ge=0)
    running_runs: int = Field(ge=0)


class ValidationQualityItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_key: str
    name: str
    pipeline: PipelineSummary
    severity: ValidationSeverity
    pass_rate: AggregationMetric
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    not_evaluated: int = Field(ge=0)
    blocking_failed: int = Field(ge=0)
    warning_failed: int = Field(ge=0)


class ReviewResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_key: str
    resource_type: Literal["PIPELINE", "SOURCE", "VALIDATION"]
    name: str
    signal: str
    severity: AlertSeverity
    pipeline_key: str | None
    source_key: str | None
    check_key: str | None


class HealthMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: AwareDatetime
    period: AggregationPeriod
    comparison_period: AggregationPeriod
    scope: AggregationScope
    metrics: HistoricalMetricSet
    pipeline_reliability: list[PipelineReliabilityItem]
    validation_quality: list[ValidationQualityItem]
    current_source_connectivity: list[DataSourceListItem]
    resources_requiring_review: list[ReviewResource]


class AlertCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total: int = Field(ge=0)
    critical: int = Field(ge=0)
    warning: int = Field(ge=0)


class DashboardSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configured_pipelines: int = Field(ge=0)
    enabled_pipelines: int = Field(ge=0)
    successful_runs: int = Field(ge=0)
    failed_runs: int = Field(ge=0)
    active_alerts: AlertCounts
    sources: int = Field(ge=0)
    non_disabled_sources: int = Field(ge=0)


class DashboardHealthIndicators(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_success_rate: AggregationMetric
    validation_pass_rate: AggregationMetric
    healthy_sources: AggregationMetric
    freshness_compliance: AggregationMetric


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: AwareDatetime
    period: AggregationPeriod
    environment: str | None
    state_availability: StateAvailability
    overall_state: OperationalState | None
    summary: DashboardSummary
    health_indicators: DashboardHealthIndicators
    active_issues: IssueCollection
    pipelines_requiring_attention: PipelineHealthCollection
    latest_runs: RunCollection
    recent_activity: ActivityCollection
