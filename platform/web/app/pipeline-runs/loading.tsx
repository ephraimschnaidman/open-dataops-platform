import { AppShell } from "@/components/app-shell";
import { PipelineRunsSkeleton } from "@/components/pipeline-runs";

export default function Loading() {
    return <AppShell><PipelineRunsSkeleton /></AppShell>;
}
