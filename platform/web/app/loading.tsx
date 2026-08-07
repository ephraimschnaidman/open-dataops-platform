import { AppShell } from "@/components/app-shell";
import { DashboardSkeleton } from "@/components/dashboard";

export default function Loading() {
    return (
        <AppShell>
            <DashboardSkeleton />
        </AppShell>
    );
}
