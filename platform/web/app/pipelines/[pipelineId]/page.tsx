import type { Metadata } from "next";
import Link from "next/link";
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
    return { title: pipeline ? `${pipeline.name} · Pipelines · Datum` : "Pipeline · Datum" };
}

export default async function PipelineDetailRoute({ params }: PipelineDetailRouteProps) {
    const { pipelineId } = await params;
    const pipeline = getPipelineDetail(pipelineId);
    if (!pipeline) notFound();
    const healthContext = new URLSearchParams({ resourceType: "Pipelines", resource: pipeline.id, environment: pipeline.environment });
    return <AppShell><div className="mb-3 flex justify-end"><Link href={`/health-metrics?${healthContext.toString()}`} className="inline-flex h-8 items-center rounded-md border border-zinc-200 bg-white px-2.5 text-xs font-medium text-zinc-700 shadow-card hover:bg-zinc-50">View Health Metrics</Link></div><PipelineDetailPage pipeline={pipeline} /></AppShell>;
}
