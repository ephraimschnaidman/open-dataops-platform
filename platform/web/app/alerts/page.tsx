import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { AlertsPage } from "@/components/alerts";

export const metadata: Metadata = { title: "Alerts · Datum" };

export default function AlertsRoute() {
    return <AppShell><AlertsPage /></AppShell>;
}
