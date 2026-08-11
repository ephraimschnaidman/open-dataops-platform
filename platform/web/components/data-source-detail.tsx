"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Activity, CheckCircle2, CircleAlert, Clock3, Database, FileText, GitBranch, MoreHorizontal, Pencil, PlugZap } from "lucide-react";
import type { DataSourceDetail, SourceActivity } from "@/lib/data-source-detail-data";
import { Breadcrumbs, Button, Card, EmptyState, KeyValueGrid, OperationalStatus, PageHeader, Skeleton, StatusBadge } from "@/components/ui";

function HealthCard({ source }: { source: DataSourceDetail }) {
    return <Card title="Operational Health" description="Latest connectivity result and recommended response."><div className="p-4"><dl className="mb-4 grid grid-cols-2 gap-3 rounded-lg border border-zinc-100 bg-zinc-50/60 p-3 text-xs sm:grid-cols-3"><div><dt className="text-zinc-500">Source Status</dt><dd className="mt-1"><StatusBadge status={source.status} /></dd></div><div><dt className="text-zinc-500">Last Checked</dt><dd className="mt-1 font-medium text-zinc-800">{source.health.lastChecked}</dd></div><div><dt className="text-zinc-500">Response Time</dt><dd className="mt-1 font-medium tabular-nums text-zinc-800">{source.health.latency}</dd></div></dl><OperationalStatus result={source.health} /></div></Card>;
}

function ConfigurationCard({ source }: { source: DataSourceDetail }) {
    return <Card title="Configuration Summary" description="Connection settings with sensitive values hidden."><KeyValueGrid items={source.configuration} /></Card>;
}

function ConnectedPipelines({ source }: { source: DataSourceDetail }) {
    return <Card title="Connected Pipelines" description={`${source.pipelines} ${source.pipelines === 1 ? "pipeline depends" : "pipelines depend"} on this source.`}>{source.connectedPipelines.length ? <div className="overflow-x-auto"><table className="w-full min-w-[680px] border-collapse text-left"><thead><tr className="border-b border-zinc-200 bg-zinc-50/70 text-[10px] font-semibold uppercase tracking-wider text-zinc-400"><th className="px-4 py-2.5">Pipeline</th><th className="px-3 py-2.5">Status</th><th className="px-3 py-2.5">Schedule</th><th className="px-3 py-2.5">Last Run</th></tr></thead><tbody>{source.connectedPipelines.map((pipeline) => <tr key={pipeline.id} className="border-b border-zinc-100 text-xs last:border-0 hover:bg-zinc-50"><td className="px-4 py-3"><span className="flex items-center gap-2.5"><span className="grid h-7 w-7 place-items-center rounded-md border border-zinc-200 bg-white text-zinc-400"><GitBranch className="h-3.5 w-3.5" /></span><span className="font-mono font-medium text-zinc-800">{pipeline.name}</span></span></td><td className="px-3 py-3"><StatusBadge status={pipeline.status} /></td><td className="px-3 py-3 text-zinc-600">{pipeline.schedule}</td><td className="whitespace-nowrap px-3 py-3 text-zinc-500">{pipeline.lastRun}</td></tr>)}</tbody></table></div> : <div className="p-4"><EmptyState title="No connected pipelines" description="This source is not currently used by any pipelines." icon={<GitBranch className="h-4 w-4" />} /></div>}</Card>;
}

function ValidationCard({ source }: { source: DataSourceDetail }) {
    const counts = [{ label: "Passed", value: source.validation.passed, tone: "text-emerald-700" }, { label: "Warnings", value: source.validation.warnings, tone: "text-amber-700" }, { label: "Failed", value: source.validation.failed, tone: "text-rose-700" }];
    return <Card title="Validation Summary" description="Latest validation results for incoming data." action={<StatusBadge status={source.validation.status} />}><div className="p-4"><div className="grid grid-cols-3 gap-2">{counts.map((count) => <div key={count.label} className="rounded-md border border-zinc-100 bg-zinc-50/60 p-3"><p className={`text-xl font-semibold tabular-nums ${count.tone}`}>{count.value}</p><p className="mt-0.5 text-[11px] text-zinc-500">{count.label}</p></div>)}</div><div className="mt-4 flex items-center justify-between border-t border-zinc-100 pt-3 text-xs"><span className="flex items-center gap-1.5 text-zinc-500"><Clock3 className="h-3.5 w-3.5" /> Last validation</span><span className="font-medium text-zinc-700">{source.validation.lastRun}</span></div></div></Card>;
}

