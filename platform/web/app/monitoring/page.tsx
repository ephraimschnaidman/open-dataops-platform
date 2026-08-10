import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { MonitoringPage } from "@/components/monitoring";

export const metadata: Metadata = { title: "Monitoring · Datum" };

export default function MonitoringRoute() {
    return <AppShell><MonitoringPage /></AppShell>;
}
