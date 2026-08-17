"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  Boxes,
  CheckCircle2,
  ChevronDown,
  CircleGauge,
  Database,
  FileCheck2,
  FileText,
  GitBranch,
  HeartPulse,
  LayoutDashboard,
  LogOut,
  Menu,
  MonitorDot,
  Plus,
  Settings,
  ShieldAlert,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { environments, useEnvironmentContext } from "@/lib/environment-context";

interface NavGroup {
  label: string;
  items: Array<{ name: string; icon: LucideIcon; href?: string; demoOnly?: boolean }>;
}

const navGroups: NavGroup[] = [
  { label: "", items: [{ name: "Dashboard", icon: LayoutDashboard, href: "/" }] },
  {
    label: "Build",
    items: [
      { name: "Data Sources", icon: Database, href: "/data-sources" },
      { name: "Pipelines", icon: GitBranch, href: "/pipelines" },
      { name: "Metadata", icon: Boxes },
    ],
  },
  {
    label: "Operate",
    items: [
      { name: "Pipeline Runs", icon: Activity, href: "/pipeline-runs" },
      { name: "Monitoring", icon: MonitorDot, href: "/monitoring" },
      { name: "Alerts", icon: ShieldAlert, href: "/alerts" },
      { name: "Logs", icon: FileText, href: "/logs" },
    ],
  },
  {
    label: "Platform",
    items: [
      { name: "Validation", icon: FileCheck2, href: "/validation" },
      { name: "Health Metrics", icon: HeartPulse, href: "/health-metrics" },
      { name: "Settings", icon: Settings, href: "/settings", demoOnly: true },
    ],
  },
];

