import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { PipelinesPage } from "@/components/pipelines";

export const metadata: Metadata = { title: "Pipelines · Datum" };

export default function Pipelines() {
    return <AppShell><PipelinesPage /></AppShell>;
}
