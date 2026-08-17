"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  Activity,
  Clock3,
  Database,
  FileCheck2,
  Gauge,
  HeartPulse,
  RefreshCw,
  TimerReset,
} from "lucide-react";

import { TrendChart } from "@/components/trend-chart";
import type { AggregationMetric, HealthMetricsResponse } from "@/lib/api-contract";
import {
  HEALTH_WINDOWS,
  metricTone,
  presentMetric,
  reviewResourceHref,
  sparseTrend,
  type HealthWindow,
} from "@/lib/aggregation-adapters";
import { useApiQuery } from "@/lib/use-api-query";
import {
  Breadcrumbs,
  Button,
  Card,
  EmptyState,
  ErrorState,
  FilterSelect,
  MetricCard,
  PageHeader,
  Skeleton,
  StatusBadge,
  TechnicalDetails,
} from "@/components/ui";

type ResourceType = "all" | "pipeline" | "source";
type ResourceOption = { key: string; name: string };

const windowOptions = HEALTH_WINDOWS.map((value) => ({
  value,
  label: `Last ${value.replace("d", " days").replace("h", " hours")}`,
}));
const environmentOptions = [
  { value: "all", label: "All Environments" },
  { value: "production", label: "Production" },
  { value: "staging", label: "Staging" },
  { value: "development", label: "Development" },
];
const metricDefinitions = [
  { key: "pipeline_success_rate", label: "Pipeline Success Rate", icon: Gauge },
  { key: "average_runtime", label: "Average Runtime", icon: Clock3 },
  { key: "validation_pass_rate", label: "Validation Pass Rate", icon: FileCheck2 },
  { key: "source_availability", label: "Source Availability", icon: Database },
  { key: "freshness_compliance", label: "Freshness Compliance", icon: Activity },
  { key: "schedule_adherence", label: "Schedule Adherence", icon: TimerReset },
] as const;

function Row({ children }: { children: React.ReactNode }) {
  return <div className="grid gap-2 border-b border-zinc-100 px-4 py-3 last:border-0 md:grid-cols-[minmax(0,1.4fr)_repeat(4,minmax(0,1fr))]">{children}</div>;
}

