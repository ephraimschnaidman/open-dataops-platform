import { AppShell } from "@/components/app-shell";
import { DataSourceDetailSkeleton } from "@/components/data-source-detail";

export default function Loading() {
    return <AppShell><DataSourceDetailSkeleton /></AppShell>;
}
