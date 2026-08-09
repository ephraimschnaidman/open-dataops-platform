import { AppShell } from "@/components/app-shell";
import { DataSourcesSkeleton } from "@/components/data-sources";

export default function Loading() {
    return <AppShell><DataSourcesSkeleton /></AppShell>;
}
