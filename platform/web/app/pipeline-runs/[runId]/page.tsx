import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { PipelineRunDetailPage } from "@/components/pipeline-run-detail";
import { getPipelineRunDetail, pipelineRunDetails } from "@/lib/pipeline-run-detail-data";

interface PipelineRunDetailRouteProps {
    params: Promise<{ runId: string }>;
}

export const dynamicParams = false;

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
    if (!run) notFound();
    return <AppShell><PipelineRunDetailPage initialRun={run} /></AppShell>;
}
