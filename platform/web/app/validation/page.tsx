import type { Metadata } from "next";
import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import { ValidationPage, ValidationPageSkeleton } from "@/components/validation";

export const metadata: Metadata = { title: "Validation · Datum" };
export default function ValidationRoute() { return <AppShell><Suspense fallback={<ValidationPageSkeleton />}><ValidationPage /></Suspense></AppShell>; }
