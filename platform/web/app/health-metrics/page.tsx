import type { Metadata } from "next";
import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import { HealthMetricsPage, HealthMetricsPageSkeleton } from "@/components/health-metrics";

export const metadata: Metadata = { title: "Health Metrics · Corvetra" };

export default function HealthMetricsRoute() {
    return <AppShell><Suspense fallback={<HealthMetricsPageSkeleton />}><HealthMetricsPage /></Suspense></AppShell>;
}
