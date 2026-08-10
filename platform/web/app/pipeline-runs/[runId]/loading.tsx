import { AppShell } from "@/components/app-shell";
import { PipelineRunDetailSkeleton } from "@/components/pipeline-run-detail";

export default function Loading() {
    return <AppShell><PipelineRunDetailSkeleton /></AppShell>;
}