function Cell({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="min-w-0"><p className="text-[9px] font-semibold uppercase tracking-wider text-zinc-400 md:hidden">{label}</p><div className="mt-0.5 truncate text-xs text-zinc-700 md:mt-0">{children}</div></div>;
}

function MetricTrend({ title, metric, color }: { title: string; metric: AggregationMetric; color: string }) {
  const presented = presentMetric(metric);
  const trend = sparseTrend(metric);
  return (
    <Card title={title} description={`Current: ${presented.value} · Previous: ${presented.previous} · Delta: ${presented.delta}`}>
      <div className="p-4">
        {metric.availability !== "AVAILABLE" ? (
          <EmptyState title={presented.value} description={presented.detail} icon={<HeartPulse className="h-4 w-4" />} tone="neutral" />
        ) : trend.points.length ? (
          <>
            <TrendChart labels={trend.labels} series={[{ label: title, values: trend.values, color }]} valueSuffix={metric.unit === "PERCENT" ? "%" : metric.unit === "SECONDS" ? "s" : ""} />
            <p className="mt-3 text-[10px] text-zinc-500">{trend.points.length} persisted bucket{trend.points.length === 1 ? "" : "s"}; empty buckets are intentionally omitted.</p>
          </>
        ) : (
          <EmptyState title="No persisted trend points" description="The metric value is available, but the backend returned no populated trend buckets." icon={<HeartPulse className="h-4 w-4" />} tone="neutral" />
        )}
      </div>
    </Card>
  );
}

export function HealthMetricsPage() {
  const params = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const requestedWindow = params.get("time");
  const [windowValue, setWindowValue] = useState<HealthWindow>(
    HEALTH_WINDOWS.includes(requestedWindow as HealthWindow) ? (requestedWindow as HealthWindow) : "7d",
  );
  const [environment, setEnvironment] = useState(params.get("environment") ?? "production");
  const [resourceType, setResourceType] = useState<ResourceType>(
    params.get("resourceType") === "pipeline" || params.get("resourceType") === "source"
      ? (params.get("resourceType") as ResourceType)
      : "all",
  );
  const [resource, setResource] = useState(params.get("resource") ?? "all");
  const [pipelineOptions, setPipelineOptions] = useState<ResourceOption[]>([]);
  const [sourceOptions, setSourceOptions] = useState<ResourceOption[]>([]);

  const query = {
    window: windowValue,
    environment: environment === "all" ? undefined : environment,
    pipeline: resourceType === "pipeline" && resource !== "all" ? resource : undefined,
    source: resourceType === "source" && resource !== "all" ? resource : undefined,
  };
  const request = useApiQuery<HealthMetricsResponse>("/api/v1/health-metrics", query);

  useEffect(() => {
    if (!request.data) return;
    setPipelineOptions((current) => {
      const options = new Map(current.map((item) => [item.key, item]));
      request.data?.pipeline_reliability.forEach((item) =>
        options.set(item.pipeline.pipeline_key, { key: item.pipeline.pipeline_key, name: item.pipeline.name }),
      );
      return [...options.values()];
    });
    setSourceOptions((current) => {
      const options = new Map(current.map((item) => [item.key, item]));
      request.data?.current_source_connectivity.forEach((item) =>
        options.set(item.source_key, { key: item.source_key, name: item.name }),
      );
      return [...options.values()];
    });
  }, [request.data]);

  const syncUrl = (next: {
    window?: HealthWindow;
    environment?: string;
    resourceType?: ResourceType;
    resource?: string;
  }) => {
    const nextParams = new URLSearchParams(params.toString());
    const values = {
      time: next.window ?? windowValue,
      environment: next.environment ?? environment,
      resourceType: next.resourceType ?? resourceType,
      resource: next.resource ?? resource,
    };
    for (const [key, value] of Object.entries(values)) {
      const defaultValue = key === "time" ? "7d" : key === "environment" ? "production" : "all";
      if (value === defaultValue) nextParams.delete(key);
      else nextParams.set(key, value);
    }
    router.replace(nextParams.size ? `${pathname}?${nextParams}` : pathname);
  };

  const availableResources = resourceType === "pipeline" ? pipelineOptions : resourceType === "source" ? sourceOptions : [];
  const resourceOptions = useMemo(() => {
    const options = [...availableResources];
    if (resource !== "all" && !options.some((item) => item.key === resource)) {
      options.push({ key: resource, name: resource });
    }
    return [{ value: "all", label: "All Resources" }, ...options.map((item) => ({ value: item.key, label: item.name }))];
  }, [availableResources, resource]);

  const filters = (
    <div className="flex flex-wrap items-end gap-2">
      <FilterSelect
        label="Health metrics window"
        value={windowValue}
        options={windowOptions}
        onChange={(value) => {
          const next = value as HealthWindow;
          setWindowValue(next);
          syncUrl({ window: next });
        }}
      />
      <FilterSelect label="Environment" value={environment} options={environmentOptions} onChange={(value) => {
        setEnvironment(value);
        syncUrl({ environment: value });
      }} />
      <FilterSelect
        label="Resource type"
        value={resourceType}
        options={[
          { value: "all", label: "All Resources" },
          { value: "pipeline", label: "Pipelines" },
          { value: "source", label: "Data Sources" },
        ]}
        onChange={(value) => {
          const next = value as ResourceType;
          setResourceType(next);
          setResource("all");
          syncUrl({ resourceType: next, resource: "all" });
        }}
      />
      {resourceType !== "all" && <FilterSelect label="Resource" value={resource} options={resourceOptions} onChange={(value) => {
        setResource(value);
        syncUrl({ resource: value });
      }} />}
      <Button onClick={request.retry}><RefreshCw className="h-3.5 w-3.5" /> Refresh</Button>
    </div>
  );

  if (request.loading && !request.data) return <HealthMetricsPageSkeleton />;
  if (request.error) {
    return (
      <div className="animate-enter">
        <Breadcrumbs items={[{ label: "Platform" }, { label: "Health Metrics" }]} />
        <PageHeader title="Health Metrics" description="Persisted reliability, performance, quality, and current connectivity signals." action={filters} />
        <ErrorState
          title={request.error.kind === "permission" ? "Permission denied" : request.error.kind === "unavailable" ? "Health metrics service unavailable" : "Health Metrics couldn't be loaded"}
          description={request.error.message}
          actionLabel={request.error.retryable ? "Try Again" : undefined}
          onRetry={request.error.retryable ? request.retry : undefined}
          technicalDetails={[{ label: "Platform Code", value: request.error.code }]}
        />
      </div>
    );
  }
  if (!request.data) return null;

  const data = request.data;
  const supportedAvailable = [
    data.metrics.pipeline_success_rate,
    data.metrics.average_runtime,
    data.metrics.validation_pass_rate,
  ].filter((metric) => metric.availability === "AVAILABLE").length;

  return (
    <div className="animate-enter">
      <Breadcrumbs items={[{ label: "Platform" }, { label: "Health Metrics" }]} />
      <PageHeader
        title="Health Metrics"
        description="Persisted reliability, performance, quality, and current connectivity signals."
        eyebrow={<>Generated <span className="font-mono">{data.generated_at}</span></>}
        action={filters}
      />

      <Card title="Historical Metric Coverage" description="Availability is reported independently for every metric.">
        <div className="p-4">
          <TechnicalDetails items={[
            { label: "Available supported metrics", value: `${supportedAvailable} / 3` },
            { label: "Selected period", value: `${data.period.start} — ${data.period.end}` },
            { label: "Comparison period", value: `${data.comparison_period.start} — ${data.comparison_period.end}` },
            { label: "Scope", value: data.scope.pipeline ?? data.scope.source ?? data.scope.environment ?? "All" },
          ]} />
        </div>
      </Card>

      <section className="mt-7">
        <h2 className="mb-3 text-[15px] font-semibold text-zinc-900">Core Health Metrics</h2>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
          {metricDefinitions.map((definition) => {
            const metric = data.metrics[definition.key];
            const presented = presentMetric(metric);
            const comparison = presented.previous === "Not available" || presented.previous === "Insufficient data"
              ? `${presented.detail} · Previous: ${presented.previous}`
              : `Previous: ${presented.previous} · Delta: ${presented.delta}`;
            return <MetricCard key={definition.key} label={definition.label} value={presented.value} detail={comparison} icon={definition.icon} tone={metricTone(metric)} />;
          })}
        </div>
      </section>

      <div className="mt-7 grid gap-7 xl:grid-cols-3">
        <MetricTrend title="Pipeline Success Rate" metric={data.metrics.pipeline_success_rate} color="#4f46e5" />
        <MetricTrend title="Average Runtime" metric={data.metrics.average_runtime} color="#d97706" />
        <MetricTrend title="Validation Pass Rate" metric={data.metrics.validation_pass_rate} color="#059669" />
      </div>

      <section className="mt-7">
        <Card title="Pipeline Reliability" description="Backend historical outcomes by canonical pipeline.">
          {data.pipeline_reliability.length ? data.pipeline_reliability.map((item) => {
            const success = presentMetric(item.success_rate);
            const runtime = presentMetric(item.average_runtime);
            return <Row key={item.pipeline.pipeline_key}>
              <Cell label="Pipeline"><Link className="font-medium text-indigo-700" href={`/pipelines/${item.pipeline.pipeline_key}`}>{item.pipeline.name}</Link></Cell>
              <Cell label="Status"><StatusBadge status={item.pipeline.operational_status === "FAILED" ? "Failed" : item.pipeline.operational_status[0] + item.pipeline.operational_status.slice(1).toLowerCase()} /></Cell>
              <Cell label="Success rate">{success.value}</Cell>
              <Cell label="Average runtime">{runtime.value}</Cell>
              <Cell label="Runs">{item.successful_runs} successful · {item.failed_runs} failed · {item.running_runs} running</Cell>
            </Row>;
          }) : <div className="p-4"><EmptyState title="No pipeline history" description="No pipeline executions match this period and scope." icon={<Gauge className="h-4 w-4" />} tone="neutral" /></div>}
        </Card>
      </section>

      <section className="mt-7">
        <Card title="Validation Quality" description="Not-evaluated checks remain separate from the pass-rate denominator.">
          {data.validation_quality.length ? data.validation_quality.map((item) => {
            const rate = presentMetric(item.pass_rate);
            return <Row key={item.check_key}>
              <Cell label="Check"><Link className="font-medium text-indigo-700" href={`/validation?check=${encodeURIComponent(item.check_key)}`}>{item.name}</Link></Cell>
              <Cell label="Pipeline"><Link href={`/pipelines/${item.pipeline.pipeline_key}`}>{item.pipeline.name}</Link></Cell>
              <Cell label="Pass rate">{rate.value}</Cell>
              <Cell label="Results">{item.passed} passed · {item.failed} failed · {item.not_evaluated} not evaluated</Cell>
              <Cell label="Failures">{item.blocking_failed} blocking · {item.warning_failed} warning</Cell>
            </Row>;
          }) : <div className="p-4"><EmptyState title="No validation history" description="No validation executions match this period and scope." icon={<FileCheck2 className="h-4 w-4" />} tone="neutral" /></div>}
        </Card>
      </section>

      <section className="mt-7">
        <Card title="Current Source Connectivity" description="CURRENT_SNAPSHOT — current state only, not historical availability or uptime.">
          {data.current_source_connectivity.length ? data.current_source_connectivity.map((source) => <Row key={source.source_key}>
            <Cell label="Source"><Link className="font-medium text-indigo-700" href={`/data-sources/${source.source_key}`}>{source.name}</Link></Cell>
            <Cell label="Current status"><StatusBadge status={source.operational_status[0] + source.operational_status.slice(1).toLowerCase()} /></Cell>
            <Cell label="Snapshot type">CURRENT_SNAPSHOT</Cell>
            <Cell label="Type">{source.source_type}</Cell>
            <Cell label="Observed">{source.last_observed_at ?? "Not available"}</Cell>
          </Row>) : <div className="p-4"><EmptyState title="No current source snapshot" description="No sources match this scope." icon={<Database className="h-4 w-4" />} tone="neutral" /></div>}
        </Card>
      </section>

      <section className="mt-7">
        <Card title="Resources Requiring Review" description="Backend-selected resources contributing to current or historical degradation.">
          {data.resources_requiring_review.length ? data.resources_requiring_review.map((resourceItem) => {
            const href = reviewResourceHref(resourceItem);
            return <Row key={`${resourceItem.resource_type}:${resourceItem.resource_key}`}>
              <Cell label="Resource">{href ? <Link className="font-medium text-indigo-700" href={href}>{resourceItem.name}</Link> : resourceItem.name}</Cell>
              <Cell label="Type">{resourceItem.resource_type}</Cell>
              <Cell label="Signal">{resourceItem.signal}</Cell>
              <Cell label="Severity"><StatusBadge status={resourceItem.severity === "CRITICAL" ? "Critical" : "Warning"} /></Cell>
              <Cell label="Key"><span className="font-mono">{resourceItem.resource_key}</span></Cell>
            </Row>;
          }) : <div className="p-4"><EmptyState title="No resources require review" description="The aggregation returned no review resources for this scope." /></div>}
        </Card>
      </section>

      <Card className="mt-7" title="Snapshot Context" description="Exact server-provided aggregation timestamps and scope.">
        <div className="p-4">
          <TechnicalDetails items={[
            { label: "Generated at", value: data.generated_at },
            { label: "Period start", value: data.period.start },
            { label: "Period end", value: data.period.end },
            { label: "Environment", value: data.scope.environment ?? "All" },
            { label: "Pipeline", value: data.scope.pipeline ?? "All" },
            { label: "Source", value: data.scope.source ?? "All" },
          ]} />
        </div>
      </Card>
    </div>
  );
}

export function HealthMetricsPageSkeleton() {
  return <div className="space-y-7"><Skeleton className="h-20" /><Skeleton className="h-36" /><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"><Skeleton className="h-28" /><Skeleton className="h-28" /><Skeleton className="h-28" /></div><Skeleton className="h-72" /></div>;
}
