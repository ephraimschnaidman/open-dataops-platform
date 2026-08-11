import type { Metadata } from "next";
import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import { LogsPage, LogsPageSkeleton } from "@/components/logs";

export const metadata: Metadata = { title: "Logs · Datum" };

export default function LogsRoute() {
    return <AppShell><Suspense fallback={<LogsPageSkeleton />}><LogsPage /></Suspense></AppShell>;
}
