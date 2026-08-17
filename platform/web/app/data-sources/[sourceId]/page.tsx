import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { DataSourceDetailPage } from "@/components/data-source-detail";

interface DetailPageProps { params: Promise<{ sourceId: string }> }

export async function generateMetadata({ params }: DetailPageProps): Promise<Metadata> {
    const { sourceId } = await params;
    return { title: `${sourceId} · Data Sources · Corvetra` };
}

export default async function DataSourceDetailRoute({ params }: DetailPageProps) {
    const { sourceId } = await params;
    return <AppShell><DataSourceDetailPage sourceKey={sourceId} /></AppShell>;
}
