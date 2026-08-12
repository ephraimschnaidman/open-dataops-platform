"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Activity, AlertTriangle, CircleCheck, CircleX, GitBranch, MoreHorizontal, Play, Search } from "lucide-react";
import { pipelines } from "@/lib/pipelines-data";
import { getPipelineRunDetail } from "@/lib/pipeline-run-detail-data";
import {
    formatRunDuration,
    formatStartedAt,
    pipelineRuns as initialPipelineRuns,
    pipelineRunsReferenceTime,
    sortPipelineRuns,
    timeRangeOptions,
    type PipelineRun,
    type PipelineRunStatus,
    type PipelineRunTimeRange,
    type PipelineRunTrigger,
} from "@/lib/pipeline-runs-data";
import { Button, EmptyState, ErrorState, FilterSelect, MetricCard, PageHeader, SearchField, Skeleton, StatusBadge } from "@/components/ui";
import { ConfirmationDialog, DropdownMenu, Toast, type MenuItem } from "@/components/overlays";
import { withReturnTo } from "@/lib/navigation-context";
import { conceptualRetryId, persistConceptualRetry, persistRunStatus, readConceptualRetries, readRunStatusOverrides } from "@/lib/mock-run-state";
import { isEnvironment, useEnvironmentContext } from "@/lib/environment-context";

interface ToastState {
    message: string;
    tone: "success" | "neutral";
    action?: { label: string; onSelect: () => void };
}

type DialogState = { kind: "retry" | "cancel"; run: PipelineRun } | null;

function RunMetrics({ runs, rangeLabel }: { runs: PipelineRun[]; rangeLabel: string }) {
    const running = runs.filter((run) => run.status === "Running").length;
    const failed = runs.filter((run) => run.status === "Failed").length;
    const successful = runs.filter((run) => run.status === "Success").length;
    const resolved = successful + failed;
    const successRate = resolved ? `${((successful / resolved) * 100).toFixed(1)}%` : "—";
    return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><MetricCard label="Total Runs" value={String(runs.length)} detail={rangeLabel} icon={Activity} /><MetricCard label="Running" value={String(running)} detail="Currently executing" icon={Play} /><MetricCard label="Failed" value={String(failed)} detail="Require investigation" icon={CircleX} tone="danger" /><MetricCard label="Success Rate" value={successRate} detail={`${successful} of ${resolved} non-cancelled runs`} icon={CircleCheck} tone="positive" /></div>;
}

function SupportingDataWarning({ onRetry }: { onRetry: () => void }) {
    return <div role="status" className="mb-3 flex flex-col gap-2 rounded-lg border border-amber-200 bg-amber-50/70 px-3 py-2.5 text-xs sm:flex-row sm:items-center"><AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" /><div className="min-w-0 flex-1"><span className="font-medium text-amber-900">Some pipeline details are unavailable.</span><span className="ml-2 font-mono text-[10px] text-amber-700">PIPELINE_REFERENCE_DATA_UNAVAILABLE</span></div><Button variant="ghost" className="h-7 self-start px-2 text-amber-800 hover:bg-amber-100 sm:self-auto" onClick={onRetry}>Try Again</Button></div>;
}

