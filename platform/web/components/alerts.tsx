"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, BellRing, CheckCircle2, Clock3, MoreHorizontal, RefreshCw, Search, ShieldAlert } from "lucide-react";
import { AlertStatusBadge, SeverityBadge } from "@/components/alert-badges";
import { ConfirmationDialog, DropdownMenu, Toast, type MenuItem } from "@/components/overlays";
import { Button, EmptyState, ErrorState, FilterSelect, MetricCard, OperationalStatus, PageHeader, SearchField, Skeleton } from "@/components/ui";
import { alerts as initialAlerts, persistAlertStatus, readAlertOverrides, sortAlerts, type AlertEnvironment, type AlertResourceType, type AlertSeverity, type AlertsQaState, type AlertWorkflowStatus, type OperationalAlert } from "@/lib/alerts-data";
import { getDevelopmentQaParam } from "@/lib/development-qa";
import { useEnvironmentContext } from "@/lib/environment-context";

type StatusFilter = "All" | "Active" | AlertWorkflowStatus;
type ResourceFilter = "All" | AlertResourceType;
type EnvironmentFilter = "All" | AlertEnvironment;

function AlertMetrics({ alerts }: { alerts: OperationalAlert[] }) {
    const active = alerts.filter((alert) => alert.status !== "Resolved");
    return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><MetricCard label="Active Alerts" value={String(active.length)} detail="Open and acknowledged" icon={BellRing} /><MetricCard label="Critical" value={String(active.filter((alert) => alert.severity === "Critical").length)} detail="Highest operational impact" icon={ShieldAlert} tone="danger" /><MetricCard label="Warning" value={String(active.filter((alert) => alert.severity === "Warning").length)} detail="Require review" icon={AlertTriangle} tone="warning" /><MetricCard label="Acknowledged" value={String(active.filter((alert) => alert.status === "Acknowledged").length)} detail="Seen by an operator" icon={CheckCircle2} /></div>;
}

function contextualItems(alert: OperationalAlert, navigate: (destination: string, alert: OperationalAlert) => void): MenuItem[] {
    if (alert.status === "Resolved") return [];
    const items: MenuItem[] = [];
    if (alert.runId) items.push({ label: "View Failed Run", onSelect: () => navigate("run", alert) });
    if (alert.resourceType === "Pipeline" || alert.resourceType === "Pipeline Run" || alert.resourceType === "Validation") items.push({ label: "View Pipeline", onSelect: () => navigate("pipeline", alert) });
    if (alert.resourceType === "Data Source") items.push({ label: "View Data Source", onSelect: () => navigate("source", alert) });
    if (alert.resourceType === "Validation") items.push({ label: "Review Validation", onSelect: () => navigate("validation", alert) });
    if (alert.severity === "Critical") items.push({ label: "View Logs", onSelect: () => navigate("logs", alert) });
    return items;
}