function Sidebar({
  open,
  onClose,
  currentEnvironment,
  onEnvironmentChange,
}: {
  open: boolean;
  onClose: () => void;
  currentEnvironment: string;
  onEnvironmentChange: (environment: (typeof environments)[number]) => void;
}) {
  const pathname = usePathname();

  return (
    <>
      <button
        aria-label="Close navigation"
        onClick={onClose}
        className={`fixed inset-0 z-30 bg-zinc-950/30 transition lg:hidden ${open ? "opacity-100" : "pointer-events-none opacity-0"}`}
      />
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-[226px] flex-col border-r border-zinc-200 bg-[#fbfbfc] transition-transform duration-200 lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex h-14 items-center justify-between border-b border-zinc-200 px-4">
          <div className="flex items-center gap-2.5">
            <span className="grid h-7 w-7 place-items-center rounded-md bg-zinc-900 text-white"><CircleGauge className="h-4 w-4" /></span>
            <span className="text-sm font-semibold tracking-[-0.02em]">Corvetra</span>
          </div>
          <button aria-label="Close navigation" onClick={onClose} className="rounded-md p-1 text-zinc-500 hover:bg-zinc-100 lg:hidden"><X className="h-4 w-4" /></button>
        </div>

        <div className="border-b border-zinc-200 p-3 lg:hidden">
          <label className="block text-[10px] font-semibold uppercase tracking-[0.11em] text-zinc-400" htmlFor="mobile-environment">Environment</label>
          <select
            id="mobile-environment"
            aria-label="Environment"
            value={currentEnvironment}
            onChange={(event) => onEnvironmentChange(event.target.value as (typeof environments)[number])}
            className="mt-2 h-9 w-full rounded-md border border-zinc-200 bg-white px-2.5 text-xs font-medium text-zinc-700"
          >
            {environments.map((environment) => <option key={environment} value={environment}>{environment}</option>)}
          </select>
        </div>

        <nav className="flex-1 overflow-y-auto px-2.5 py-3">
          {navGroups.map((group) => (
            <div key={group.label || "primary"} className="mb-5">
              {group.label && <p className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-[0.11em] text-zinc-400">{group.label}</p>}
              <div className="space-y-0.5">
                {group.items.map(({ name, icon: Icon, href, demoOnly }) => {
                  const active = Boolean(href && (href === "/" ? pathname === "/" : pathname.startsWith(href)));
                  const className = `group flex w-full items-center gap-2.5 rounded-md px-2.5 py-[7px] text-left text-[13px] transition ${active ? "bg-zinc-900 font-medium text-white shadow-sm" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-950"}`;
                  const content = (
                    <>
                      <Icon className={`h-4 w-4 ${active ? "text-zinc-300" : "text-zinc-400 group-hover:text-zinc-600"}`} />
                      <span className="flex-1">{name}</span>
                      {demoOnly && <span className={`rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase ${active ? "bg-white/15 text-zinc-200" : "bg-zinc-200 text-zinc-500"}`}>Demo</span>}
                    </>
                  );
                  return href ? (
                    <Link key={name} href={href} title={demoOnly ? "Demo-only settings; changes are not persisted" : undefined} onClick={onClose} className={className}>{content}</Link>
                  ) : (
                    <span key={name} title={`${name} is not available in this MVP`} aria-disabled="true" className={`${className} cursor-not-allowed opacity-50 hover:bg-transparent hover:text-zinc-600`}>{content}</span>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>
    </>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { currentEnvironment, setCurrentEnvironment } = useEnvironmentContext();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [environmentOpen, setEnvironmentOpen] = useState(false);
  const environmentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!environmentRef.current?.contains(event.target as Node)) setEnvironmentOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  return (
    <div className="min-h-screen">
      <Sidebar
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        currentEnvironment={currentEnvironment}
        onEnvironmentChange={setCurrentEnvironment}
      />
      <div className="min-w-0 lg:pl-[226px]">
        <header className="sticky top-0 z-20 flex h-14 min-w-0 items-center gap-2 border-b border-zinc-200 bg-white/95 px-3 backdrop-blur sm:gap-3 md:px-6">
          <button onClick={() => setMobileOpen(true)} aria-label="Open navigation" className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-100 lg:hidden"><Menu className="h-5 w-5" /></button>
          <p className="min-w-0 flex-1 truncate text-xs text-zinc-400">Global search is not available in this release.</p>
          <div className="ml-auto flex shrink-0 items-center gap-1.5">
            <button disabled title="Creation workflows are not available in this MVP" className="hidden h-8 cursor-not-allowed items-center gap-1.5 rounded-md bg-zinc-200 px-3 text-xs font-medium text-zinc-500 sm:flex"><Plus className="h-3.5 w-3.5" /> New</button>
            <div className="relative hidden sm:block" ref={environmentRef}>
              <button
                aria-label={`Current environment: ${currentEnvironment}`}
                aria-expanded={environmentOpen}
                onClick={() => setEnvironmentOpen(!environmentOpen)}
                className="flex h-8 items-center gap-2 rounded-md border border-zinc-200 bg-white px-2.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
              >
                <span className={`h-1.5 w-1.5 rounded-full ring-2 ${currentEnvironment === "Production" ? "bg-emerald-500 ring-emerald-100" : currentEnvironment === "Staging" ? "bg-blue-400 ring-blue-100" : "bg-violet-400 ring-violet-100"}`} />
                {currentEnvironment}
                <ChevronDown className="h-3 w-3 text-zinc-400" />
              </button>
              {environmentOpen && (
                <div className="animate-enter absolute right-0 top-10 w-48 rounded-lg border border-zinc-200 bg-white p-1.5 text-xs shadow-panel">
                  <p className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Environment</p>
                  {environments.map((environment) => {
                    const selected = environment === currentEnvironment;
                    return (
                      <button
                        key={environment}
                        onClick={() => {
                          setCurrentEnvironment(environment);
                          setEnvironmentOpen(false);
                        }}
                        className={`mt-0.5 flex w-full items-center justify-between rounded-md px-2 py-2 ${selected ? "bg-zinc-50 font-medium text-zinc-900" : "text-zinc-500 hover:bg-zinc-50"}`}
                      >
                        <span className="flex items-center gap-2">
                          <span className={`h-1.5 w-1.5 rounded-full ${environment === "Production" ? "bg-emerald-500" : environment === "Staging" ? "bg-blue-400" : "bg-violet-400"}`} />
                          {environment}
                        </span>
                        {selected && <CheckCircle2 className="h-3.5 w-3.5" />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
            <span className="hidden text-[10px] text-zinc-400 xl:inline">Authenticated session</span>
            <button title="Sign out" aria-label="Sign out" onClick={logout} className="ml-0.5 grid h-8 w-8 place-items-center rounded-full bg-zinc-100 text-zinc-500 ring-1 ring-zinc-200 transition hover:bg-zinc-200 hover:text-zinc-800"><LogOut className="h-4 w-4" /></button>
          </div>
        </header>
        <main className="mx-auto min-w-0 max-w-[1440px] p-3 sm:p-4 md:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
