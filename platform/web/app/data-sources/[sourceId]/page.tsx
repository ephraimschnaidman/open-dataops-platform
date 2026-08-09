import type { Metadata } from "next";
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
    return <AppShell><DataSourceDetailPage source={source} /></AppShell>;
}
