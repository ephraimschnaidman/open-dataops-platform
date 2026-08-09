import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { DataSourcesPage } from "@/components/data-sources";

export const metadata: Metadata = { title: "Data Sources · Datum" };

export default function DataSources() {
    return <AppShell><DataSourcesPage /></AppShell>;
}
