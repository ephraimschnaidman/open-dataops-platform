"use client";

import { useRouter } from "next/navigation";
import { BellRing } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Button, EmptyState } from "@/components/ui";

export function AlertNotFound() {
    const router = useRouter();
    return <AppShell><EmptyState title="Alert not found" description="We couldn't find the requested operational alert." icon={<BellRing className="h-4 w-4" />} tone="neutral" action={<Button variant="primary" onClick={() => router.push("/alerts")}>Back to Alerts</Button>} /></AppShell>;
}

export default AlertNotFound;
