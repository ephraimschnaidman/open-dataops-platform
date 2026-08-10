import { AppShell } from "@/components/app-shell";
import { AlertDetailSkeleton } from "@/components/alert-detail";

export default function Loading() {
    return <AppShell><AlertDetailSkeleton /></AppShell>;
}
