import { AppShell } from "@/components/app-shell";
import { PipelineDetailSkeleton } from "@/components/pipeline-detail";

export default function Loading() {
    return <AppShell><PipelineDetailSkeleton /></AppShell>;
}
