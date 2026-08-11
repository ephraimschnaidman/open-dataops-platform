import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { DataSourceDetailPage } from "@/components/data-source-detail";
import { dataSourceDetails, getDataSourceDetail } from "@/lib/data-source-detail-data";

interface DetailPageProps {
    params: Promise<{ sourceId: string }>;
}

export function generateStaticParams() {
    return dataSourceDetails.map((source) => ({ sourceId: source.id }));
}

export async function generateMetadata({ params }: DetailPageProps): Promise<Metadata> {
    const { sourceId } = await params;
    const source = getDataSourceDetail(sourceId);
    return { title: source ? `${source.name} · Data Sources · Datum` : "Data Source · Datum" };
}

export default async function DataSourceDetailRoute({ params }: DetailPageProps) {
    const { sourceId } = await params;
    const source = getDataSourceDetail(sourceId);
    if (!source) notFound();
    const healthContext = new URLSearchParams({ resourceType: "Data Sources", resource: source.id, environment: source.environment });
    return <AppShell><div className="mb-3 flex justify-end"><Link href={`/health-metrics?${healthContext.toString()}`} className="inline-flex h-8 items-center rounded-md border border-zinc-200 bg-white px-2.5 text-xs font-medium text-zinc-700 shadow-card hover:bg-zinc-50">View Health Metrics</Link></div><DataSourceDetailPage source={source} /></AppShell>;
}
