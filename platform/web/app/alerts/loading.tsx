import { AppShell } from "@/components/app-shell";
import { AlertsSkeleton } from "@/components/alerts";

export default function Loading() {
    return <AppShell><AlertsSkeleton /></AppShell>;
}
