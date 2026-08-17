import type {
  ActiveIssue,
  ActivityItem,
  AggregationMetric,
  MetricAvailability,
  MetricPoint,
  ReviewResource,
  StateAvailability,
  OperationalState,
} from "@/lib/api-contract";

export const MONITORING_WINDOWS = ["1h", "6h", "24h", "7d", "30d"] as const;
export const HEALTH_WINDOWS = ["24h", "7d", "30d", "90d"] as const;

export type MonitoringWindow = (typeof MONITORING_WINDOWS)[number];
export type HealthWindow = (typeof HEALTH_WINDOWS)[number];

export interface PresentedMetric {
  availability: MetricAvailability;
  value: string;
  detail: string;
  previous: string;
  delta: string;
}

export function presentOverallState(
  availability: StateAvailability,
  state: OperationalState | null,
): OperationalState | "Not available / No evaluable data" {
  return availability === "NO_DATA" || state == null
    ? "Not available / No evaluable data"
    : state;
}

function formatAvailableValue(metric: AggregationMetric, value: number): string {
  if (metric.unit === "PERCENT") return `${value}%`;
  if (metric.unit === "SECONDS") return `${value} s`;
  return String(value);
}

export function presentMetric(metric: AggregationMetric): PresentedMetric {
  if (metric.availability === "INSUFFICIENT_DATA") {
    return {
      availability: metric.availability,
      value: "Insufficient data",
      detail: metric.sample_count
        ? `${metric.sample_count} sample${metric.sample_count === 1 ? "" : "s"}`
        : metric.reason ?? "No qualifying samples",
      previous: "Insufficient data",
      delta: "Not available",
    };
  }
  if (metric.availability === "UNSUPPORTED") {
    return {
      availability: metric.availability,
      value: "Not available",
      detail: metric.reason ?? "Unsupported by the aggregation API",
      previous: "Not available",
      delta: "Not available",
    };
  }

  const value = metric.value == null ? "Not available" : formatAvailableValue(metric, metric.value);
  const previous =
    metric.previous.availability === "AVAILABLE" && metric.previous.value != null
      ? formatAvailableValue(metric, metric.previous.value)
      : metric.previous.availability === "INSUFFICIENT_DATA"
        ? "Insufficient data"
        : "Not available";

  return {
    availability: metric.availability,
    value,
    detail: `${metric.sample_count} sample${metric.sample_count === 1 ? "" : "s"}`,
    previous,
    delta: metric.delta == null ? "Not available" : formatAvailableValue(metric, metric.delta),
  };
}

export function sparseTrend(metric: AggregationMetric): {
  labels: string[];
  values: number[];
  points: MetricPoint[];
} {
  return {
    labels: metric.points.map((point) => point.start),
    values: metric.points.map((point) => point.value),
    points: [...metric.points],
  };
}

export function activeIssueHref(issue: ActiveIssue): string | null {
  if (issue.alert_key) return `/alerts/${issue.alert_key}`;
  if (issue.origin === "SOURCE" && issue.source) return `/data-sources/${issue.source.source_key}`;
  if (issue.validation && issue.run) {
    return `/validation/${issue.validation.check_key}?run=${encodeURIComponent(issue.run.corvetra_run_id)}`;
  }
  if (issue.run) return `/pipeline-runs/${issue.run.corvetra_run_id}`;
  if (issue.pipeline) return `/pipelines/${issue.pipeline.pipeline_key}`;
  if (issue.source) return `/data-sources/${issue.source.source_key}`;
  return null;
}

export function activityHref(activity: ActivityItem): string | null {
  if (activity.kind === "TECHNICAL_EVENT") {
    const parameters = new URLSearchParams();
    if (activity.run) parameters.set("run", activity.run.corvetra_run_id);
    if (activity.pipeline) parameters.set("pipeline", activity.pipeline.pipeline_key);
    if (activity.source) parameters.set("source", activity.source.source_key);
    const query = parameters.toString();
    return query ? `/logs?${query}` : "/logs";
  }
  if (activity.run) return `/pipeline-runs/${activity.run.corvetra_run_id}`;
  return null;
}

export function reviewResourceHref(resource: ReviewResource): string | null {
  if (resource.resource_type === "PIPELINE" && resource.pipeline_key) {
    return `/pipelines/${resource.pipeline_key}`;
  }
  if (resource.resource_type === "SOURCE" && resource.source_key) {
    return `/data-sources/${resource.source_key}`;
  }
  if (resource.resource_type === "VALIDATION" && resource.check_key) {
    return `/validation?check=${encodeURIComponent(resource.check_key)}`;
  }
  return null;
}

export function metricTone(metric: AggregationMetric): "neutral" | "positive" | "warning" {
  // Availability describes whether a value can be evaluated, not whether that
  // value is operationally healthy. The API does not return a metric-health
  // classification, so the frontend must not infer one.
  void metric;
  return "neutral";
}
