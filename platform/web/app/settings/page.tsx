import type { Metadata } from "next";
import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import { SettingsPage, SettingsPageSkeleton } from "@/components/settings";

export const metadata: Metadata = { title: "Settings · Corvetra" };

export default function SettingsRoute() {
    return <AppShell><Suspense fallback={<SettingsPageSkeleton />}><SettingsPage /></Suspense></AppShell>;
}
