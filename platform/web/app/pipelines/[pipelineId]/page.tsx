import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { PipelineDetailPage } from "@/components/pipeline-detail";
import { getPipelineDetail, pipelineDetails } from "@/lib/pipeline-detail-data";

interface PipelineDetailRouteProps {
    params: Promise<{ pipelineId: string }>;
}

export function generateStaticParams() {
    return pipelineDetails.map((pipeline) => ({ pipelineId: pipeline.id }));
}

export async function generateMetadata({ params }: PipelineDetailRouteProps): Promise<Metadata> {
    const { pipelineId } = await params;
    const pipeline = getPipelineDetail(pipelineId);
    return { title: pipeline ? `${pipeline.name} · Pipelines · Corvetra` : "Pipeline · Corvetra" };
}

export default async function PipelineDetailRoute({ params }: PipelineDetailRouteProps) {
    const { pipelineId } = await params;
    const pipeline = getPipelineDetail(pipelineId);
    if (!pipeline) notFound();
    return <AppShell><PipelineDetailPage pipeline={pipeline} /></AppShell>;
}
