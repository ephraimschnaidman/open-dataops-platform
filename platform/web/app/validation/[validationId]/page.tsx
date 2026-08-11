import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import { ValidationDetailPage, ValidationDetailSkeleton } from "@/components/validation-detail";
import { getValidationCheck, validationChecks } from "@/lib/validation-data";

interface Props { params: Promise<{ validationId: string }>; }
export function generateStaticParams() { return validationChecks.map((check) => ({ validationId: check.id })); }
export async function generateMetadata({ params }: Props): Promise<Metadata> { const check = getValidationCheck((await params).validationId); return { title: check ? `${check.name} · Validation · Datum` : "Validation · Datum" }; }
export default async function ValidationDetailRoute({ params }: Props) { const check = getValidationCheck((await params).validationId); if (!check) notFound(); return <AppShell><Suspense fallback={<ValidationDetailSkeleton />}><ValidationDetailPage check={check} /></Suspense></AppShell>; }
