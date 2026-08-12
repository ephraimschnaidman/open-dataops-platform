"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
    Activity,
    ArrowRight,
    ChevronRight,
    CircleAlert,
    Database,
    GitBranch,
    MoreHorizontal,
    Network,
    ShieldCheck,
    X,
} from "lucide-react";
import {
    activities as allActivities,
    healthItems as productionHealthItems,
    issues as productionIssues,
    metrics,
    pipelineRuns as allPipelineRuns,
    type Issue,
} from "@/lib/dashboard-data";
import {
    EmptyState,
    ErrorState,
    MetricCard,
    Section,
    Skeleton,
    StatusBadge,
} from "@/components/ui";
import { pipelines } from "@/lib/pipelines-data";
import { useEnvironmentContext } from "@/lib/environment-context";

function MetricCards() {
    const { currentEnvironment } = useEnvironmentContext();
    const icons = [GitBranch, ShieldCheck, CircleAlert, Activity];
    const scopedPipelines = pipelines.filter(
        (pipeline) => pipeline.environment === currentEnvironment,
    );
    const scopedRuns = allPipelineRuns.filter((run) =>
        scopedPipelines.some((pipeline) => pipeline.name === run.pipeline),
    );
    const scopedMetrics =
        currentEnvironment === "Production"
            ? metrics
            : [
                  {
                      label: "Pipelines",
                      value: String(scopedPipelines.length),
                      detail: `Configured in ${currentEnvironment}`,
                      tone: "neutral" as const,
                  },
                  {
                      label: "Successful runs",
                      value: String(
                          scopedRuns.filter((run) => run.status === "Success")
                              .length,
                      ),
                      detail: "Recent demo activity",
                      tone: "positive" as const,
                  },
                  {
                      label: "Failed runs",
                      value: String(
                          scopedRuns.filter((run) => run.status === "Failed")
                              .length,
                      ),
                      detail: "Recent demo activity",
                      tone: "warning" as const,
                  },
                  {
                      label: "Active alerts",
                      value: "0",
                      detail: `No active alerts in ${currentEnvironment}`,
                      tone: "neutral" as const,
                  },
              ];
    return (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {scopedMetrics.map((metric, index) => (
                <MetricCard
                    key={metric.label}
                    {...metric}
                    icon={icons[index]}
                />
            ))}
        </div>
    );
}

function Issues({ onSelect }: { onSelect: (issue: Issue) => void }) {
    const { currentEnvironment } = useEnvironmentContext();
    const issues = currentEnvironment === "Production" ? productionIssues : [];
    if (!issues.length) return <EmptyState />;
    return (
        <div className="overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-card">
            <div className="hidden grid-cols-[1.3fr_1.5fr_100px_100px_20px] gap-4 border-b border-zinc-200 bg-zinc-50/70 px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-400 md:grid">
                <span>Resource</span>
                <span>Issue</span>
                <span>Severity</span>
                <span>Detected</span>
                <span />
            </div>
            {issues.map((issue) => (
                <button
                    key={issue.id}
                    onClick={() => onSelect(issue)}
                    className="group grid w-full grid-cols-[1fr_auto] items-center gap-3 border-b border-zinc-100 px-4 py-3 text-left transition last:border-0 hover:bg-zinc-50 md:grid-cols-[1.3fr_1.5fr_100px_100px_20px] md:gap-4"
                >
                    <div className="flex min-w-0 items-center gap-2.5">
                        <span
                            className={`h-2 w-2 shrink-0 rounded-full ${issue.severity === "Critical" ? "bg-rose-500" : "bg-amber-400"}`}
                        />
                        <span className="truncate font-mono text-xs font-medium text-zinc-800">
                            {issue.resource}
                        </span>
                    </div>
                    <ChevronRight className="h-4 w-4 text-zinc-300 transition group-hover:translate-x-0.5 group-hover:text-zinc-600 md:order-last" />
                    <span className="col-span-2 truncate pl-[18px] text-xs text-zinc-600 md:col-span-1 md:pl-0">
                        {issue.kind}
                    </span>
                    <span className="hidden md:block">
                        <StatusBadge status={issue.severity} />
                    </span>
                    <span className="hidden text-xs text-zinc-500 md:block">
                        {issue.time}
                    </span>
                </button>
            ))}
        </div>
    );
}

