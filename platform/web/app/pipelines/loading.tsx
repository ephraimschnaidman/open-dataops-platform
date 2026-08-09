import { AppShell } from "@/components/app-shell";
import { PipelinesSkeleton } from "@/components/pipelines";

export default function Loading() {
    return <AppShell><PipelinesSkeleton /></AppShell>;
}