const activityIcons = { success: CheckCircle2, warning: CircleAlert, error: CircleAlert, neutral: Activity };
const activityTones = { success: "bg-emerald-50 text-emerald-600", warning: "bg-amber-50 text-amber-600", error: "bg-rose-50 text-rose-600", neutral: "bg-zinc-100 text-zinc-500" };

function ActivityItem({ item, last }: { item: SourceActivity; last: boolean }) {
    const Icon = activityIcons[item.tone];
    return <li className="relative flex gap-3 pb-5 last:pb-0">{!last && <span className="absolute left-3.5 top-7 h-[calc(100%-12px)] w-px bg-zinc-200" />}<span className={`relative z-10 grid h-7 w-7 shrink-0 place-items-center rounded-full ${activityTones[item.tone]}`}><Icon className="h-3.5 w-3.5" /></span><div className="min-w-0 flex-1"><div className="flex flex-col justify-between gap-1 sm:flex-row"><p className="text-xs font-medium text-zinc-800">{item.title}</p><time className="shrink-0 text-[11px] text-zinc-400">{item.time}</time></div><p className="mt-1 text-xs leading-5 text-zinc-500">{item.detail}</p><p className="mt-1 text-[11px] text-zinc-400">{item.actor}</p></div></li>;
}

function RecentActivity({ source }: { source: DataSourceDetail }) {
    return <Card title="Recent Activity" description="Connection and configuration events for this source."><ol className="p-4">{source.recentActivity.map((item, index) => <ActivityItem key={item.id} item={item} last={index === source.recentActivity.length - 1} />)}</ol></Card>;
}

export function DataSourceDetailPage({ source }: { source: DataSourceDetail }) {
    const router = useRouter();
    const [notice, setNotice] = useState("");
    const showNotice = (message: string) => { setNotice(message); window.setTimeout(() => setNotice(""), 3000); };
    const actions = <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto"><Button onClick={() => router.push(`/validation?${new URLSearchParams({ source: source.id }).toString()}`)}>View Validation</Button><Button onClick={() => router.push(`/logs?${new URLSearchParams({ scope: "source", source: source.id, environment: source.environment, time: "1h" }).toString()}`)}><FileText className="h-3.5 w-3.5" /> View Logs</Button><Button variant="primary" onClick={() => showNotice("Live connection testing is not available in this phase.")}><PlugZap className="h-3.5 w-3.5" /> Test Connection</Button><Button onClick={() => showNotice("Source editing is not available in this phase.")}><Pencil className="h-3.5 w-3.5" /> Edit</Button><Button aria-label="More source actions" onClick={() => showNotice("Additional source actions are not available in this phase.")}><MoreHorizontal className="h-4 w-4" /> More</Button></div>;

    return <div className="animate-enter"><Breadcrumbs items={[{ label: "Data Sources", href: "/data-sources" }, { label: source.name }]} /><PageHeader title={source.name} description={source.description} eyebrow={<><Database className="h-3 w-3" /> {source.type}<span className="text-zinc-300">·</span>{source.environment}<StatusBadge status={source.status} /></>} action={actions} /><div className="grid gap-7 xl:grid-cols-2"><HealthCard source={source} /><ConfigurationCard source={source} /></div><div className="mt-7"><ConnectedPipelines source={source} /></div><div className="mt-7 grid gap-7 xl:grid-cols-[0.85fr_1.15fr]"><ValidationCard source={source} /><RecentActivity source={source} /></div><div className="mt-5 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-zinc-400"><span>Owner: <strong className="font-medium text-zinc-600">{source.owner}</strong></span><span>Created: <strong className="font-medium text-zinc-600">{source.createdAt}</strong></span><span>Source ID: <strong className="font-mono font-medium text-zinc-600">{source.id}</strong></span></div>{notice && <div role="status" className="fixed bottom-5 right-5 z-50 max-w-sm rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs text-white shadow-panel">{notice}</div>}</div>;
}

export function DataSourceDetailSkeleton() {
    return <div className="space-y-7"><Skeleton className="h-4 w-56" /><div className="flex items-end justify-between gap-4"><div><Skeleton className="h-7 w-60" /><Skeleton className="mt-2 h-4 w-96" /></div><div className="flex gap-2"><Skeleton className="h-9 w-32" /><Skeleton className="h-9 w-20" /><Skeleton className="h-9 w-9" /></div></div><div className="grid gap-7 xl:grid-cols-2"><Skeleton className="h-80" /><Skeleton className="h-80" /></div><Skeleton className="h-64" /><div className="grid gap-7 xl:grid-cols-2"><Skeleton className="h-56" /><Skeleton className="h-56" /></div></div>;
}