function PipelineTable() {
    const router = useRouter();
    const { currentEnvironment } = useEnvironmentContext();
    const pipelineRuns = allPipelineRuns.filter((run) =>
        pipelines.some(
            (pipeline) =>
                pipeline.name === run.pipeline &&
                pipeline.environment === currentEnvironment,
        ),
    );
    const [error, setError] = useState(false);
    if (error) return <ErrorState onRetry={() => setError(false)} />;
    if (!pipelineRuns.length)
        return (
            <EmptyState
                title={`No recent pipeline runs in ${currentEnvironment}`}
                description="Runs will appear after a pipeline executes in this environment."
            />
        );
    return (
        <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white shadow-card">
            <table className="w-full min-w-[760px] border-collapse text-left">
                <thead>
                    <tr className="border-b border-zinc-200 bg-zinc-50/70 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                        <th className="px-4 py-2.5">Pipeline</th>
                        <th className="px-3 py-2.5">Status</th>
                        <th className="px-3 py-2.5">Started</th>
                        <th className="px-3 py-2.5">Duration</th>
                        <th className="px-3 py-2.5">Records</th>
                        <th className="px-3 py-2.5">Trigger</th>
                        <th className="w-10 px-3 py-2.5">
                            <span className="sr-only">Actions</span>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {pipelineRuns.map((run) => (
                        <tr
                            key={run.id}
                            tabIndex={0}
                            onClick={() =>
                                router.push(`/pipeline-runs/${run.id}`)
                            }
                            onKeyDown={(event) => {
                                if (event.key === "Enter")
                                    router.push(`/pipeline-runs/${run.id}`);
                            }}
                            className="group cursor-pointer border-b border-zinc-100 text-xs last:border-0 hover:bg-zinc-50"
                        >
                            <td className="px-4 py-3">
                                <div className="flex items-center gap-2.5">
                                    <span className="grid h-7 w-7 place-items-center rounded-md border border-zinc-200 bg-white text-zinc-400">
                                        <GitBranch className="h-3.5 w-3.5" />
                                    </span>
                                    <span className="font-mono font-medium text-zinc-800">
                                        {run.pipeline}
                                    </span>
                                </div>
                            </td>
                            <td className="px-3 py-3">
                                <StatusBadge status={run.status} />
                            </td>
                            <td className="whitespace-nowrap px-3 py-3 text-zinc-500">
                                {run.started}
                            </td>
                            <td className="px-3 py-3 tabular-nums text-zinc-600">
                                {run.duration}
                            </td>
                            <td className="px-3 py-3 tabular-nums text-zinc-600">
                                {run.records}
                            </td>
                            <td className="px-3 py-3 text-zinc-500">
                                {run.trigger}
                            </td>
                            <td className="px-3 py-3">
                                <button
                                    aria-label={`Actions for ${run.pipeline}`}
                                    className="rounded p-1 text-zinc-400 opacity-0 hover:bg-zinc-200 group-hover:opacity-100"
                                >
                                    <MoreHorizontal className="h-4 w-4" />
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            {process.env.NODE_ENV === "development" && <button className="sr-only" onClick={() => setError(true)}>
                Show error state
            </button>}
        </div>
    );
}

function HealthOverview() {
    const { currentEnvironment } = useEnvironmentContext();
    const healthItems =
        currentEnvironment === "Production" ? productionHealthItems : [];
    if (!healthItems.length)
        return (
            <EmptyState
                title={`No health signals in ${currentEnvironment}`}
                description="No demo health data requires attention in this environment."
            />
        );
    return (
        <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-card">
            <div className="grid gap-x-6 gap-y-5 sm:grid-cols-2">
                {healthItems.map((item) => (
                    <div key={item.label}>
                        <div className="mb-2 flex items-start justify-between">
                            <div>
                                <p className="text-xs font-medium text-zinc-700">
                                    {item.label}
                                </p>
                                <p className="mt-0.5 text-[11px] text-zinc-400">
                                    {item.note}
                                </p>
                            </div>
                            <span
                                className={`text-sm font-semibold tabular-nums ${item.tone === "warning" ? "text-amber-700" : "text-zinc-900"}`}
                            >
                                {item.value}
                            </span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-zinc-100">
                            <div
                                className={`h-full rounded-full ${item.tone === "warning" ? "bg-amber-400" : "bg-emerald-500"}`}
                                style={{ width: `${item.progress}%` }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function ActivityFeed() {
    const { currentEnvironment } = useEnvironmentContext();
    const activities = currentEnvironment === "Production" ? allActivities : [];
    const icons = {
        failed: CircleAlert,
        connected: Database,
        rule: ShieldCheck,
        success: GitBranch,
    };
    if (!activities.length)
        return (
            <EmptyState
                title={`No recent activity in ${currentEnvironment}`}
                description="Activity will appear after resources in this environment run or change."
            />
        );
    return (
        <div className="rounded-lg border border-zinc-200 bg-white px-4 shadow-card">
            {activities.map((item) => {
                const Icon = icons[item.type as keyof typeof icons];
                return (
                    <div
                        key={item.id}
                        className="flex gap-3 border-b border-zinc-100 py-3 last:border-0"
                    >
                        <span
                            className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full ${item.type === "failed" ? "bg-rose-50 text-rose-600" : item.type === "success" ? "bg-emerald-50 text-emerald-600" : "bg-zinc-100 text-zinc-500"}`}
                        >
                            <Icon className="h-3.5 w-3.5" />
                        </span>
                        <div className="min-w-0 flex-1">
                            <p className="truncate text-xs font-medium text-zinc-700">
                                {item.text}
                            </p>
                            <p className="mt-1 text-[11px] text-zinc-400">
                                {item.actor} · {item.time}
                            </p>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

function IssueDrawer({
    issue,
    onClose,
    onInvestigate,
}: {
    issue: Issue | null;
    onClose: () => void;
    onInvestigate: (issue: Issue) => void;
}) {
    return (
        <>
            <button
                aria-label="Close issue details"
                onClick={onClose}
                className={`fixed inset-0 z-30 bg-zinc-950/20 transition ${issue ? "opacity-100" : "pointer-events-none opacity-0"}`}
            />
            <aside
                className={`fixed inset-y-0 right-0 z-40 w-full max-w-md border-l border-zinc-200 bg-white shadow-panel transition-transform duration-300 ${issue ? "translate-x-0" : "translate-x-full"}`}
            >
                <div className="flex h-14 items-center justify-between border-b border-zinc-200 px-5">
                    <div className="flex items-center gap-2">
                        <CircleAlert className="h-4 w-4 text-amber-500" />
                        <span className="text-sm font-semibold">
                            Issue details
                        </span>
                    </div>
                    <button
                        onClick={onClose}
                        className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>
                {issue && (
                    <div className="p-5">
                        <div className="flex items-center justify-between">
                            <StatusBadge status={issue.severity} />
                            <span className="font-mono text-[11px] text-zinc-400">
                                {issue.id}
                            </span>
                        </div>
                        <h3 className="mt-5 font-mono text-base font-semibold text-zinc-900">
                            {issue.resource}
                        </h3>
                        <p className="mt-1 text-sm font-medium text-zinc-600">
                            {issue.kind}
                        </p>
                        <p className="mt-4 text-sm leading-6 text-zinc-600">
                            {issue.description}
                        </p>
                        <dl className="mt-6 divide-y divide-zinc-100 rounded-lg border border-zinc-200">
                            <div className="flex justify-between p-3 text-xs">
                                <dt className="text-zinc-500">Detected</dt>
                                <dd className="font-medium text-zinc-800">
                                    {issue.time}
                                </dd>
                            </div>
                            <div className="flex justify-between p-3 text-xs">
                                <dt className="text-zinc-500">Owner</dt>
                                <dd className="font-medium text-zinc-800">
                                    {issue.owner}
                                </dd>
                            </div>
                            <div className="flex justify-between p-3 text-xs">
                                <dt className="text-zinc-500">Environment</dt>
                                <dd className="flex items-center gap-1.5 font-medium text-zinc-800">
                                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                                    Production
                                </dd>
                            </div>
                        </dl>
                        <div className="mt-6 rounded-lg border border-indigo-100 bg-indigo-50/60 p-4">
                            <p className="text-xs font-semibold text-indigo-900">
                                Recommended next step
                            </p>
                            <p className="mt-1.5 text-xs leading-5 text-indigo-800/80">
                                {issue.nextStep}
                            </p>
                        </div>
                        <div className="mt-6 flex gap-2">
                            <button
                                onClick={() => onInvestigate(issue)}
                                className="flex h-9 flex-1 items-center justify-center gap-2 rounded-md bg-zinc-900 text-xs font-medium text-white hover:bg-zinc-800"
                            >
                                Investigate{" "}
                                <ArrowRight className="h-3.5 w-3.5" />
                            </button>
                            <Link
                                href={`/alerts/${issue.id}`}
                                className="flex h-9 items-center rounded-md border border-zinc-200 px-3 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
                            >
                                View Alert
                            </Link>
                        </div>
                    </div>
                )}
            </aside>
        </>
    );
}

export function Dashboard() {
    const router = useRouter();
    const { currentEnvironment } = useEnvironmentContext();
    const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
    return (
        <div className="animate-enter">
            <div className="mb-7 flex items-end justify-between gap-4">
                <div>
                    <div className="mb-1.5 flex items-center gap-2 text-[11px] font-medium text-zinc-400">
                        <Network className="h-3 w-3" /> {currentEnvironment}{" "}
                        workspace
                    </div>
                    <h1 className="text-2xl font-semibold tracking-[-0.035em] text-zinc-950">
                        Dashboard
                    </h1>
                    <p className="mt-1 text-sm text-zinc-500">
                        Monitor the health and activity of your data platform.
                    </p>
                </div>
                <div className="hidden items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-500 shadow-card sm:flex">
                    <span className="h-2 w-2 rounded-full bg-emerald-500 ring-4 ring-emerald-50" />
                    <span className="font-medium text-zinc-700">
                        {currentEnvironment === "Production"
                            ? "Platform operational"
                            : `No active issues in ${currentEnvironment}`}
                    </span>
                    <span className="text-zinc-300">·</span> Updated just now
                </div>
            </div>
            <Section
                title="Platform status"
                description="Operational summary for the last 24 hours"
            >
                <MetricCards />
            </Section>
            <Section
                title="Needs attention"
                description="Issues with the highest operational impact"
                className="mt-7"
                action={
                    <Link
                        href="/alerts"
                        className="flex items-center gap-1 text-xs font-medium text-zinc-500 hover:text-zinc-900"
                    >
                        View alerts <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                }
            >
                <Issues onSelect={setSelectedIssue} />
            </Section>
            <Section
                title="Recent pipeline runs"
                description="Latest activity across production pipelines"
                className="mt-7"
                action={
                    <Link
                        href="/pipeline-runs"
                        className="flex items-center gap-1 text-xs font-medium text-zinc-500 hover:text-zinc-900"
                    >
                        View all runs <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                }
            >
                <PipelineTable />
            </Section>
            <div className="mt-7 grid gap-7 xl:grid-cols-[1.35fr_0.85fr]">
                <Section
                    title="Platform health"
                    description="Key service-level indicators"
                    action={
                        <Link
                            href="/health-metrics?time=24h"
                            className="flex items-center gap-1 text-xs font-medium text-zinc-500 hover:text-zinc-900"
                        >
                            View Health Metrics{" "}
                            <ChevronRight className="h-3.5 w-3.5" />
                        </Link>
                    }
                >
                    <HealthOverview />
                </Section>
                <Section
                    title="Recent activity"
                    description="Changes across your workspace"
                >
                    <ActivityFeed />
                </Section>
            </div>
            <IssueDrawer
                issue={selectedIssue}
                onClose={() => setSelectedIssue(null)}
                onInvestigate={(issue) =>
                    router.push(
                        issue.id === "ALT-1042"
                            ? "/pipeline-runs/run_01J94EVT18"
                            : issue.id === "ALT-1040"
                              ? "/validation/order-id-unique"
                              : `/alerts/${issue.id}`,
                    )
                }
            />
        </div>
    );
}

export function DashboardSkeleton() {
    return (
        <div className="space-y-6">
            <div>
                <Skeleton className="h-7 w-36" />
                <Skeleton className="mt-2 h-4 w-72" />
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-32" />
                ))}
            </div>
            <Skeleton className="h-64" />
            <Skeleton className="h-80" />
        </div>
    );
}
