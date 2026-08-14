from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Callable, Sequence

from api.repositories.aggregations import AggregationFilters, AggregationRepository
from api.schemas.aggregations import (
    ActiveIssue,
    ActivityCollection,
    ActivityItem,
    AggregationMetric,
    AggregationPeriod,
    AggregationScope,
    AlertCounts,
    DashboardHealthIndicators,
    DashboardResponse,
    DashboardSummary,
    HealthMetricsResponse,
    HistoricalMetricSet,
    IssueCollection,
    MetricComparison,
    MetricPoint,
    MonitoringResponse,
    PipelineHealthCollection,
    PipelineHealthItem,
    PipelineReliabilityItem,
    ReviewResource,
    RunCollection,
    RunMetricSet,
    SourceHealthCollection,
    ValidationCondition,
    ValidationConditionCollection,
    ValidationQualityItem,
)
from api.schemas.core_resources import DataSourceSummary, PipelineSummary
from api.schemas.data_sources import DataSourceListItem
from api.schemas.pipeline_runs import PipelineRunListItem
from api.schemas.pipelines import PipelineListItem

WINDOWS = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}
PIPELINE_ORDER = {"FAILED": 0, "WARNING": 1, "RUNNING": 2, "HEALTHY": 3, "DISABLED": 4}
SOURCE_ORDER = {"DISCONNECTED": 0, "WARNING": 1, "HEALTHY": 2, "DISABLED": 3}