function AlertsTable({ alerts, activeMenu, onMenuChange, onOpen, onAcknowledge, onResolve, onNavigate }: { alerts: OperationalAlert[]; activeMenu: string | null; onMenuChange: (id: string | null) => void; onOpen: (alert: OperationalAlert) => void; onAcknowledge: (alert: OperationalAlert) => void; onResolve: (alert: OperationalAlert) => void; onNavigate: (destination: string, alert: OperationalAlert) => void }) {
    const items = (alert: OperationalAlert): MenuItem[] => [{ label: "View Details", onSelect: () => onOpen(alert) }, ...(alert.status === "Open" ? [{ label: "Acknowledge", onSelect: () => onAcknowledge(alert) }] : []), ...(alert.status !== "Resolved" ? [{ label: "Resolve", onSelect: () => onResolve(alert) }] : []), ...contextualItems(alert, onNavigate)];
    return <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white shadow-card">
        <table className="w-full min-w-[720px] border-collapse text-left">
            <thead><tr className="border-b border-zinc-200 bg-zinc-50/70 text-[10px] font-semibold uppercase tracking-wider text-zinc-400"><th className="px-4 py-2.5">Severity</th><th className="px-3 py-2.5">Alert</th><th className="px-3 py-2.5">Resource</th><th className="px-3 py-2.5">Status</th><th className="hidden px-3 py-2.5 md:table-cell">Started</th><th className="hidden px-3 py-2.5 lg:table-cell">Last Seen</th><th className="hidden px-3 py-2.5 xl:table-cell">Environment</th><th className="w-12 px-3 py-2.5"><span className="sr-only">Actions</span></th></tr></thead>
            <tbody>{alerts.map((alert) => <tr key={alert.id} tabIndex={0} onClick={() => onOpen(alert)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onOpen(alert); } }} className="group cursor-pointer border-b border-zinc-100 text-xs outline-none last:border-0 hover:bg-zinc-50 focus-visible:bg-indigo-50/50">
                <td className="px-4 py-3"><SeverityBadge severity={alert.severity} /></td>
                <td className="px-3 py-3"><span className="block min-w-[210px] font-medium text-zinc-800">{alert.title}</span><span className="mt-1 block font-mono text-[10px] text-zinc-500">{alert.id} · {alert.platformCode}</span></td>
                <td className="px-3 py-3"><span className="block min-w-[150px] font-medium text-zinc-700">{alert.resourceName}</span><span className="mt-0.5 block text-[10px] text-zinc-400">{alert.resourceType}{alert.runId ? ` · ${alert.runId}` : ""}</span></td>
                <td className="px-3 py-3"><AlertStatusBadge status={alert.status} /></td>
                <td className="hidden whitespace-nowrap px-3 py-3 text-zinc-500 md:table-cell">{alert.startedLabel}</td>
                <td className="hidden whitespace-nowrap px-3 py-3 text-zinc-500 lg:table-cell">{alert.lastSeenLabel}</td>
                <td className="hidden px-3 py-3 text-zinc-600 xl:table-cell">{alert.environment}</td>
                <td className="px-3 py-3" onClick={(event) => event.stopPropagation()} onKeyDown={(event) => event.stopPropagation()}><DropdownMenu open={activeMenu === alert.id} onOpenChange={(open) => onMenuChange(open ? alert.id : null)} items={items(alert)}><button aria-label={`Actions for ${alert.id}`} onClick={() => onMenuChange(activeMenu === alert.id ? null : alert.id)} className="rounded p-1 text-zinc-400 opacity-70 hover:bg-zinc-200 hover:text-zinc-700 group-hover:opacity-100"><MoreHorizontal className="h-4 w-4" /></button></DropdownMenu></td>
            </tr>)}</tbody>
        </table>
    </div>;
}

