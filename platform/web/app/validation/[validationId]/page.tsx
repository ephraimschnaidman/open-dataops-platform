import type { Metadata } from "next";
import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import { ValidationDetailPage,ValidationDetailSkeleton } from "@/components/validation-detail";
interface Props{params:Promise<{validationId:string}>}
export async function generateMetadata({params}:Props):Promise<Metadata>{const{validationId}=await params;return{title:`${validationId} · Validation · Corvetra`}}
export default async function Route({params}:Props){const{validationId}=await params;return <AppShell><Suspense fallback={<ValidationDetailSkeleton/>}><ValidationDetailPage checkKey={validationId}/></Suspense></AppShell>}
