"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  Activity,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Database,
  Gauge,
  RefreshCw,
  ShieldAlert,
  TimerReset,
} from "lucide-react";

import type { MonitoringResponse } from "@/lib/api-contract";
import {
  activeIssueHref,
  activityHref,
  metricTone,
  MONITORING_WINDOWS,
  presentOverallState,
  presentMetric,
  type MonitoringWindow,
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
  OperationalStatus,
  PageHeader,
  Skeleton,
  StatusBadge,
  TechnicalDetails,
} from "@/components/ui";

type ResourceType = "all" | "pipeline" | "source";
type ResourceOption = { key: string; name: string };

const windowOptions = MONITORING_WINDOWS.map((value) => ({
  value,
  label: value === "1h" ? "Last 1 hour" : `Last ${value.replace("d", " days").replace("h", " hours")}`,
}));
const environmentOptions = [
  { value: "all", label: "All Environments" },
  { value: "production", label: "Production" },
  { value: "staging", label: "Staging" },
  { value: "development", label: "Development" },
];
const metricDefinitions = [
  { key: "pipeline_success_rate", label: "Pipeline Success Rate", icon: Gauge },
  { key: "successful_runs", label: "Successful Runs", icon: CheckCircle2 },
  { key: "failed_runs", label: "Failed Runs", icon: CircleAlert },
  { key: "average_runtime", label: "Average Runtime", icon: Clock3 },
  { key: "schedule_adherence", label: "Schedule Adherence", icon: TimerReset },
  { key: "healthy_sources", label: "Healthy Sources", icon: Database },
] as const;

function Row({ children }: { children: React.ReactNode }) {
  return <div className="grid gap-2 border-b border-zinc-100 px-4 py-3 last:border-0 md:grid-cols-[minmax(0,1.4fr)_repeat(3,minmax(0,1fr))]">{children}</div>;
}