function PipelineRunsTable({ runs, now, activeMenu, onMenuChange, onOpen: onOpenFallback, onRetry, onCancel, onViewPipeline, onViewLogs }: { runs: PipelineRun[]; now: number; activeMenu: string | null; onMenuChange: (id: string | null) => void; onOpen: (run: PipelineRun) => void; onRetry: (run: PipelineRun) => void; onCancel: (run: PipelineRun) => void; onViewPipeline: (run: PipelineRun) => void; onViewLogs: (run: PipelineRun) => void }) {
    const onOpen = onOpenFallback;
    const menuItems = (run: PipelineRun): MenuItem[] => {
        const items: MenuItem[] = [{ label: "View Run", onSelect: () => onOpen(run) }];
        if (run.status === "Failed" || run.status === "Cancelled") items.push({ label: "Retry", onSelect: () => onRetry(run) });
        if (run.status === "Running") items.push({ label: "Cancel Run", tone: "danger", onSelect: () => onCancel(run) });
        items.push({ label: "View Logs", onSelect: () => onViewLogs(run) }, { label: "View Pipeline", onSelect: () => onViewPipeline(run) });
        return items;
    };
    return <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white shadow-card"><table className="w-full min-w-[720px] border-collapse text-left"><thead><tr className="border-b border-zinc-200 bg-zinc-50/70 text-[10px] font-semibold uppercase tracking-wider text-zinc-400"><th className="px-4 py-2.5">Pipeline</th><th className="px-3 py-2.5">Status</th><th className="px-3 py-2.5">Stage</th><th className="px-3 py-2.5">Started</th><th className="hidden px-3 py-2.5 md:table-cell">Duration</th><th className="hidden px-3 py-2.5 lg:table-cell">Trigger</th><th className="hidden px-3 py-2.5 text-right xl:table-cell">Records</th><th className="hidden px-3 py-2.5 xl:table-cell">Run ID</th><th className="w-12 px-3 py-2.5"><span className="sr-only">Actions</span></th></tr></thead><tbody>{runs.map((run) => <tr key={run.id} tabIndex={0} aria-label={`Open run ${run.id} for ${run.pipelineName}`} onClick={() => onOpen(run)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onOpen(run); } }} className="group cursor-pointer border-b border-zinc-100 text-xs outline-none last:border-0 hover:bg-zinc-50 focus-visible:bg-indigo-50/50"><td className="px-4 py-3"><div className="flex min-w-[170px] items-center gap-2.5"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-zinc-200 bg-white text-zinc-400"><GitBranch className="h-3.5 w-3.5" /></span><span className="truncate font-medium text-zinc-850">{run.pipelineName}</span></div></td><td className="px-3 py-3"><StatusBadge status={run.status} />{run.status === "Failed" && <span className="mt-1.5 block max-w-[190px] truncate font-mono text-[10px] text-rose-700" title={run.vendorCode ? `${run.platformCode} · ${run.vendorCode}` : run.platformCode}>{run.platformCode}</span>}</td><td className="whitespace-nowrap px-3 py-3 font-medium text-zinc-700">{run.stage}</td><td className="whitespace-nowrap px-3 py-3 text-zinc-600" title={new Date(run.startedAt).toLocaleString()}>{formatStartedAt(run.startedAt, now)}</td><td className="hidden whitespace-nowrap px-3 py-3 tabular-nums text-zinc-600 md:table-cell">{formatRunDuration(run, now)}</td><td className="hidden px-3 py-3 text-zinc-600 lg:table-cell">{run.trigger}</td><td className="hidden px-3 py-3 text-right tabular-nums text-zinc-600 xl:table-cell">{run.records?.toLocaleString() ?? "—"}</td><td className="hidden px-3 py-3 xl:table-cell"><span className="block max-w-[120px] truncate font-mono text-[10px] text-zinc-500" title={run.id}>{run.id}</span></td><td className="px-3 py-3" onClick={(event) => event.stopPropagation()} onKeyDown={(event) => event.stopPropagation()}><DropdownMenu open={activeMenu === run.id} onOpenChange={(open) => onMenuChange(open ? run.id : null)} items={menuItems(run)}><button aria-label={`Actions for ${run.id}`} aria-expanded={activeMenu === run.id} onClick={() => onMenuChange(activeMenu === run.id ? null : run.id)} className="rounded p-1 text-zinc-400 opacity-70 hover:bg-zinc-200 hover:text-zinc-700 group-hover:opacity-100"><MoreHorizontal className="h-4 w-4" /></button></DropdownMenu></td></tr>)}</tbody></table></div>;
}

