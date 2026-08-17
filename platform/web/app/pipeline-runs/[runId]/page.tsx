import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { PipelineRunDetailPage } from "@/components/pipeline-run-detail";
interface Props{params:Promise<{runId:string}>}
export async function generateMetadata({params}:Props):Promise<Metadata>{const{runId}=await params;return{title:`${runId} · Pipeline Runs · Corvetra`}}
export default async function Route({params}:Props){const{runId}=await params;return <AppShell><PipelineRunDetailPage runId={runId}/></AppShell>}
