import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import { PipelineDetailPage } from "@/components/pipeline-detail";
interface Props{params:Promise<{pipelineId:string}>}
export async function generateMetadata({params}:Props):Promise<Metadata>{const{pipelineId}=await params;return{title:`${pipelineId} · Pipelines · Corvetra`}}
export default async function Route({params}:Props){const{pipelineId}=await params;return <AppShell><PipelineDetailPage pipelineKey={pipelineId}/></AppShell>}
