import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { AlertDetailPage } from "@/components/alert-detail";
import { alerts, getAlert } from "@/lib/alerts-data";

interface AlertDetailRouteProps { params: Promise<{ alertId: string }> }

export function generateStaticParams() {
    return alerts.map((alert) => ({ alertId: alert.id }));
}

export async function generateMetadata({ params }: AlertDetailRouteProps): Promise<Metadata> {
    const { alertId } = await params;
    const alert = getAlert(alertId);
    return { title: alert ? `${alert.id} · ${alert.title} · Corvetra` : "Alert · Corvetra" };
}

export default async function AlertDetailRoute({ params }: AlertDetailRouteProps) {
    const { alertId } = await params;
    const alert = getAlert(alertId);
    if (!alert) notFound();
    return <AppShell><AlertDetailPage initialAlert={alert} /></AppShell>;
}
