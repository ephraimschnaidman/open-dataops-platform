import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { PipelineRunDetailPage } from "@/components/pipeline-run-detail";
import { getPipelineRunDetail, pipelineRunDetails } from "@/lib/pipeline-run-detail-data";
import PipelineRunNotFound from "./not-found";

interface PipelineRunDetailRouteProps {
    params: Promise<{ runId: string }>;
}

export function generateStaticParams() {
    return pipelineRunDetails.map((run) => ({ runId: run.id }));
}

export async function generateMetadata({ params }: PipelineRunDetailRouteProps): Promise<Metadata> {
    const { runId } = await params;
    const run = getPipelineRunDetail(runId);
    return { title: run ? `${run.pipelineName} · ${run.id} · Datum` : "Pipeline Run · Datum" };
}

export default async function PipelineRunDetailRoute({ params }: PipelineRunDetailRouteProps) {
    const { runId } = await params;
    const run = getPipelineRunDetail(runId);
    if (!run) return <PipelineRunNotFound />;
    return <AppShell><PipelineRunDetailPage initialRun={run} /></AppShell>;
}
