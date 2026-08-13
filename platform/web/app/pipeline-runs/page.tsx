import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { PipelineRunsPage } from "@/components/pipeline-runs";

export const metadata: Metadata = { title: "Pipeline Runs · Corvetra" };

export default function PipelineRunsRoute() {
    return <AppShell><PipelineRunsPage /></AppShell>;
}
