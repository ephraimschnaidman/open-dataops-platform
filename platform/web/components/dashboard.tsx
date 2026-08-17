"use client";

import Link from "next/link";
import {
  Activity,
  CircleAlert,
  Database,
  FileCheck2,
  GitBranch,
  Gauge,
  Network,
  RefreshCw,
} from "lucide-react";

import type { DashboardResponse } from "@/lib/api-contract";
import {
  activeIssueHref,
  activityHref,
  metricTone,
  presentMetric,
  presentOverallState,
} from "@/lib/aggregation-adapters";
import { latestRunHref, presentDashboardSummary } from "@/lib/dashboard-adapters";
import { environmentApiKey, useEnvironmentContext } from "@/lib/environment-context";
import { useApiQuery } from "@/lib/use-api-query";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  MetricCard,
  OperationalStatus,
  PageHeader,
  Section,
  Skeleton,
  StatusBadge,
  TechnicalDetails,
} from "@/components/ui";

const summaryIcons = [GitBranch, Activity, CircleAlert, CircleAlert, Database];
const indicatorDefinitions = [
  { key: "pipeline_success_rate", label: "Pipeline Success Rate", icon: Gauge },
  { key: "validation_pass_rate", label: "Validation Pass Rate", icon: FileCheck2 },
  { key: "healthy_sources", label: "Healthy Sources", icon: Database },
  { key: "freshness_compliance", label: "Freshness Compliance", icon: Activity },
] as const;

function Row({ children, columns = 4 }: { children: React.ReactNode; columns?: 4 | 5 }) {
  const layout = columns === 5
    ? "md:grid-cols-[minmax(0,1.3fr)_repeat(4,minmax(0,1fr))]"
    : "md:grid-cols-[minmax(0,1.4fr)_repeat(3,minmax(0,1fr))]";
  return <div className={`grid gap-2 border-b border-zinc-100 px-4 py-3 last:border-0 ${layout}`}>{children}</div>;
}

function Cell({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="text-[9px] font-semibold uppercase tracking-wider text-zinc-400 md:hidden">{label}</p>
      <div className="mt-0.5 truncate text-xs text-zinc-700 md:mt-0">{children}</div>
    </div>
  );
}

function statusLabel(status: string): string {
  return status === "FAILED"
    ? "Failed"
    : status === "SUCCESS"
      ? "Success"
      : status[0] + status.slice(1).toLowerCase();
}