export function AlertsPage() {
    const router = useRouter();
    const { currentEnvironment } = useEnvironmentContext();
    const [alerts, setAlerts] = useState(initialAlerts);
    const [query, setQuery] = useState("");
    const [severity, setSeverity] = useState<"All" | AlertSeverity>("All");
    const [status, setStatus] = useState<StatusFilter>("Active");
    const [resourceType, setResourceType] = useState<ResourceFilter>("All");
    const [environment, setEnvironment] = useState<EnvironmentFilter>(currentEnvironment);
    const [qaState, setQaState] = useState<AlertsQaState>("mixed");
    const [lastUpdated, setLastUpdated] = useState("10:43 AM");
    const [activeMenu, setActiveMenu] = useState<string | null>(null);
    const [resolveAlert, setResolveAlert] = useState<OperationalAlert | null>(null);
    const [toast, setToast] = useState<{ message: string; tone: "success" | "neutral" } | null>(null);
    useEffect(() => {
        const overrides = readAlertOverrides();
        setAlerts((current) => current.map((alert) => overrides[alert.id] ? { ...alert, status: overrides[alert.id] } : alert));
        const params = new URLSearchParams(window.location.search);
        const qa = getDevelopmentQaParam(params) as AlertsQaState | null;
        if (qa && ["mixed", "critical", "warning", "acknowledged", "no-active", "no-alerts", "resolved", "filtered-empty", "stale", "error", "partial-summary"].includes(qa)) { setQaState(qa); if (qa === "resolved") setStatus("Resolved"); }
        const requestedSeverity = params.get("severity") as AlertSeverity | null; if (requestedSeverity && ["Critical", "Warning"].includes(requestedSeverity)) setSeverity(requestedSeverity);
        const requestedStatus = params.get("status") as StatusFilter | null; if (requestedStatus && ["All", "Active", "Open", "Acknowledged", "Resolved"].includes(requestedStatus)) setStatus(requestedStatus);
        const requestedResource = params.get("resource") as ResourceFilter | null; if (requestedResource && ["Pipeline", "Pipeline Run", "Data Source", "Validation", "Platform"].includes(requestedResource)) setResourceType(requestedResource);
        const requestedEnvironment = params.get("environment") as AlertEnvironment | null; if (requestedEnvironment && ["Production", "Staging", "Development"].includes(requestedEnvironment)) setEnvironment(requestedEnvironment); else setEnvironment(currentEnvironment);
        setQuery(params.get("q") ?? "");
    }, [currentEnvironment]);
    const syncParam = (key: string, value: string, defaultValue: string) => { const params = new URLSearchParams(window.location.search); if (value === defaultValue || !value) params.delete(key); else params.set(key, value); const next = params.toString(); window.history.replaceState(null, "", `${window.location.pathname}${next ? `?${next}` : ""}`); };
    const qaAlerts = useMemo(() => {
        if (qaState === "no-alerts") return [];
        if (qaState === "critical") return alerts.filter((alert) => alert.severity === "Critical");
        if (qaState === "warning") return alerts.filter((alert) => alert.severity === "Warning");
        if (qaState === "acknowledged") return alerts.filter((alert) => alert.status !== "Resolved").map((alert) => ({ ...alert, status: "Acknowledged" as const }));
        if (qaState === "resolved") return alerts.filter((alert) => alert.status === "Resolved");
        return alerts;
    }, [alerts, qaState]);
    const environmentAlerts = useMemo(() => qaAlerts.filter((alert) => environment === "All" || alert.environment === environment), [qaAlerts, environment]);
    const filteredAlerts = useMemo(() => qaState === "no-active" || qaState === "filtered-empty" ? [] : sortAlerts(environmentAlerts.filter((alert) => { const term = query.trim().toLowerCase(); const searchable = [alert.id, alert.title, alert.resourceName, alert.runId, alert.platformCode, alert.vendorCode, alert.message].filter(Boolean).join(" ").toLowerCase(); return (!term || searchable.includes(term)) && (severity === "All" || alert.severity === severity) && (status === "All" || (status === "Active" ? alert.status !== "Resolved" : alert.status === status)) && (resourceType === "All" || alert.resourceType === resourceType); })), [environmentAlerts, qaState, query, severity, status, resourceType]);
    const hasActiveFilters = Boolean(query) || severity !== "All" || (status !== "Active" && status !== "All") || resourceType !== "All" || environment !== "All";
    const resetFilters = () => { setQuery(""); setSeverity("All"); setStatus("All"); setResourceType("All"); setEnvironment("All"); const params = new URLSearchParams(window.location.search); ["q", "severity", "resource", "environment"].forEach((key) => params.delete(key)); params.set("status", "All"); const next = params.toString(); window.history.replaceState(null, "", `${window.location.pathname}?${next}`); };
    const updateStatus = (alert: OperationalAlert, nextStatus: AlertWorkflowStatus) => { persistAlertStatus(alert.id, nextStatus); setAlerts((current) => current.map((item) => item.id === alert.id ? { ...item, status: nextStatus, ...(nextStatus === "Acknowledged" ? { acknowledgedAt: "Aug 10, 2026 · 10:44 AM" } : { resolvedAt: "Aug 10, 2026 · 10:44 AM", resolutionType: "Manual" as const }) } : item)); setToast({ message: nextStatus === "Acknowledged" ? "Alert acknowledged" : "Alert resolved", tone: "success" }); };
    const navigate = (destination: string, alert: OperationalAlert) => { if (destination === "run" && alert.runId) router.push(`/pipeline-runs/${alert.runId}`); else if (destination === "pipeline" && alert.resourceId) router.push(`/pipelines/${alert.resourceId}`); else if (destination === "source" && alert.resourceId) router.push(`/data-sources/${alert.resourceId}`); else if (destination === "validation") router.push(`/validation?${new URLSearchParams({ ...(alert.resourceId ? { pipeline: alert.resourceId } : {}), ...(alert.runId ? { run: alert.runId } : {}), result: "Failed" }).toString()}`); else if (destination === "logs") router.push(`/logs?${new URLSearchParams({ scope: alert.resourceType === "Data Source" ? "source" : alert.resourceType === "Validation" ? "validation" : alert.runId ? "run" : "pipeline", ...(alert.resourceId ? { [alert.resourceType === "Data Source" ? "source" : "pipeline"]: alert.resourceId } : {}), ...(alert.runId ? { run: alert.runId } : {}), environment: alert.environment, code: alert.platformCode, alert: alert.id, time: "24h" }).toString()}`); else setToast({ message: "Resource detail is not available for this alert.", tone: "neutral" }); };
    const openAlert = (alert: OperationalAlert) => { const returnTo = `${window.location.pathname}${window.location.search}`; const params = new URLSearchParams({ returnTo }); router.push(`/alerts/${alert.id}?${params.toString()}`); };
    const selectQa = (value: string) => { const next = value === "default" ? "mixed" : value as AlertsQaState; setQaState(next); if (next === "resolved") setStatus("Resolved"); else setStatus("Active"); syncParam("qa", value === "default" ? "" : value, ""); };
    const activeCount = environmentAlerts.filter((alert) => alert.status !== "Resolved").length;
    if (qaState === "error") return <div className="animate-enter"><PageHeader title="Alerts" description="Review and act on operational issues across your data platform." /><OperationalStatus statusLabel="Failed" result={{ status: "Error", platformCode: "ALERTS_UNAVAILABLE", vendorCode: "503", message: "Alerts couldn't be loaded. The platform could not retrieve operational alert data.", recommendedAction: "Try loading Alerts again." }} action={<Button onClick={() => selectQa("default")}>Try Again</Button>} /></div>;
    return <div className="animate-enter">
        <PageHeader
            title="Alerts"
            description="Review and act on operational issues across your data platform."
            action={<div className="flex flex-wrap items-center gap-2">
                {process.env.NODE_ENV === "development" && <div className="flex items-center gap-2">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">QA State</span>
                    <FilterSelect label="QA State" value={qaState === "mixed" ? "default" : qaState} onChange={selectQa} options={[{ label: "Default", value: "default" }, { label: "Critical only", value: "critical" }, { label: "Warning only", value: "warning" }, { label: "All acknowledged", value: "acknowledged" }, { label: "No active alerts", value: "no-active" }, { label: "Resolved history", value: "resolved" }, { label: "Filtered empty", value: "filtered-empty" }, { label: "Stale data", value: "stale" }, { label: "Page error", value: "error" }, { label: "Partial summary error", value: "partial-summary" }]} />
                </div>}
                <span className="text-[11px] text-zinc-400">Last updated {lastUpdated}</span>
                <Button onClick={() => setLastUpdated("just now")}><RefreshCw className="h-3.5 w-3.5" /> Refresh</Button>
            </div>}
        />
        {qaState === "stale" && <div className="mb-7 rounded-lg border border-amber-200 bg-amber-50 p-4"><div className="flex gap-3"><Clock3 className="mt-0.5 h-4 w-4 text-amber-600" /><div><p className="text-sm font-semibold text-amber-900">Alert data may be stale</p><p className="mt-1 font-mono text-[10px] text-amber-700">ALERT_DATA_STALE</p><p className="mt-2 text-xs text-amber-800">The latest alert evaluation was completed 18 minutes ago. Confirm the current resource state before resolving alerts.</p><p className="mt-1 text-xs text-amber-800">Last updated 10:24 AM</p></div></div></div>}
        {qaState === "partial-summary" ? <ErrorState title="Alert summary unavailable" description="The alert queue remains available below." actionLabel="Try Again" technicalDetails={[{ label: "Platform Code", value: "ALERT_SUMMARY_UNAVAILABLE" }]} onRetry={() => selectQa("default")} /> : <AlertMetrics alerts={environmentAlerts} />}
        <section className="mt-7">
            <div className="mb-3 flex flex-col gap-2 xl:flex-row xl:items-center">
                <SearchField value={query} onChange={(value) => { setQuery(value); syncParam("q", value, ""); }} placeholder="Search alerts..." className="xl:max-w-xs" />
                <FilterSelect label="Severity" value={severity} onChange={(value) => { setSeverity(value as "All" | AlertSeverity); syncParam("severity", value, "All"); }} options={[{ label: "All severities", value: "All" }, { label: "Critical", value: "Critical" }, { label: "Warning", value: "Warning" }]} />
                <FilterSelect label="Status" value={status} onChange={(value) => { setStatus(value as StatusFilter); syncParam("status", value, "Active"); }} options={[{ label: "All statuses", value: "All" }, { label: "Active", value: "Active" }, { label: "Open", value: "Open" }, { label: "Acknowledged", value: "Acknowledged" }, { label: "Resolved", value: "Resolved" }]} />
                <FilterSelect label="Resource Type" value={resourceType} onChange={(value) => { setResourceType(value as ResourceFilter); syncParam("resource", value, "All"); }} options={[{ label: "All resources", value: "All" }, { label: "Pipeline", value: "Pipeline" }, { label: "Pipeline Run", value: "Pipeline Run" }, { label: "Data Source", value: "Data Source" }, { label: "Validation", value: "Validation" }, { label: "Platform", value: "Platform" }]} />
                <FilterSelect label="Environment" value={environment} onChange={(value) => { setEnvironment(value as EnvironmentFilter); syncParam("environment", value, "All"); }} options={[{ label: "All environments", value: "All" }, { label: "Production", value: "Production" }, { label: "Staging", value: "Staging" }, { label: "Development", value: "Development" }]} />
                <div className="flex items-center gap-2 xl:ml-auto">
                    {hasActiveFilters && <Button variant="ghost" onClick={resetFilters}>Reset filters</Button>}
                    <span className="text-[11px] text-zinc-400">{filteredAlerts.length} {filteredAlerts.length === 1 ? "alert" : "alerts"}</span>
                </div>
            </div>
            {qaState === "no-alerts" ? <EmptyState title="No alerts yet" description="Operational alerts will appear here when pipelines, data sources, or validation checks require attention." icon={<BellRing className="h-4 w-4" />} tone="neutral" />
                : qaState === "no-active" && status === "Active" ? <EmptyState title="No active alerts" description="Everything currently looks healthy." icon={<CheckCircle2 className="h-4 w-4" />} action={<Button onClick={() => { setStatus("Resolved"); syncParam("status", "Resolved", "Active"); }}>View Resolved Alerts</Button>} />
                    : !filteredAlerts.length ? <EmptyState title="No alerts match these filters" description="Try adjusting your search or filters." icon={<Search className="h-4 w-4" />} tone="neutral" action={hasActiveFilters ? <Button onClick={resetFilters}>Reset filters</Button> : undefined} />
                        : <AlertsTable alerts={filteredAlerts} activeMenu={activeMenu} onMenuChange={setActiveMenu} onOpen={openAlert} onAcknowledge={(alert) => updateStatus(alert, "Acknowledged")} onResolve={setResolveAlert} onNavigate={navigate} />}
        </section>
        <ConfirmationDialog open={Boolean(resolveAlert)} title="Resolve this alert?" description="This alert will move out of the active queue. If the underlying problem returns, the platform may reopen the alert or create a new occurrence." confirmLabel="Resolve Alert" onCancel={() => setResolveAlert(null)} onConfirm={() => { if (resolveAlert) updateStatus(resolveAlert, "Resolved"); setResolveAlert(null); }} />
        {toast && <Toast {...toast} onClose={() => setToast(null)} />}
        <span className="sr-only">{activeCount} active alerts</span>
    </div>;
}

export function AlertsSkeleton() {
    return <div className="space-y-7"><div className="flex items-end justify-between"><div><Skeleton className="h-7 w-28" /><Skeleton className="mt-2 h-4 w-96" /></div><Skeleton className="h-9 w-48" /></div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-28" />)}</div><div><div className="mb-3 flex flex-wrap gap-2"><Skeleton className="h-9 w-72" />{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-9 w-32" />)}</div><div className="overflow-hidden rounded-lg border border-zinc-200 bg-white"><Skeleton className="h-9 rounded-none" />{Array.from({ length: 7 }).map((_, index) => <div key={index} className="flex gap-8 border-t border-zinc-100 px-4 py-3"><Skeleton className="h-9 w-24" /><Skeleton className="h-9 w-64" /><Skeleton className="h-9 w-40" /><Skeleton className="h-9 flex-1" /></div>)}</div></div></div>;
}
