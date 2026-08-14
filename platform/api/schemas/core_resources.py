from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

SourceType = Literal["KAFKA", "POSTGRESQL", "SNOWFLAKE", "SQL_SERVER"]
DataSourceOperationalStatus = Literal[
    "HEALTHY", "WARNING", "DISCONNECTED", "DISABLED"
]
PipelineOperationalStatus = Literal[
    "HEALTHY", "WARNING", "FAILED", "RUNNING", "DISABLED"
]
RunStatus = Literal["SUCCESS", "FAILED", "RUNNING"]
StageName = Literal["EXTRACT", "TRANSFORM", "VALIDATE", "LOAD"]
AlertSeverity = Literal["CRITICAL", "WARNING"]
AlertStatus = Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"]
ValidationResult = Literal["PASSED", "FAILED", "NOT_EVALUATED"]
ValidationSeverity = Literal["WARNING", "BLOCKING"]
ValidationCheckType = Literal[
    "NOT_NULL", "UNIQUE", "ACCEPTED_VALUES", "RANGE", "FRESHNESS",
    "ROW_COUNT", "REFERENTIAL_INTEGRITY", "CUSTOM",
]
EventLevel = Literal["ERROR", "WARNING", "INFO", "DEBUG"]


class PaginationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    returned_count: int = Field(ge=0)


class EnvironmentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environment_key: str
    name: str


class DataSourceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str
    name: str
    source_type: SourceType
    operational_status: DataSourceOperationalStatus


class PipelineSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_key: str
    name: str
    operational_status: PipelineOperationalStatus


class RunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corvetra_run_id: str
    status: RunStatus
    stage: StageName | None
    started_at: AwareDatetime
    completed_at: AwareDatetime | None
    duration_seconds: float | None = Field(ge=0)
    platform_code: str | None
    vendor_code: str | None
    rule_code: str | None


class AlertSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_key: str
    title: str
    severity: AlertSeverity
    status: AlertStatus
    platform_code: str
    vendor_code: str | None
    rule_code: str | None
    message: str
    detected_at: AwareDatetime
    last_seen_at: AwareDatetime
    acknowledged_at: AwareDatetime | None
    resolved_at: AwareDatetime | None


class ValidationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    not_evaluated: int = Field(ge=0)
    blocking_failed: int = Field(ge=0)
    warning_failed: int = Field(ge=0)
    last_evaluated_at: AwareDatetime | None


class TechnicalEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_key: str
    occurred_at: AwareDatetime
    level: EventLevel
    stage: StageName | None
    platform_code: str | None
    vendor_code: str | None
    rule_code: str | None
    message: str


class ApiErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str