function Cell({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="min-w-0"><p className="text-[9px] font-semibold uppercase tracking-wider text-zinc-400 md:hidden">{label}</p><div className="mt-0.5 truncate text-xs text-zinc-700 md:mt-0">{children}</div></div>;
}

export function MonitoringPage() {
  const params = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const requestedWindow = params.get("time");
  const [windowValue, setWindowValue] = useState<MonitoringWindow>(
    MONITORING_WINDOWS.includes(requestedWindow as MonitoringWindow)
      ? (requestedWindow as MonitoringWindow)
      : "24h",
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
  const request = useApiQuery<MonitoringResponse>("/api/v1/monitoring", query);

  useEffect(() => {
    if (!request.data) return;
    setPipelineOptions((current) => {
      const options = new Map(current.map((item) => [item.key, item]));
      request.data?.pipeline_health.items.forEach((item) =>
        options.set(item.pipeline_key, { key: item.pipeline_key, name: item.name }),
      );
      return [...options.values()];
    });
    setSourceOptions((current) => {
      const options = new Map(current.map((item) => [item.key, item]));
      request.data?.source_health.items.forEach((item) =>
        options.set(item.source_key, { key: item.source_key, name: item.name }),
      );
      return [...options.values()];
    });
  }, [request.data]);

  const syncUrl = (next: {
    window?: MonitoringWindow;
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
      const defaultValue = key === "time" ? "24h" : key === "environment" ? "production" : "all";
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
        label="Monitoring window"
        value={windowValue}
        options={windowOptions}
        onChange={(value) => {
          const next = value as MonitoringWindow;
          setWindowValue(next);
          syncUrl({ window: next });
        }}
      />
      <FilterSelect
        label="Environment"
        value={environment}
        options={environmentOptions}
        onChange={(value) => {
          setEnvironment(value);
          syncUrl({ environment: value });
        }}
      />
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
      {resourceType !== "all" && (
        <FilterSelect
          label="Resource"
          value={resource}
          options={resourceOptions}
          onChange={(value) => {
            setResource(value);
            syncUrl({ resource: value });
          }}
        />
      )}
      <Button onClick={request.retry}><RefreshCw className="h-3.5 w-3.5" /> Refresh</Button>
    </div>
  );

  if (request.loading && !request.data) return <MonitoringSkeleton />;
  if (request.error) {
    return (
      <div className="animate-enter">
        <Breadcrumbs items={[{ label: "Operate" }, { label: "Monitoring" }]} />
        <PageHeader title="Monitoring" description="Current operational state and active platform conditions." action={filters} />
        <ErrorState
          title={request.error.kind === "permission" ? "Permission denied" : request.error.kind === "unavailable" ? "Monitoring service unavailable" : "Monitoring couldn't be loaded"}
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
  const noEvaluableState = data.state_availability === "NO_DATA" || data.overall_state == null;
  const overallState = presentOverallState(data.state_availability, data.overall_state);
  const stateResult = noEvaluableState
    ? { status: "Neutral" as const, platformCode: "MONITORING_NO_DATA", message: overallState, recommendedAction: "Adjust the scope or allow operational observations to accumulate." }
    : data.overall_state === "CRITICAL"
      ? { status: "Error" as const, platformCode: "PLATFORM_OPERATIONAL_CRITICAL", message: "Critical operational conditions require attention.", recommendedAction: "Review the active issues and affected resources below." }
      : data.overall_state === "WARNING"
        ? { status: "Warning" as const, platformCode: "PLATFORM_OPERATIONAL_WARNING", message: "Operational warnings require review.", recommendedAction: "Review warning issues and affected resources below." }
        : { status: "Success" as const, platformCode: "PLATFORM_OPERATIONAL_HEALTHY", message: "Current evaluable resources are healthy.", recommendedAction: "Continue monitoring current activity." };

  return (
    <div className="animate-enter">
      <Breadcrumbs items={[{ label: "Operate" }, { label: "Monitoring" }]} />
      <PageHeader
        title="Monitoring"
        description="Current operational state and active platform conditions."
        eyebrow={<>Generated <span className="font-mono">{data.generated_at}</span></>}
        action={filters}
      />

      <Card title="Overall Operational State" description="Authoritative state returned by the Monitoring aggregation.">
        <div className="p-4">
          <OperationalStatus
            result={stateResult}
            statusLabel={noEvaluableState ? "Disabled" : data.overall_state === "CRITICAL" ? "Critical" : data.overall_state === "WARNING" ? "Warning" : "Healthy"}
            details={[
              { label: "State availability", value: data.state_availability },
              { label: "Overall state", value: overallState },
              { label: "Selected period", value: `${data.period.start} — ${data.period.end}` },
            ]}
          />
        </div>
      </Card>

      <section className="mt-7">
        <h2 className="mb-3 text-[15px] font-semibold text-zinc-900">Current Metrics</h2>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
          {metricDefinitions.map((definition) => {
            const metric = data.metrics[definition.key];
            const presented = presentMetric(metric);
            return <MetricCard key={definition.key} label={definition.label} value={presented.value} detail={presented.detail} icon={definition.icon} tone={metricTone(metric)} />;
          })}
        </div>
      </section>

      <section className="mt-7">
        <Card title="Active Issues" description="Backend-deduplicated current conditions; no frontend issue reconstruction.">
          {data.active_issues.items.length ? (
            <div>
              {data.active_issues.items.map((issue) => {
                const href = activeIssueHref(issue);
                return (
                  <div key={issue.issue_key} className="border-b border-zinc-100 p-4 last:border-0">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2"><StatusBadge status={issue.severity === "CRITICAL" ? "Critical" : "Warning"} /><span className="font-mono text-[10px] text-zinc-500">{issue.issue_key}</span></div>
                        <p className="mt-2 text-sm font-semibold text-zinc-900">{issue.title}</p>
                        <p className="mt-1 text-xs text-zinc-600">{issue.message}</p>
                        <p className="mt-2 font-mono text-[10px] text-zinc-500">{issue.platform_code ?? "Not available"}{issue.vendor_code ? ` · Vendor: ${issue.vendor_code}` : ""}{issue.rule_code ? ` · Rule: ${issue.rule_code}` : ""}</p>
                      </div>
                      {href && <Link href={href} className="text-xs font-medium text-indigo-700 hover:text-indigo-900">View details</Link>}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : <div className="p-4"><EmptyState title="No active issues" description="The aggregation returned no active operational issues for this scope." /></div>}
        </Card>
      </section>

      <div className="mt-7 grid gap-7 xl:grid-cols-2">
        <Card title="Pipeline Health" description="Current backend pipeline status with period metrics.">
          {data.pipeline_health.items.length ? data.pipeline_health.items.map((pipeline) => {
            const success = presentMetric(pipeline.period_success_rate);
            return <Row key={pipeline.pipeline_key}>
              <Cell label="Pipeline"><Link className="font-medium text-zinc-900 hover:text-indigo-700" href={`/pipelines/${pipeline.pipeline_key}`}>{pipeline.name}</Link></Cell>
              <Cell label="Status"><StatusBadge status={pipeline.operational_status === "FAILED" ? "Failed" : pipeline.operational_status[0] + pipeline.operational_status.slice(1).toLowerCase()} /></Cell>
              <Cell label="Success rate">{success.value}</Cell>
              <Cell label="Latest run">{pipeline.latest_run ? <Link className="font-mono text-indigo-700" href={`/pipeline-runs/${pipeline.latest_run.corvetra_run_id}`}>{pipeline.latest_run.corvetra_run_id}</Link> : "Not available"}</Cell>
            </Row>;
          }) : <div className="p-4"><EmptyState title="No pipeline health data" description="No pipelines match the selected scope." tone="neutral" /></div>}
        </Card>

        <Card title="Source Health" description="Authoritative current connectivity; Disabled remains a distinct state.">
          {data.source_health.items.length ? data.source_health.items.map((source) => <Row key={source.source_key}>
            <Cell label="Source"><Link className="font-medium text-zinc-900 hover:text-indigo-700" href={`/data-sources/${source.source_key}`}>{source.name}</Link></Cell>
            <Cell label="Status"><StatusBadge status={source.operational_status[0] + source.operational_status.slice(1).toLowerCase()} /></Cell>
            <Cell label="Type">{source.source_type}</Cell>
            <Cell label="Last observed">{source.last_observed_at ?? "Not available"}</Cell>
          </Row>) : <div className="p-4"><EmptyState title="No source health data" description="No sources match the selected scope." tone="neutral" /></div>}
        </Card>
      </div>

      <div className="mt-7 grid gap-7 xl:grid-cols-2">
        <Card title="Recent Failed Runs" description="Failed executions returned by the aggregation for this period.">
          {data.recent_failed_runs.items.length ? data.recent_failed_runs.items.map((run) => <Row key={run.corvetra_run_id}>
            <Cell label="Run"><Link className="font-mono text-indigo-700" href={`/pipeline-runs/${run.corvetra_run_id}`}>{run.corvetra_run_id}</Link></Cell>
            <Cell label="Pipeline"><Link href={`/pipelines/${run.pipeline.pipeline_key}`}>{run.pipeline.name}</Link></Cell>
            <Cell label="Stage">{run.stage ?? "Not available"}</Cell>
            <Cell label="Started">{run.started_at}</Cell>
          </Row>) : <div className="p-4"><EmptyState title="No failed runs in this period" description="Current issues may still be present outside the selected run-history window." /></div>}
        </Card>

        <Card title="Validation Conditions" description="Latest failed validation conditions and any representing alert.">
          {data.validation_conditions.items.length ? data.validation_conditions.items.map((validation) => <Row key={`${validation.check_key}:${validation.run.corvetra_run_id}`}>
            <Cell label="Check"><Link className="font-medium text-indigo-700" href={`/validation/${validation.check_key}?run=${encodeURIComponent(validation.run.corvetra_run_id)}`}>{validation.name}</Link></Cell>
            <Cell label="Result"><StatusBadge status={validation.result === "FAILED" ? "Failed" : validation.result} /></Cell>
            <Cell label="Run"><Link className="font-mono" href={`/pipeline-runs/${validation.run.corvetra_run_id}`}>{validation.run.corvetra_run_id}</Link></Cell>
            <Cell label="Alert">{validation.represented_by_alert_key ? <Link href={`/alerts/${validation.represented_by_alert_key}`}>{validation.represented_by_alert_key}</Link> : "Not represented"}</Cell>
          </Row>) : <div className="p-4"><EmptyState title="No validation conditions" description="No failed validation conditions match this scope." /></div>}
        </Card>
      </div>

      <section className="mt-7">
        <Card title="Recent Activity" description="Persisted run and technical-event activity, using exact API timestamps.">
          {data.recent_activity.items.length ? data.recent_activity.items.map((activity) => {
            const href = activityHref(activity);
            return <Row key={`${activity.kind}:${activity.event_key ?? activity.run?.corvetra_run_id}:${activity.occurred_at}`}>
              <Cell label="Time"><span className="font-mono">{activity.occurred_at}</span></Cell>
              <Cell label="Resource">{activity.pipeline?.name ?? activity.source?.name ?? "Platform"}</Cell>
              <Cell label="Message">{activity.message}</Cell>
              <Cell label="Evidence">{href ? <Link className="text-indigo-700" href={href}>{activity.kind === "TECHNICAL_EVENT" ? "View logs" : "View run"}</Link> : "Not available"}</Cell>
            </Row>;
          }) : <div className="p-4"><EmptyState title="No recent activity" description="No persisted activity falls inside the selected period." tone="neutral" /></div>}
        </Card>
      </section>

      <Card className="mt-7" title="Snapshot Context" description="Aggregation scope and exact server-provided timestamps.">
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

export function MonitoringSkeleton() {
  return <div className="space-y-7"><Skeleton className="h-20" /><Skeleton className="h-52" /><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"><Skeleton className="h-28" /><Skeleton className="h-28" /><Skeleton className="h-28" /></div><Skeleton className="h-72" /></div>;
}