class AggregationService:
    def __init__(
        self,
        repository: AggregationRepository,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _periods(self, window: str) -> tuple[datetime, AggregationPeriod, AggregationPeriod]:
        end = self._clock()
        duration = WINDOWS[window]
        start = end - duration
        previous_start = start - duration
        return end, AggregationPeriod(window=window, start=start, end=end), AggregationPeriod(
            window=window, start=previous_start, end=start
        )

    @staticmethod
    def _scope(filters: AggregationFilters) -> AggregationScope:
        return AggregationScope(
            environment=filters.environment,
            pipeline=filters.pipeline,
            source=filters.source,
        )

    @staticmethod
    def _comparison(availability: str, value: float | None, count: int) -> MetricComparison:
        return MetricComparison(availability=availability, value=value, sample_count=count)

    @staticmethod
    def _unsupported(unit: str, reason: str) -> AggregationMetric:
        return AggregationMetric(
            availability="UNSUPPORTED", unit=unit, value=None,
            sample_count=0, previous=MetricComparison(
                availability="UNSUPPORTED", value=None, sample_count=0
            ), delta=None, points=[], reason=reason,
        )

    @staticmethod
    def _bucket_size(window: str) -> timedelta:
        if window == "24h":
            return timedelta(hours=1)
        if window == "90d":
            return timedelta(days=7)
        return timedelta(days=1)

    @classmethod
    def _points(
        cls,
        rows: Sequence[dict],
        *,
        period: AggregationPeriod,
        timestamp: str,
        calculator: Callable[[Sequence[dict]], float | None],
    ) -> list[MetricPoint]:
        buckets: dict[int, list[dict]] = defaultdict(list)
        bucket_size = cls._bucket_size(period.window)
        seconds = bucket_size.total_seconds()
        for row in rows:
            index = int((row[timestamp] - period.start).total_seconds() // seconds)
            if index >= 0:
                buckets[index].append(row)
        points: list[MetricPoint] = []
        for index in sorted(buckets):
            value = calculator(buckets[index])
            if value is None:
                continue
            start = period.start + bucket_size * index
            points.append(MetricPoint(
                start=start,
                end=min(start + bucket_size, period.end),
                value=value,
                sample_count=len(buckets[index]),
            ))
        return points

    @classmethod
    def _rate_metric(
        cls,
        current: Sequence[dict],
        previous: Sequence[dict],
        *,
        period: AggregationPeriod,
        numerator_status: str,
        denominator_statuses: set[str],
        status_field: str,
        timestamp_field: str,
    ) -> AggregationMetric:
        def values(rows: Sequence[dict]) -> tuple[int, int, float | None]:
            denominator = sum(row[status_field] in denominator_statuses for row in rows)
            numerator = sum(row[status_field] == numerator_status for row in rows)
            return numerator, denominator, (numerator / denominator * 100 if denominator else None)

        eligible_current = [row for row in current if row[status_field] in denominator_statuses]
        eligible_previous = [row for row in previous if row[status_field] in denominator_statuses]
        numerator, denominator, value = values(eligible_current)
        _, previous_denominator, previous_value = values(eligible_previous)
        available = "AVAILABLE" if denominator else "INSUFFICIENT_DATA"
        previous_available = "AVAILABLE" if previous_denominator else "INSUFFICIENT_DATA"
        points = cls._points(
            eligible_current,
            period=period,
            timestamp=timestamp_field,
            calculator=lambda rows: values(rows)[2],
        )
        return AggregationMetric(
            availability=available,
            unit="PERCENT",
            value=value,
            numerator=numerator,
            denominator=denominator,
            sample_count=denominator,
            previous=cls._comparison(previous_available, previous_value, previous_denominator),
            delta=(value - previous_value if value is not None and previous_value is not None else None),
            points=points,
            reason=None if denominator else "No qualifying completed samples in the selected period",
        )

    @classmethod
    def _runtime_metric(
        cls,
        current: Sequence[dict],
        previous: Sequence[dict],
        *,
        period: AggregationPeriod,
    ) -> AggregationMetric:
        def valid(rows: Sequence[dict]) -> list[dict]:
            return [row for row in rows if row.get("duration_seconds") is not None
                    and row["duration_seconds"] >= 0 and row.get("status") in {"SUCCESS", "FAILED"}]

        def average(rows: Sequence[dict]) -> float | None:
            samples = valid(rows)
            return sum(float(row["duration_seconds"]) for row in samples) / len(samples) if samples else None

        samples, previous_samples = valid(current), valid(previous)
        value, previous_value = average(samples), average(previous_samples)
        return AggregationMetric(
            availability="AVAILABLE" if samples else "INSUFFICIENT_DATA",
            unit="SECONDS", value=value, sample_count=len(samples),
            previous=cls._comparison(
                "AVAILABLE" if previous_samples else "INSUFFICIENT_DATA",
                previous_value, len(previous_samples),
            ),
            delta=(value - previous_value if value is not None and previous_value is not None else None),
            points=cls._points(
                samples, period=period, timestamp="started_at", calculator=average
            ),
            reason=None if samples else "No completed runs with valid timestamps in the selected period",
        )

    @classmethod
    def _count_metric(
        cls, current: Sequence[dict], previous: Sequence[dict], *, status: str
    ) -> AggregationMetric:
        value = sum(row.get("status") == status for row in current)
        previous_value = sum(row.get("status") == status for row in previous)
        return AggregationMetric(
            availability="AVAILABLE", unit="COUNT", value=float(value),
            numerator=value, denominator=len(current), sample_count=len(current),
            previous=cls._comparison("AVAILABLE", float(previous_value), len(previous)),
            delta=float(value - previous_value), points=[], reason=None,
        )

    @classmethod
    def _source_metric(cls, sources: Sequence[dict]) -> AggregationMetric:
        eligible = [row for row in sources if row["operational_status"] != "DISABLED"]
        healthy = sum(row["operational_status"] == "HEALTHY" for row in eligible)
        return AggregationMetric(
            availability="AVAILABLE" if eligible else "INSUFFICIENT_DATA",
            unit="COUNT", value=float(healthy) if eligible else None,
            numerator=healthy, denominator=len(eligible), sample_count=len(eligible),
            previous=cls._comparison("UNSUPPORTED", None, 0), delta=None, points=[],
            reason=None if eligible else "No non-disabled sources are available in this scope",
        )

    @staticmethod
    def _run_rows(rows: Sequence[dict], start: datetime, end: datetime) -> list[dict]:
        return [row for row in rows if start <= row["started_at"] < end]

    @staticmethod
    def _validation_rows(rows: Sequence[dict], start: datetime, end: datetime) -> list[dict]:
        return [row for row in rows if start <= row["evaluated_at"] < end]

    @staticmethod
    def _pipeline_item(row: dict) -> PipelineListItem:
        return PipelineListItem.model_validate({key: value for key, value in row.items()
                                                if key not in {"pipeline_id", "data_source_id", "latest_run_uuid"}})

    @staticmethod
    def _source_item(row: dict) -> DataSourceListItem:
        return DataSourceListItem.model_validate({key: value for key, value in row.items()
                                                  if key != "data_source_id"})

    @staticmethod
    def _condition(row: dict) -> ValidationCondition:
        return ValidationCondition.model_validate({
            "check_key": row["check_key"], "name": row["name"], "type": row["type"],
            "result": row["result"], "severity": row["severity"],
            "platform_code": row["platform_code"], "rule_code": row["rule_code"],
            "vendor_code": row["vendor_code"], "actual": row["actual"],
            "expected": row["expected"], "message": row["message"],
            "evaluated_at": row["evaluated_at"], "run": row["run"],
            "pipeline": row["pipeline"], "source": row["source"],
            "environment": row["environment"],
            "represented_by_alert_key": row.get("alert_key"),
        })

    def _issues(
        self,
        pipelines: Sequence[dict],
        sources: Sequence[dict],
        alerts: Sequence[dict],
        validations: Sequence[dict],
    ) -> tuple[list[ActiveIssue], list[ValidationCondition]]:
        conditions = [self._condition(row) for row in validations]
        condition_by_id = {row["validation_execution_id"]: condition
                           for row, condition in zip(validations, conditions)}
        covered_runs: set[object] = set()
        covered_validations: set[object] = set()
        covered_sources: set[object] = set()
        issues: list[ActiveIssue] = []

        for row in alerts:
            validation = condition_by_id.get(row.get("validation_execution_id"))
            covered_runs.add(row["pipeline_run_id"])
            if row.get("validation_execution_id") is not None:
                covered_validations.add(row["validation_execution_id"])
            if row["source"]["operational_status"] == "DISCONNECTED" and row.get("vendor_code"):
                covered_sources.add(row["data_source_id"])
            issues.append(ActiveIssue.model_validate({
                "issue_key": row["alert_key"], "origin": "ALERT",
                "severity": row["severity"], "title": row["title"],
                "message": row["message"], "platform_code": row["platform_code"],
                "vendor_code": row["vendor_code"], "rule_code": row["rule_code"],
                "observed_at": row["last_seen_at"], "alert_key": row["alert_key"],
                "alert_status": row["status"], "environment": row["environment"],
                "pipeline": row["pipeline"], "source": row["source"], "run": row["run"],
                "validation": validation,
                "technical_evidence_count": row.get("evidence_count") or 0,
                "latest_event_key": row.get("latest_event_key"),
            }))

        source_issues: dict[object, ActiveIssue] = {}
        for row in sources:
            status = row["operational_status"]
            if status not in {"DISCONNECTED", "WARNING"} or row["data_source_id"] in covered_sources:
                continue
            source = DataSourceSummary.model_validate({
                "source_key": row["source_key"], "name": row["name"],
                "source_type": row["source_type"],
                "operational_status": row["operational_status"],
            })
            severity = "CRITICAL" if status == "DISCONNECTED" else "WARNING"
            issue = ActiveIssue.model_validate({
                "issue_key": f"source:{row['source_key']}:{status.lower()}",
                "origin": "SOURCE", "severity": severity,
                "title": f"{row['name']} is {status.lower()}",
                "message": f"Current source status is {status}.",
                "platform_code": None, "vendor_code": None, "rule_code": None,
                "observed_at": None, "alert_key": None, "alert_status": None,
                "environment": row["environment"], "pipeline": None, "source": source,
                "run": None, "validation": None, "technical_evidence_count": 0,
                "latest_event_key": None,
            })
            source_issues[row["data_source_id"]] = issue
            issues.append(issue)

        for row in pipelines:
            status = row["operational_status"]
            latest_run_id = row.get("latest_run_uuid")
            if status not in {"FAILED", "WARNING"} or latest_run_id in covered_runs:
                continue
            if row["data_source_id"] in source_issues:
                continue
            severity = "CRITICAL" if status == "FAILED" else "WARNING"
            latest_run = row.get("latest_run") or {}
            issues.append(ActiveIssue.model_validate({
                "issue_key": f"pipeline:{row['pipeline_key']}:{status.lower()}",
                "origin": "PIPELINE", "severity": severity,
                "title": f"{row['pipeline_name'] if 'pipeline_name' in row else row['name']} is {status.lower()}",
                "message": f"Current pipeline status is {status}.",
                "platform_code": latest_run.get("platform_code"),
                "vendor_code": latest_run.get("vendor_code"),
                "rule_code": latest_run.get("rule_code"),
                "observed_at": latest_run.get("completed_at") or latest_run.get("started_at"),
                "alert_key": None, "alert_status": None,
                "environment": row["environment"],
                "pipeline": {"pipeline_key": row["pipeline_key"], "name": row["name"],
                             "operational_status": status},
                "source": row["source"], "run": row.get("latest_run"),
                "validation": None, "technical_evidence_count": 0,
                "latest_event_key": None,
            }))

        for row, condition in zip(validations, conditions):
            if row["validation_execution_id"] in covered_validations:
                continue
            severity = "CRITICAL" if row["severity"] == "BLOCKING" else "WARNING"
            issues.append(ActiveIssue.model_validate({
                "issue_key": f"validation:{row['check_key']}:{row['run']['corvetra_run_id']}",
                "origin": "VALIDATION", "severity": severity,
                "title": f"{row['name']} failed", "message": row["message"],
                "platform_code": row["platform_code"], "vendor_code": row["vendor_code"],
                "rule_code": row["rule_code"], "observed_at": row["evaluated_at"],
                "alert_key": None, "alert_status": None, "environment": row["environment"],
                "pipeline": row["pipeline"], "source": row["source"], "run": row["run"],
                "validation": condition,
                "technical_evidence_count": row.get("evidence_count") or 0,
                "latest_event_key": row.get("latest_event_key"),
            }))

        issues.sort(key=lambda issue: (
            0 if issue.severity == "CRITICAL" else 1,
            -(issue.observed_at.timestamp() if issue.observed_at else 0),
            issue.issue_key,
        ))
        return issues, conditions

    @staticmethod
    def _overall_state(issues: Sequence[ActiveIssue], pipelines: Sequence[dict], sources: Sequence[dict]):
        evaluable = any(row["is_enabled"] for row in pipelines) or any(
            row["operational_status"] != "DISABLED" for row in sources
        )
        if not evaluable:
            return "NO_DATA", None
        if any(issue.severity == "CRITICAL" for issue in issues):
            return "AVAILABLE", "CRITICAL"
        if issues:
            return "AVAILABLE", "WARNING"
        return "AVAILABLE", "HEALTHY"

    @staticmethod
    def _activity_from_run(row: dict) -> ActivityItem:
        return ActivityItem.model_validate({
            "kind": "RUN", "occurred_at": row["started_at"],
            "environment": row["environment"], "pipeline": row["pipeline"],
            "source": row["source"],
            "run": {key: row[key] for key in (
                "corvetra_run_id", "status", "stage", "started_at", "completed_at",
                "duration_seconds", "platform_code", "vendor_code", "rule_code")},
            "event_key": None, "level": None, "stage": row["stage"],
            "platform_code": row["platform_code"], "vendor_code": row["vendor_code"],
            "rule_code": row["rule_code"],
            "message": f"{row['pipeline']['name']} run {row['status'].lower()}.",
        })

    @staticmethod
    def _activity_from_event(row: dict) -> ActivityItem:
        return ActivityItem.model_validate({"kind": "TECHNICAL_EVENT", **row})

    @staticmethod
    def _collection(items: Sequence, limit: int) -> tuple[list, int, bool]:
        return list(items[:limit]), len(items), len(items) > limit

    async def get_monitoring(self, *, window: str, filters: AggregationFilters) -> MonitoringResponse:
        _, period, previous_period = self._periods(window)
        history_start = previous_period.start
        pipelines = await self._repository.get_pipelines(filters)
        sources = await self._repository.get_sources(filters)
        alerts = await self._repository.get_active_alerts(filters)
        validations = await self._repository.get_latest_failed_validations(filters)
        runs = await self._repository.get_runs(
            filters, started_from=history_start, started_to=period.end
        )
        events = await self._repository.get_events(
            filters, occurred_from=period.start, occurred_to=period.end
        )
        current_runs = self._run_rows(runs, period.start, period.end)
        previous_runs = self._run_rows(runs, previous_period.start, previous_period.end)
        issues, conditions = self._issues(pipelines, sources, alerts, validations)
        state_availability, overall_state = self._overall_state(issues, pipelines, sources)
        success_rate = self._rate_metric(
            current_runs, previous_runs, period=period, numerator_status="SUCCESS",
            denominator_statuses={"SUCCESS", "FAILED"}, status_field="status",
            timestamp_field="started_at",
        )
        runtime = self._runtime_metric(current_runs, previous_runs, period=period)
        unsupported_schedule = self._unsupported(
            "PERCENT", "Expected schedules and start windows are not persisted"
        )
        source_metric = self._source_metric(sources)

        issue_keys_by_pipeline: dict[str, list[str]] = defaultdict(list)
        for issue in issues:
            if issue.pipeline:
                issue_keys_by_pipeline[issue.pipeline.pipeline_key].append(issue.issue_key)
        pipeline_health: list[PipelineHealthItem] = []
        for row in pipelines:
            item = self._pipeline_item(row)
            current = [run for run in current_runs if run["pipeline"]["pipeline_key"] == item.pipeline_key]
            previous = [run for run in previous_runs if run["pipeline"]["pipeline_key"] == item.pipeline_key]
            pipeline_health.append(PipelineHealthItem.model_validate({
                **item.model_dump(),
                "period_success_rate": self._rate_metric(
                    current, previous, period=period, numerator_status="SUCCESS",
                    denominator_statuses={"SUCCESS", "FAILED"}, status_field="status",
                    timestamp_field="started_at",
                ),
                "period_average_runtime": self._runtime_metric(current, previous, period=period),
                "successful_runs": sum(run["status"] == "SUCCESS" for run in current),
                "failed_runs": sum(run["status"] == "FAILED" for run in current),
                "running_runs": sum(run["status"] == "RUNNING" for run in current),
                "active_issue_keys": issue_keys_by_pipeline[item.pipeline_key],
            }))
        pipeline_health.sort(key=lambda item: (PIPELINE_ORDER[item.operational_status], item.name, item.pipeline_key))
        source_items = [self._source_item(row) for row in sources]
        source_items.sort(key=lambda item: (SOURCE_ORDER[item.operational_status], item.name, item.source_key))

        failed_rows = [row for row in current_runs if row["status"] == "FAILED"]
        failed_items = [PipelineRunListItem.model_validate({key: value for key, value in row.items()
                                                            if key != "pipeline_run_id"}) for row in failed_rows]
        activity = [self._activity_from_run(row) for row in current_runs]
        activity.extend(self._activity_from_event(row) for row in events)
        activity.sort(key=lambda item: item.occurred_at, reverse=True)

        issue_items, issue_total, issue_truncated = self._collection(issues, 20)
        pipeline_items, pipeline_total, pipeline_truncated = self._collection(pipeline_health, 50)
        source_section, source_total, source_truncated = self._collection(source_items, 50)
        failed_section, failed_total, failed_truncated = self._collection(failed_items, 10)
        condition_section, condition_total, condition_truncated = self._collection(conditions, 20)
        activity_section, activity_total, activity_truncated = self._collection(activity, 20)
        return MonitoringResponse(
            generated_at=period.end, period=period, scope=self._scope(filters),
            state_availability=state_availability, overall_state=overall_state,
            metrics=RunMetricSet(
                pipeline_success_rate=success_rate,
                successful_runs=self._count_metric(current_runs, previous_runs, status="SUCCESS"),
                failed_runs=self._count_metric(current_runs, previous_runs, status="FAILED"),
                average_runtime=runtime, schedule_adherence=unsupported_schedule,
                healthy_sources=source_metric,
            ),
            active_issues=IssueCollection(items=issue_items, total=issue_total, truncated=issue_truncated),
            pipeline_health=PipelineHealthCollection(items=pipeline_items, total=pipeline_total, truncated=pipeline_truncated),
            source_health=SourceHealthCollection(items=source_section, total=source_total, truncated=source_truncated),
            recent_failed_runs=RunCollection(items=failed_section, total=failed_total, truncated=failed_truncated),
            validation_conditions=ValidationConditionCollection(items=condition_section, total=condition_total, truncated=condition_truncated),
            recent_activity=ActivityCollection(items=activity_section, total=activity_total, truncated=activity_truncated),
        )

    def _validation_metric(
        self, current: Sequence[dict], previous: Sequence[dict], period: AggregationPeriod
    ) -> AggregationMetric:
        return self._rate_metric(
            current, previous, period=period, numerator_status="PASSED",
            denominator_statuses={"PASSED", "FAILED"}, status_field="result_status",
            timestamp_field="evaluated_at",
        )

    async def get_health_metrics(self, *, window: str, filters: AggregationFilters) -> HealthMetricsResponse:
        _, period, previous_period = self._periods(window)
        pipelines = await self._repository.get_pipelines(filters)
        sources = await self._repository.get_sources(filters)
        runs = await self._repository.get_runs(
            filters, started_from=previous_period.start, started_to=period.end
        )
        validations = await self._repository.get_validation_history(
            filters, evaluated_from=previous_period.start, evaluated_to=period.end
        )
        current_runs = self._run_rows(runs, period.start, period.end)
        previous_runs = self._run_rows(runs, previous_period.start, previous_period.end)
        current_validations = self._validation_rows(validations, period.start, period.end)
        previous_validations = self._validation_rows(validations, previous_period.start, previous_period.end)
        success = self._rate_metric(
            current_runs, previous_runs, period=period, numerator_status="SUCCESS",
            denominator_statuses={"SUCCESS", "FAILED"}, status_field="status",
            timestamp_field="started_at",
        )
        runtime = self._runtime_metric(current_runs, previous_runs, period=period)
        validation_metric = self._validation_metric(current_validations, previous_validations, period)
        unsupported_source = self._unsupported(
            "PERCENT", "Data source operational status is a current snapshot, not availability history"
        )
        unsupported_freshness = self._unsupported(
            "PERCENT", "Legacy table freshness metrics are not mapped to canonical pipelines"
        )
        unsupported_schedule = self._unsupported(
            "PERCENT", "Expected schedules and start windows are not persisted"
        )

        reliability: list[PipelineReliabilityItem] = []
        for row in pipelines:
            pipeline = PipelineSummary(
                pipeline_key=row["pipeline_key"], name=row["name"],
                operational_status=row["operational_status"],
            )
            current = [run for run in current_runs if run["pipeline"]["pipeline_key"] == pipeline.pipeline_key]
            previous = [run for run in previous_runs if run["pipeline"]["pipeline_key"] == pipeline.pipeline_key]
            reliability.append(PipelineReliabilityItem(
                pipeline=pipeline,
                success_rate=self._rate_metric(
                    current, previous, period=period, numerator_status="SUCCESS",
                    denominator_statuses={"SUCCESS", "FAILED"}, status_field="status",
                    timestamp_field="started_at",
                ),
                average_runtime=self._runtime_metric(current, previous, period=period),
                successful_runs=sum(run["status"] == "SUCCESS" for run in current),
                failed_runs=sum(run["status"] == "FAILED" for run in current),
                running_runs=sum(run["status"] == "RUNNING" for run in current),
            ))
        reliability.sort(key=lambda item: item.pipeline.name)

        validation_quality: list[ValidationQualityItem] = []
        for check_key in sorted({row["check_key"] for row in validations}):
            current = [row for row in current_validations if row["check_key"] == check_key]
            previous = [row for row in previous_validations if row["check_key"] == check_key]
            representative = (current or previous)[-1]
            validation_quality.append(ValidationQualityItem(
                check_key=check_key, name=representative["check_name"],
                pipeline=PipelineSummary(
                    pipeline_key=representative["pipeline_key"],
                    name=representative["pipeline_name"],
                    operational_status=representative["operational_status"],
                ),
                severity=representative["effective_severity"],
                pass_rate=self._validation_metric(current, previous, period),
                passed=sum(row["result_status"] == "PASSED" for row in current),
                failed=sum(row["result_status"] == "FAILED" for row in current),
                not_evaluated=sum(row["result_status"] == "NOT_EVALUATED" for row in current),
                blocking_failed=sum(row["result_status"] == "FAILED" and row["effective_severity"] == "BLOCKING" for row in current),
                warning_failed=sum(row["result_status"] == "FAILED" and row["effective_severity"] == "WARNING" for row in current),
            ))

        reviews: list[ReviewResource] = []
        for item in reliability:
            if item.failed_runs:
                reviews.append(ReviewResource(
                    resource_key=item.pipeline.pipeline_key, resource_type="PIPELINE",
                    name=item.pipeline.name, signal=f"{item.failed_runs} failed run(s)",
                    severity="CRITICAL", pipeline_key=item.pipeline.pipeline_key,
                    source_key=None, check_key=None,
                ))
        for item in validation_quality:
            if item.failed:
                reviews.append(ReviewResource(
                    resource_key=item.check_key, resource_type="VALIDATION", name=item.name,
                    signal=f"{item.failed} failed validation execution(s)",
                    severity="CRITICAL" if item.blocking_failed else "WARNING",
                    pipeline_key=item.pipeline.pipeline_key, source_key=None,
                    check_key=item.check_key,
                ))
        for row in sources:
            if row["operational_status"] in {"DISCONNECTED", "WARNING"}:
                reviews.append(ReviewResource(
                    resource_key=row["source_key"], resource_type="SOURCE", name=row["name"],
                    signal=f"Current status {row['operational_status']}",
                    severity="CRITICAL" if row["operational_status"] == "DISCONNECTED" else "WARNING",
                    pipeline_key=None, source_key=row["source_key"], check_key=None,
                ))
        reviews.sort(key=lambda item: (0 if item.severity == "CRITICAL" else 1, item.name))
        source_items = [self._source_item(row) for row in sources]
        source_items.sort(key=lambda item: (
            SOURCE_ORDER[item.operational_status], item.name, item.source_key
        ))
        return HealthMetricsResponse(
            generated_at=period.end, period=period, comparison_period=previous_period,
            scope=self._scope(filters),
            metrics=HistoricalMetricSet(
                pipeline_success_rate=success, average_runtime=runtime,
                validation_pass_rate=validation_metric,
                source_availability=unsupported_source,
                freshness_compliance=unsupported_freshness,
                schedule_adherence=unsupported_schedule,
            ),
            pipeline_reliability=reliability,
            validation_quality=validation_quality,
            current_source_connectivity=source_items,
            resources_requiring_review=reviews[:20],
        )

    async def get_dashboard(self, *, environment: str | None) -> DashboardResponse:
        filters = AggregationFilters(environment=environment)
        monitoring = await self.get_monitoring(window="24h", filters=filters)
        previous_start = monitoring.period.start - WINDOWS["24h"]
        validations = await self._repository.get_validation_history(
            filters, evaluated_from=previous_start, evaluated_to=monitoring.period.end
        )
        current_validations = self._validation_rows(
            validations, monitoring.period.start, monitoring.period.end
        )
        previous_validations = self._validation_rows(
            validations, previous_start, monitoring.period.start
        )
        validation_metric = self._validation_metric(
            current_validations, previous_validations, monitoring.period
        )
        pipelines = await self._repository.get_pipelines(filters)
        sources = await self._repository.get_sources(filters)
        alerts = await self._repository.get_active_alerts(filters)
        latest_runs = await self._repository.get_runs(filters)
        latest_events = await self._repository.get_events(filters)
        activities = [self._activity_from_event(row) for row in latest_events]
        activities.extend(self._activity_from_run(row) for row in latest_runs)
        activities.sort(key=lambda item: item.occurred_at, reverse=True)
        attention = [item for item in monitoring.pipeline_health.items
                     if item.operational_status in {"FAILED", "WARNING"}]
        return DashboardResponse(
            generated_at=monitoring.generated_at, period=monitoring.period,
            environment=environment, state_availability=monitoring.state_availability,
            overall_state=monitoring.overall_state,
            summary=DashboardSummary(
                configured_pipelines=len(pipelines),
                enabled_pipelines=sum(row["is_enabled"] for row in pipelines),
                successful_runs=int(monitoring.metrics.successful_runs.value or 0),
                failed_runs=int(monitoring.metrics.failed_runs.value or 0),
                active_alerts=AlertCounts(
                    total=len(alerts),
                    critical=sum(row["severity"] == "CRITICAL" for row in alerts),
                    warning=sum(row["severity"] == "WARNING" for row in alerts),
                ),
                sources=len(sources),
                non_disabled_sources=sum(row["operational_status"] != "DISABLED"
                                         for row in sources),
            ),
            health_indicators=DashboardHealthIndicators(
                pipeline_success_rate=monitoring.metrics.pipeline_success_rate,
                validation_pass_rate=validation_metric,
                healthy_sources=monitoring.metrics.healthy_sources,
                freshness_compliance=self._unsupported(
                    "PERCENT", "Legacy table freshness metrics are not mapped to canonical pipelines"
                ),
            ),
            active_issues=monitoring.active_issues,
            pipelines_requiring_attention=PipelineHealthCollection(
                items=attention[:5], total=len(attention), truncated=len(attention) > 5
            ),
            latest_runs=RunCollection(
                items=[PipelineRunListItem.model_validate({key: value for key, value in row.items()
                                                          if key != "pipeline_run_id"}) for row in latest_runs[:5]],
                total=len(latest_runs), truncated=len(latest_runs) > 5,
            ),
            recent_activity=ActivityCollection(
                items=activities[:10], total=len(activities), truncated=len(activities) > 10
            ),
        )
