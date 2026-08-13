import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { AlertsPage } from "@/components/alerts";

export const metadata: Metadata = { title: "Alerts · Corvetra" };

export default function AlertsRoute() {
    return <AppShell><AlertsPage /></AppShell>;
}