export function Dashboard() {
  const { currentEnvironment } = useEnvironmentContext();
  const environment = environmentApiKey(currentEnvironment);
  const request = useApiQuery<DashboardResponse>("/api/v1/dashboard", { environment });

  if (request.loading && !request.data) return <DashboardSkeleton />;
  if (request.error) {
    return (
      <div className="animate-enter">
        <PageHeader
          title="Dashboard"
          description="Current platform state, operational attention, and canonical activity."
          eyebrow={<><Network className="h-3 w-3" /> {currentEnvironment} workspace</>}
        />
        <ErrorState
          title={request.error.kind === "permission" ? "Permission denied" : request.error.kind === "unavailable" ? "Dashboard service unavailable" : "Dashboard couldn't be loaded"}
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
  const overallState = presentOverallState(data.state_availability, data.overall_state);
  const noEvaluableState = data.state_availability === "NO_DATA" || data.overall_state == null;
  const overallResult = noEvaluableState
    ? {
        status: "Neutral" as const,
        platformCode: "DASHBOARD_NO_DATA",
        message: overallState,
        recommendedAction: "Select another environment or allow operational observations to accumulate.",
      }
    : data.overall_state === "CRITICAL"
      ? {
          status: "Error" as const,
          platformCode: "PLATFORM_OPERATIONAL_CRITICAL",
          message: "Critical operational conditions require attention.",
          recommendedAction: "Review the active issues and affected resources below.",
        }
      : data.overall_state === "WARNING"
        ? {
            status: "Warning" as const,
            platformCode: "PLATFORM_OPERATIONAL_WARNING",
            message: "Operational warnings require review.",
            recommendedAction: "Review the active issues and affected resources below.",
          }
        : {
            status: "Success" as const,
            platformCode: "PLATFORM_OPERATIONAL_HEALTHY",
            message: "Current evaluable resources are healthy.",
            recommendedAction: "Continue monitoring current activity.",
          };

  const summary = presentDashboardSummary(data.summary);

  return (
    <div className="animate-enter">
      <PageHeader
        title="Dashboard"
        description="Current platform state, operational attention, and canonical activity."
        eyebrow={<><Network className="h-3 w-3" /> {currentEnvironment} workspace · Generated <span className="font-mono">{data.generated_at}</span></>}
        action={<Button onClick={request.retry}><RefreshCw className="h-3.5 w-3.5" /> Refresh</Button>}
      />

      <Card title="Overall Operational State" description="Authoritative Dashboard aggregation state.">
        <div className="p-4">
          <OperationalStatus
            result={overallResult}
            statusLabel={noEvaluableState ? "Disabled" : data.overall_state === "CRITICAL" ? "Critical" : data.overall_state === "WARNING" ? "Warning" : "Healthy"}
            details={[
              { label: "State availability", value: data.state_availability },
              { label: "Overall state", value: overallState },
              { label: "Dashboard period", value: `${data.period.start} — ${data.period.end}` },
            ]}
          />
        </div>
      </Card>

      <Section title="Platform Summary" description="Counts returned by the Dashboard aggregation." className="mt-7">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {summary.map((item, index) => (
            <MetricCard key={item.label} {...item} icon={summaryIcons[index]} tone={item.label === "Active Alerts" && data.summary.active_alerts.total > 0 ? "warning" : "neutral"} />
          ))}
        </div>
      </Section>

      <Section title="Health Indicators" description="Availability is evaluated independently for each backend metric." className="mt-7">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {indicatorDefinitions.map((definition) => {
            const metric = data.health_indicators[definition.key];
            const presented = presentMetric(metric);
            return <MetricCard key={definition.key} label={definition.label} value={presented.value} detail={presented.detail} icon={definition.icon} tone={metricTone(metric)} />;
          })}
        </div>
      </Section>

      <Section title="Active Issues" description="Backend-deduplicated issue projection; identities and relationships are preserved." className="mt-7" action={<Link className="text-xs font-medium text-indigo-700" href="/alerts">View alerts</Link>}>
        <Card>
          {data.active_issues.items.length ? data.active_issues.items.map((issue) => {
            const href = activeIssueHref(issue);
            return (
              <div key={issue.issue_key} className="border-b border-zinc-100 p-4 last:border-0">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={issue.severity === "CRITICAL" ? "Critical" : "Warning"} />
                      {issue.alert_status && <StatusBadge status={issue.alert_status} />}
                      <span className="font-mono text-[10px] text-zinc-500">{issue.issue_key}</span>
                    </div>
                    <p className="mt-2 text-sm font-semibold text-zinc-900">{issue.title}</p>
                    <p className="mt-1 text-xs text-zinc-600">{issue.message}</p>
                    <p className="mt-2 font-mono text-[10px] text-zinc-500">
                      {issue.platform_code ?? "Not available"}
                      {issue.vendor_code ? ` · Vendor: ${issue.vendor_code}` : ""}
                      {issue.rule_code ? ` · Rule: ${issue.rule_code}` : ""}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-zinc-400">{issue.observed_at ?? "Timestamp not available"}</p>
                  </div>
                  {href && <Link href={href} className="text-xs font-medium text-indigo-700 hover:text-indigo-900">View details</Link>}
                </div>
              </div>
            );
          }) : <div className="p-4"><EmptyState title="No active issues" description="The Dashboard aggregation returned no active issues for this environment." /></div>}
        </Card>
      </Section>

      <Section title="Pipelines Requiring Attention" description="Current status is supplied by the backend and is not recalculated from history." className="mt-7">
        <Card>
          {data.pipelines_requiring_attention.items.length ? data.pipelines_requiring_attention.items.map((pipeline) => {
            const success = presentMetric(pipeline.period_success_rate);
            return (
              <Row key={pipeline.pipeline_key}>
                <Cell label="Pipeline"><Link className="font-medium text-indigo-700" href={`/pipelines/${pipeline.pipeline_key}`}>{pipeline.name}</Link></Cell>
                <Cell label="Status"><StatusBadge status={statusLabel(pipeline.operational_status)} /></Cell>
                <Cell label="Period success rate">{success.value}</Cell>
                <Cell label="Latest run">{pipeline.latest_run ? <Link className="font-mono text-indigo-700" href={`/pipeline-runs/${pipeline.latest_run.corvetra_run_id}`}>{pipeline.latest_run.corvetra_run_id}</Link> : "Not available"}</Cell>
              </Row>
            );
          }) : <div className="p-4"><EmptyState title="No pipelines require attention" description="No pipeline attention rows were returned for this environment." /></div>}
        </Card>
      </Section>

      <Section title="Latest Runs" description="Latest canonical runs are distinct from the current 24-hour metric period." className="mt-7" action={<Link className="text-xs font-medium text-indigo-700" href="/pipeline-runs">View all runs</Link>}>
        <Card>
          {data.latest_runs.items.length ? data.latest_runs.items.map((run) => (
            <Row key={run.corvetra_run_id} columns={5}>
              <Cell label="Run"><Link className="font-mono font-medium text-indigo-700" href={latestRunHref(run)}>{run.corvetra_run_id}</Link></Cell>
              <Cell label="Pipeline / Source">
                <Link href={`/pipelines/${run.pipeline.pipeline_key}`}>{run.pipeline.name}</Link>
                <span className="mt-1 block text-[10px] text-zinc-500">
                  <Link href={`/data-sources/${run.source.source_key}`}>{run.source.name}</Link> · {run.environment.name}
                </span>
              </Cell>
              <Cell label="Status / Stage"><span className="inline-flex items-center gap-2"><StatusBadge status={statusLabel(run.status)} /> {run.stage ?? "Not available"}</span></Cell>
              <Cell label="Timestamps">
                <span className="font-mono">{run.started_at}</span>
                <span className="mt-1 block font-mono text-[10px] text-zinc-500">Completed: {run.completed_at ?? "Not available"}</span>
              </Cell>
              <Cell label="Duration / Codes"><span>{run.duration_seconds == null ? "Not available" : `${run.duration_seconds} s`}</span><span className="mt-1 block font-mono text-[10px]">{run.platform_code ?? "Not available"}{run.vendor_code ? ` · Vendor: ${run.vendor_code}` : ""}{run.rule_code ? ` · Rule: ${run.rule_code}` : ""}</span></Cell>
            </Row>
          )) : <div className="p-4"><EmptyState title="No latest runs" description="No canonical runs were returned for this environment." icon={<GitBranch className="h-4 w-4" />} tone="neutral" /></div>}
        </Card>
      </Section>

      <Section title="Recent Activity" description="Persisted run and technical-event activity with exact backend timestamps." className="mt-7">
        <Card>
          {data.recent_activity.items.length ? data.recent_activity.items.map((activity) => {
            const href = activityHref(activity);
            return (
              <Row key={`${activity.kind}:${activity.event_key ?? activity.run?.corvetra_run_id}:${activity.occurred_at}`}>
                <Cell label="Timestamp"><span className="font-mono">{activity.occurred_at}</span></Cell>
                <Cell label="Resource">{activity.pipeline?.name ?? activity.source?.name ?? "Platform"}</Cell>
                <Cell label="Activity">{activity.message}</Cell>
                <Cell label="Details">{href ? <Link className="text-indigo-700" href={href}>{activity.kind === "TECHNICAL_EVENT" ? "View logs" : "View run"}</Link> : "Not available"}</Cell>
              </Row>
            );
          }) : <div className="p-4"><EmptyState title="No recent activity" description="No persisted activity was returned for this Dashboard period." icon={<Activity className="h-4 w-4" />} tone="neutral" /></div>}
        </Card>
      </Section>

      <Card className="mt-7" title="Snapshot Context" description="Exact server-provided Dashboard timestamps and environment.">
        <div className="p-4">
          <TechnicalDetails items={[
            { label: "Generated at", value: data.generated_at },
            { label: "Period start", value: data.period.start },
            { label: "Period end", value: data.period.end },
            { label: "Environment", value: data.environment ?? "All" },
          ]} />
        </div>
      </Card>
    </div>
  );
}

export function DashboardSkeleton() {
  return <div className="space-y-7"><Skeleton className="h-20" /><Skeleton className="h-52" /><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5"><Skeleton className="h-28" /><Skeleton className="h-28" /><Skeleton className="h-28" /><Skeleton className="h-28" /><Skeleton className="h-28" /></div><Skeleton className="h-72" /></div>;
}
