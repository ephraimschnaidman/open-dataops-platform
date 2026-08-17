import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { AlertDetailPage } from "@/components/alert-detail";
interface Props{params:Promise<{alertId:string}>}
export async function generateMetadata({params}:Props):Promise<Metadata>{const{alertId}=await params;return{title:`${alertId} · Alerts · Corvetra`}}
export default async function Route({params}:Props){const{alertId}=await params;return <AppShell><AlertDetailPage alertKey={alertId}/></AppShell>}