export function PipelineRunsPage() {
    const router = useRouter();
    const { currentEnvironment } = useEnvironmentContext();
    const [environment, setEnvironment] = useState<typeof currentEnvironment>(currentEnvironment);
    const [runs, setRuns] = useState(initialPipelineRuns);
    const [now] = useState(pipelineRunsReferenceTime);
    const [query, setQuery] = useState("");
    const [status, setStatus] = useState<PipelineRunStatus | "All">("All");
    const [pipelineId, setPipelineId] = useState("All");
    const [trigger, setTrigger] = useState<PipelineRunTrigger | "All">("All");
    const [timeRange, setTimeRange] = useState<PipelineRunTimeRange>("day");
    const [activeMenu, setActiveMenu] = useState<string | null>(null);
    const [dialog, setDialog] = useState<DialogState>(null);
    const [toast, setToast] = useState<ToastState | null>(null);
    const [pageError, setPageError] = useState(false);
    const [supportingError, setSupportingError] = useState(false);
    const [summaryError, setSummaryError] = useState(false);
    const [retryError, setRetryError] = useState(false);
    useEffect(() => {
        const overrides = readRunStatusOverrides();
        setRuns([...readConceptualRetries(), ...initialPipelineRuns].map((run) => overrides[run.id] ? { ...run, status: overrides[run.id] } : run));
        const params = new URLSearchParams(window.location.search);
        const requestedEnvironment = params.get("environment");
        const requestedPipeline = params.get("pipeline");
        const requestedStatus = params.get("status") as PipelineRunStatus | null;
        const requestedTrigger = params.get("trigger") as PipelineRunTrigger | null;
        const requestedTime = params.get("time") as PipelineRunTimeRange | null;
        if (requestedPipeline && pipelines.some((pipeline) => pipeline.id === requestedPipeline)) setPipelineId(requestedPipeline);
        if (isEnvironment(requestedEnvironment)) setEnvironment(requestedEnvironment); else if (requestedPipeline) setEnvironment(pipelines.find((pipeline) => pipeline.id === requestedPipeline)?.environment ?? currentEnvironment); else setEnvironment(currentEnvironment);
        if (requestedStatus && ["Running", "Success", "Failed", "Cancelled"].includes(requestedStatus)) setStatus(requestedStatus);
        if (requestedTrigger && ["Scheduled", "Manual", "Retry", "Event"].includes(requestedTrigger)) setTrigger(requestedTrigger);
        if (requestedTime && timeRangeOptions.some((option) => option.value === requestedTime)) setTimeRange(requestedTime);
        setQuery(params.get("q") ?? "");
    }, [currentEnvironment]);
    const syncParam = (key: string, value: string, defaultValue: string) => { const params = new URLSearchParams(window.location.search); if (!value || value === defaultValue) params.delete(key); else params.set(key, value); const next = params.toString(); window.history.replaceState(null, "", `${window.location.pathname}${next ? `?${next}` : ""}`); };
    const selectedRange = timeRangeOptions.find((option) => option.value === timeRange) ?? timeRangeOptions[1];
    const rangeRuns = useMemo(() => runs.filter((run) => now - Date.parse(run.startedAt) <= selectedRange.minutes * 60_000), [runs, now, selectedRange.minutes]);
    const filteredRuns = useMemo(() => sortPipelineRuns(rangeRuns.filter((run) => { const term = query.trim().toLowerCase(); const matchesSearch = !term || run.pipelineName.toLowerCase().includes(term) || run.id.toLowerCase().includes(term) || run.platformCode.toLowerCase().includes(term) || run.vendorCode?.toLowerCase().includes(term); const runEnvironment = pipelines.find((pipeline) => pipeline.id === run.pipelineId)?.environment; return matchesSearch && (status === "All" || run.status === status) && (pipelineId === "All" ? runEnvironment === environment : run.pipelineId === pipelineId) && (trigger === "All" || run.trigger === trigger); })), [rangeRuns, query, status, pipelineId, trigger, environment]);
    const clearFilters = () => { setQuery(""); setStatus("All"); setPipelineId("All"); setTrigger("All"); setTimeRange("day"); window.history.replaceState(null, "", window.location.pathname); };
    const placeholder = (message: string) => setToast({ message, tone: "neutral" });
    const confirmAction = () => {
        if (!dialog) return;
        if (dialog.kind === "cancel") {
            setRuns((current) => current.map((run) => run.id === dialog.run.id ? { ...run, status: "Cancelled", platformCode: "PIPELINE_RUN_CANCELLED", message: "Execution was cancelled by the user.", recommendedAction: "Retry when it is operationally safe to continue.", durationSeconds: Math.max(1, Math.floor((Date.now() - Date.parse(run.startedAt)) / 1000)) } : run));
            persistRunStatus(dialog.run.id, "Cancelled");
            setDialog(null);
            setToast({ message: "Pipeline run cancelled", tone: "neutral" });
            return;
        }
        if (retryError) { setDialog(null); return; }
        const original = dialog.run;
        const retry: PipelineRun = { ...original, id: conceptualRetryId(original.id), status: "Running", stage: "Extract", trigger: "Retry", startedAt: new Date().toISOString(), durationSeconds: undefined, records: undefined, platformCode: "PIPELINE_RUNNING", vendorCode: undefined, message: "The retry execution is currently running.", recommendedAction: "No action is required while execution continues.", retryOf: original.id };
        setRuns((current) => [retry, ...current]);
        persistConceptualRetry(retry);
        setDialog(null);
        setToast({ message: `Pipeline retry started as ${retry.id}`, tone: "success", action: { label: "View Running", onSelect: () => { setStatus("Running"); syncParam("status", "Running", "All"); } } });
    };

    if (pageError) return <div className="animate-enter"><PageHeader title="Pipeline Runs" description="View and investigate pipeline execution history." /><ErrorState title="Pipeline runs couldn't be loaded" description="We couldn't retrieve pipeline execution history." actionLabel="Try Again" technicalDetails={[{ label: "Platform Code", value: "PIPELINE_RUN_LIST_UNAVAILABLE" }, { label: "Vendor / HTTP Code", value: "503" }]} onRetry={() => setPageError(false)} /></div>;
    return <div className="animate-enter"><PageHeader title="Pipeline Runs" description="View and investigate pipeline execution history." />{summaryError ? <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <div key={index} className="rounded-lg border border-zinc-200 bg-white p-4 shadow-card"><AlertTriangle className="h-4 w-4 text-amber-500" /><p className="mt-3 text-xs font-medium text-zinc-700">Summary unavailable</p><p className="mt-1 font-mono text-[10px] text-zinc-500">PIPELINE_RUN_SUMMARY_UNAVAILABLE</p><button onClick={() => setSummaryError(false)} className="mt-2 text-[11px] font-medium text-indigo-600 hover:text-indigo-700">Try Again</button></div>)}</div> : <RunMetrics runs={rangeRuns} rangeLabel={selectedRange.label} />}<section className="mt-7"><div className="mb-3 flex flex-col gap-2 xl:flex-row xl:items-center"><SearchField value={query} onChange={(value) => { setQuery(value); syncParam("q", value, ""); }} placeholder="Search runs..." className="xl:max-w-xs" /><FilterSelect label="Filter by status" value={status} onChange={(value) => { setStatus(value as PipelineRunStatus | "All"); syncParam("status", value, "All"); }} options={[{ label: "All statuses", value: "All" }, ...(["Running", "Success", "Failed", "Cancelled"] as PipelineRunStatus[]).map((value) => ({ label: value, value }))]} /><FilterSelect label="Filter by pipeline" value={pipelineId} onChange={(value) => { setPipelineId(value); syncParam("pipeline", value, "All"); }} options={[{ label: "All pipelines", value: "All" }, ...pipelines.map((pipeline) => ({ label: pipeline.name, value: pipeline.id }))]} /><FilterSelect label="Filter by trigger" value={trigger} onChange={(value) => { setTrigger(value as PipelineRunTrigger | "All"); syncParam("trigger", value, "All"); }} options={[{ label: "All triggers", value: "All" }, ...(["Scheduled", "Manual", "Retry", "Event"] as PipelineRunTrigger[]).map((value) => ({ label: value, value }))]} /><FilterSelect label="Filter by time range" value={timeRange} onChange={(value) => { setTimeRange(value as PipelineRunTimeRange); syncParam("time", value, "day"); }} options={timeRangeOptions.map(({ label, value }) => ({ label, value }))} /><span className="text-[11px] text-zinc-400 xl:ml-auto">{filteredRuns.length} {filteredRuns.length === 1 ? "run" : "runs"}</span></div>{supportingError && <SupportingDataWarning onRetry={() => setSupportingError(false)} />}{!runs.length ? <EmptyState title="No pipeline runs yet" description="Pipeline executions will appear here after a pipeline runs." icon={<Activity className="h-4 w-4" />} tone="neutral" action={<Button onClick={() => router.push("/pipelines")}>View Pipelines</Button>} /> : !filteredRuns.length ? <EmptyState title="No runs match your filters" description="Try adjusting your search, status, pipeline, trigger, or time range." icon={<Search className="h-4 w-4" />} tone="neutral" action={<Button onClick={clearFilters}>Clear Filters</Button>} /> : <PipelineRunsTable runs={filteredRuns} now={now} activeMenu={activeMenu} onMenuChange={setActiveMenu} onOpen={(run) => { if (getPipelineRunDetail(run.id)) router.push(withReturnTo(`/pipeline-runs/${run.id}`, `${window.location.pathname}${window.location.search}`)); else placeholder(`Execution ${run.id} is conceptual and has no persisted detail view.`); }} onRetry={(run) => setDialog({ kind: "retry", run })} onCancel={(run) => setDialog({ kind: "cancel", run })} onViewPipeline={(run) => router.push(`/pipelines/${run.pipelineId}`)} onViewLogs={(run) => router.push(`/logs?${new URLSearchParams({ scope: "run", pipeline: run.pipelineId, run: run.id, environment: pipelines.find((pipeline) => pipeline.id === run.pipelineId)?.environment ?? "Production", code: run.platformCode, time: "24h", ...(run.status === "Failed" ? { levels: "Error,Warning" } : {}), ...(run.status === "Running" ? { auto: "5" } : {}) }).toString()}`)} />}</section><div className="sr-only"><button onClick={() => setPageError(true)}>Show pipeline runs error</button><button onClick={() => setSupportingError(true)}>Show pipeline reference data error</button><button onClick={() => setSummaryError(true)}>Show pipeline run summary error</button><button onClick={() => setRuns([])}>Show empty pipeline runs</button><button onClick={() => setRetryError(true)}>Make next retry fail</button></div><ConfirmationDialog open={Boolean(dialog)} title={dialog?.kind === "cancel" ? "Cancel this pipeline run?" : "Retry this pipeline run?"} description={dialog?.kind === "cancel" ? "The current execution will be stopped. Any work already committed by the pipeline may remain." : "This will start a new execution using the pipeline's current configuration."} details={dialog?.kind === "retry" ? [{ label: "Pipeline", value: dialog.run.pipelineName }, { label: "Original Run", value: dialog.run.id }] : undefined} cancelLabel={dialog?.kind === "cancel" ? "Keep Running" : "Cancel"} confirmLabel={dialog?.kind === "cancel" ? "Cancel Run" : "Retry Run"} confirmVariant={dialog?.kind === "cancel" ? "danger" : "primary"} onCancel={() => setDialog(null)} onConfirm={confirmAction} />{retryError && !dialog && <div className="fixed inset-0 z-50 grid place-items-center bg-zinc-950/30 p-4 backdrop-blur-[2px]" onMouseDown={(event) => { if (event.target === event.currentTarget) setRetryError(false); }}><div className="w-full max-w-md"><ErrorState title="Pipeline retry could not be started" description="The orchestration service did not accept the retry request." actionLabel="Try Again" technicalDetails={[{ label: "Platform Code", value: "PIPELINE_RETRY_FAILED" }, { label: "Vendor Code", value: "HTTP 503" }]} onRetry={() => setRetryError(false)} /></div></div>}{toast && <Toast {...toast} onClose={() => setToast(null)} />}</div>;
}

export function PipelineRunsSkeleton() {
    return <div><PageHeader title="Pipeline Runs" description="View and investigate pipeline execution history." /><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-28" />)}</div><div className="mt-7"><div aria-label="Loading run filters" className="mb-3 flex flex-wrap gap-2">{["Search runs...", "Status", "Pipeline", "Trigger", "Last 24 hours"].map((label, index) => <button key={label} disabled className={`h-9 rounded-md border border-zinc-200 bg-white text-left text-xs text-zinc-400 shadow-card ${index === 0 ? "w-72 px-8" : "w-32 px-3"}`}>{label}</button>)}</div><div className="overflow-hidden rounded-lg border border-zinc-200 bg-white"><Skeleton className="h-9 rounded-none" />{Array.from({ length: 7 }).map((_, index) => <div key={index} className="flex gap-8 border-t border-zinc-100 px-4 py-3"><Skeleton className="h-9 w-52" /><Skeleton className="h-9 w-28" /><Skeleton className="h-9 w-20" /><Skeleton className="h-9 flex-1" /></div>)}</div></div></div>;
}
