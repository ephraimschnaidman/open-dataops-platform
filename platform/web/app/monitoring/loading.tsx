import { AppShell } from "@/components/app-shell";
import { MonitoringSkeleton } from "@/components/monitoring";

export default function Loading() {
    return <AppShell><MonitoringSkeleton /></AppShell>;
}
