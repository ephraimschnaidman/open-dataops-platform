import type { Metadata } from "next";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { MonitoringPage } from "@/components/monitoring";

export const metadata: Metadata = { title: "Monitoring · Corvetra" };

export default function MonitoringRoute() {
    return <AppShell><div className="mb-3 flex justify-end"><Link href="/health-metrics?time=24h" className="inline-flex h-8 items-center rounded-md border border-zinc-200 bg-white px-2.5 text-xs font-medium text-zinc-700 shadow-card hover:bg-zinc-50">View Health Metrics</Link></div><MonitoringPage /></AppShell>;
}
