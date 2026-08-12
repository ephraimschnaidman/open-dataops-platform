"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Activity, Bell, Boxes, CheckCircle2, ChevronDown, CircleGauge, Command, Database, FileCheck2, FileText, GitBranch, HeartPulse, LayoutDashboard, Menu, MonitorDot, Plus, Search, Settings, ShieldAlert, Sparkles, UserRound, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { environments, useEnvironmentContext } from "@/lib/environment-context";
import { useOverlayFocus } from "@/components/overlays";

interface NavGroup {
    label: string;
    items: Array<{ name: string; icon: LucideIcon; href?: string; count?: number }>;
}

const navGroups: NavGroup[] = [
    { label: "", items: [{ name: "Dashboard", icon: LayoutDashboard, href: "/" }] },
    { label: "Build", items: [{ name: "Data Sources", icon: Database, href: "/data-sources" }, { name: "Pipelines", icon: GitBranch, href: "/pipelines" }, { name: "Metadata", icon: Boxes }] },
    { label: "Operate", items: [{ name: "Pipeline Runs", icon: Activity, href: "/pipeline-runs" }, { name: "Monitoring", icon: MonitorDot, href: "/monitoring" }, { name: "Alerts", icon: ShieldAlert, href: "/alerts", count: 4 }, { name: "Logs", icon: FileText, href: "/logs" }] },
    { label: "Platform", items: [{ name: "Validation", icon: FileCheck2, href: "/validation" }, { name: "Health Metrics", icon: HeartPulse, href: "/health-metrics" }, { name: "Settings", icon: Settings, href: "/settings" }] },
];

const searchItems = [
    { name: "Customer Ingestion", type: "Pipeline", href: "/pipelines/customer-ingestion" },
    { name: "Events Processing", type: "Pipeline", href: "/pipelines/events-processing" },
    { name: "Billing Reconciliation", type: "Pipeline", href: "/pipelines/billing-reconciliation" },
    { name: "Risk Reporting", type: "Pipeline", href: "/pipelines/risk-reporting" },
    { name: "Billing PostgreSQL", type: "Source", href: "/data-sources/billing-postgres" },
];
const newItems = [
    { icon: Database, label: "Data source" },
    { icon: GitBranch, label: "Pipeline" },
    { icon: FileCheck2, label: "Validation rule" },
];

