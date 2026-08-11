import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import { ValidationPage, ValidationPageSkeleton } from "@/components/validation";

export const metadata: Metadata = { title: "Validation · Datum" };
export default function ValidationRoute() { return <AppShell><div className="mb-3 flex justify-end"><Link href="/health-metrics?time=7d" className="inline-flex h-8 items-center rounded-md border border-zinc-200 bg-white px-2.5 text-xs font-medium text-zinc-700 shadow-card hover:bg-zinc-50">View Health Metrics</Link></div><Suspense fallback={<ValidationPageSkeleton />}><ValidationPage /></Suspense></AppShell>; }
