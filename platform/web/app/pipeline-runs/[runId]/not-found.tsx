"use client";

import { useRouter } from "next/navigation";
import { Activity } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Button, EmptyState } from "@/components/ui";

export default function PipelineRunNotFound() {
    const router = useRouter();
    return <AppShell><EmptyState title="Pipeline run not found" description="We couldn't find the requested pipeline execution." icon={<Activity className="h-4 w-4" />} tone="neutral" action={<Button variant="primary" onClick={() => router.push("/pipeline-runs")}>Back to Pipeline Runs</Button>} /></AppShell>;
}