function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
    const pathname = usePathname();
    return <><button aria-label="Close navigation" onClick={onClose} className={`fixed inset-0 z-30 bg-zinc-950/30 transition lg:hidden ${open ? "opacity-100" : "pointer-events-none opacity-0"}`} /><aside className={`fixed inset-y-0 left-0 z-40 flex w-[226px] flex-col border-r border-zinc-200 bg-[#fbfbfc] transition-transform duration-200 lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex h-14 items-center justify-between border-b border-zinc-200 px-4"><div className="flex items-center gap-2.5"><span className="grid h-7 w-7 place-items-center rounded-md bg-zinc-900 text-white"><CircleGauge className="h-4 w-4" /></span><span className="text-sm font-semibold tracking-[-0.02em]">Datum</span></div><button onClick={onClose} className="rounded-md p-1 text-zinc-500 hover:bg-zinc-100 lg:hidden"><X className="h-4 w-4" /></button></div>
        <nav className="flex-1 overflow-y-auto px-2.5 py-3">{navGroups.map((group) => <div key={group.label || "primary"} className="mb-5">{group.label && <p className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-[0.11em] text-zinc-400">{group.label}</p>}<div className="space-y-0.5">{group.items.map(({ name, icon: Icon, count, href }) => { const active = Boolean(href && (href === "/" ? pathname === "/" : pathname.startsWith(href))); const className = `group flex w-full items-center gap-2.5 rounded-md px-2.5 py-[7px] text-left text-[13px] transition ${active ? "bg-zinc-900 font-medium text-white shadow-sm" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-950"}`; const content = <><Icon className={`h-4 w-4 ${active ? "text-zinc-300" : "text-zinc-400 group-hover:text-zinc-600"}`} /><span className="flex-1">{name}</span>{count && <span className="rounded-full bg-amber-100 px-1.5 text-[10px] font-semibold text-amber-700">{count}</span>}</>; return href ? <Link key={name} href={href} onClick={onClose} className={className}>{content}</Link> : <span key={name} title={`${name} is not available in this MVP`} aria-disabled="true" className={`${className} cursor-not-allowed opacity-50 hover:bg-transparent hover:text-zinc-600`}>{content}</span>; })}</div></div>)}</nav>
        <div className="border-t border-zinc-200 p-3"><div className="rounded-lg border border-zinc-200 bg-white p-3 shadow-card"><div className="flex items-center gap-2 text-xs font-medium"><Sparkles className="h-3.5 w-3.5 text-indigo-500" /> Usage this month</div><div className="mt-2 h-1.5 overflow-hidden rounded-full bg-zinc-100"><div className="h-full w-[68%] rounded-full bg-indigo-500" /></div><p className="mt-2 text-[11px] text-zinc-500">68% of included runs</p></div></div>
    </aside></>;
}

export function AppShell({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const { currentEnvironment, setCurrentEnvironment } = useEnvironmentContext();
    const [mobileOpen, setMobileOpen] = useState(false);
    const [environmentOpen, setEnvironmentOpen] = useState(false);
    const [newOpen, setNewOpen] = useState(false);
    const [searchOpen, setSearchOpen] = useState(false);
    const [query, setQuery] = useState("");
    const envRef = useRef<HTMLDivElement>(null);
    const newRef = useRef<HTMLDivElement>(null);
    const searchDialogRef = useRef<HTMLDivElement>(null);
    const searchInputRef = useRef<HTMLInputElement>(null);
    useOverlayFocus(searchOpen, () => setSearchOpen(false), searchDialogRef, searchInputRef);
    useEffect(() => { const key = (event: KeyboardEvent) => { if ((event.metaKey || event.ctrlKey) && event.key === "k") { event.preventDefault(); setSearchOpen(true); } if (event.key === "Escape") setSearchOpen(false); }; document.addEventListener("keydown", key); return () => document.removeEventListener("keydown", key); }, []);
    useEffect(() => { const click = (event: MouseEvent) => { if (!envRef.current?.contains(event.target as Node)) setEnvironmentOpen(false); if (!newRef.current?.contains(event.target as Node)) setNewOpen(false); }; document.addEventListener("mousedown", click); return () => document.removeEventListener("mousedown", click); }, []);
    const filtered = searchItems.filter((item) => item.name.toLowerCase().includes(query.toLowerCase()));
    return <div className="min-h-screen"><Sidebar open={mobileOpen} onClose={() => setMobileOpen(false)} /><div className="lg:pl-[226px]">
        <header className="sticky top-0 z-20 flex h-14 min-w-0 items-center gap-2 border-b border-zinc-200 bg-white/95 px-3 backdrop-blur sm:gap-3 md:px-6"><button onClick={() => setMobileOpen(true)} aria-label="Open navigation" className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-100 lg:hidden"><Menu className="h-5 w-5" /></button><button onClick={() => setSearchOpen(true)} aria-haspopup="dialog" className="flex h-8 min-w-0 flex-1 max-w-[340px] items-center gap-2 rounded-md border border-zinc-200 bg-zinc-50 px-2.5 text-xs text-zinc-500 transition hover:border-zinc-300 hover:bg-white"><Search className="h-3.5 w-3.5 shrink-0" /><span className="min-w-0 flex-1 truncate text-left">Search anything...</span><kbd className="hidden rounded border border-zinc-200 bg-white px-1.5 py-0.5 text-[10px] text-zinc-400 sm:block">⌘ K</kbd></button><div className="ml-auto flex shrink-0 items-center gap-1.5">
            <div className="relative" ref={newRef}><button disabled title="Creation workflows are not available in this MVP" className="flex h-8 cursor-not-allowed items-center gap-1.5 rounded-md bg-zinc-300 px-3 text-xs font-medium text-zinc-600 shadow-sm"><Plus className="h-3.5 w-3.5" /> New <ChevronDown className="h-3 w-3 text-zinc-400" /></button>{newOpen && <div className="animate-enter absolute right-0 top-10 w-48 rounded-lg border border-zinc-200 bg-white p-1.5 text-xs shadow-panel"><p className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Create</p>{newItems.map(({ icon: Icon, label }) => <button key={label} className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-zinc-700 hover:bg-zinc-50"><Icon className="h-3.5 w-3.5 text-zinc-400" />{label}</button>)}</div>}</div>
            <div className="relative hidden sm:block" ref={envRef}><button aria-label={`Current environment: ${currentEnvironment}`} aria-expanded={environmentOpen} onClick={() => setEnvironmentOpen(!environmentOpen)} className="flex h-8 items-center gap-2 rounded-md border border-zinc-200 bg-white px-2.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50"><span className={`h-1.5 w-1.5 rounded-full ring-2 ${currentEnvironment === "Production" ? "bg-emerald-500 ring-emerald-100" : currentEnvironment === "Staging" ? "bg-blue-400 ring-blue-100" : "bg-violet-400 ring-violet-100"}`} /> {currentEnvironment} <ChevronDown className="h-3 w-3 text-zinc-400" /></button>{environmentOpen && <div className="animate-enter absolute right-0 top-10 w-48 rounded-lg border border-zinc-200 bg-white p-1.5 text-xs shadow-panel"><p className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Environment</p>{environments.map((environment) => { const selected = environment === currentEnvironment; return <button key={environment} onClick={() => { setCurrentEnvironment(environment); setEnvironmentOpen(false); }} className={`mt-0.5 flex w-full items-center justify-between rounded-md px-2 py-2 ${selected ? "bg-zinc-50 font-medium text-zinc-900" : "text-zinc-500 hover:bg-zinc-50"}`}><span className="flex items-center gap-2"><span className={`h-1.5 w-1.5 rounded-full ${environment === "Production" ? "bg-emerald-500" : environment === "Staging" ? "bg-blue-400" : "bg-violet-400"}`} />{environment}</span>{selected && <CheckCircle2 className="h-3.5 w-3.5" />}</button>; })}</div>}</div>
            <button disabled title="Notifications are not available in this MVP" aria-label="Notifications unavailable" className="relative grid h-8 w-8 cursor-not-allowed place-items-center rounded-md text-zinc-300"><Bell className="h-4 w-4" /><span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-amber-500 ring-2 ring-white" /></button><button disabled title="Profile controls are not available in this MVP" aria-label="Profile controls unavailable" className="ml-0.5 grid h-8 w-8 cursor-not-allowed place-items-center rounded-full bg-zinc-100 text-zinc-400 ring-1 ring-zinc-200"><UserRound className="h-4 w-4" /></button>
        </div></header><main className="mx-auto min-w-0 max-w-[1440px] p-3 sm:p-4 md:p-6 lg:p-8">{children}</main></div>
        {searchOpen && <div className="fixed inset-0 z-50 flex justify-center overflow-y-auto bg-zinc-950/30 px-3 pt-[8vh] backdrop-blur-[2px] sm:px-4 sm:pt-[12vh]" onMouseDown={(e) => { if (e.target === e.currentTarget) setSearchOpen(false); }}><div ref={searchDialogRef} role="dialog" aria-modal="true" aria-label="Search Datum" tabIndex={-1} className="animate-enter h-fit w-full max-w-xl overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-panel"><div role="search" className="flex items-center gap-3 border-b border-zinc-200 px-3 sm:px-4"><Search className="h-4 w-4 shrink-0 text-zinc-400" /><input ref={searchInputRef} value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search pipelines, sources, and runs" placeholder="Search pipelines, sources, runs..." className="h-12 min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-zinc-400" /><button onClick={() => setSearchOpen(false)} aria-label="Close search" className="rounded border border-zinc-200 px-1.5 py-0.5 text-[10px] text-zinc-400">ESC</button></div><div className="p-2"><p className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">{query ? "Results" : "Recent"}</p>{filtered.length ? filtered.map((item) => <button key={item.href} aria-label={`Open ${item.type} ${item.name}`} onClick={() => { setSearchOpen(false); setQuery(""); router.push(item.href); }} className="flex w-full min-w-0 items-center gap-3 rounded-lg px-2.5 py-2.5 text-left text-sm hover:bg-zinc-50"><Command className="h-4 w-4 shrink-0 text-zinc-400" /><span className="min-w-0 flex-1 truncate font-medium text-zinc-700">{item.name}</span><span className="shrink-0 text-[11px] text-zinc-400">{item.type}</span></button>) : <p className="px-2 py-8 text-center text-sm text-zinc-500">No resources found.</p>}</div></div></div>}
    </div>;
}
