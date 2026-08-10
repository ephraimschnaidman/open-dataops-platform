import type { AlertSeverity, AlertWorkflowStatus } from "@/lib/alerts-data";

export function SeverityBadge({ severity }: { severity: AlertSeverity }) {
    const style = severity === "Critical" ? "bg-rose-50 text-rose-700 ring-rose-600/20" : "bg-amber-50 text-amber-700 ring-amber-600/20";
    return <span title="Severity" className={`inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[11px] font-medium ring-1 ring-inset ${style}`}><span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />{severity}</span>;
}

export function AlertStatusBadge({ status }: { status: AlertWorkflowStatus }) {
    const style = status === "Open" ? "bg-blue-50 text-blue-700 ring-blue-600/20" : status === "Acknowledged" ? "bg-indigo-50 text-indigo-700 ring-indigo-600/20" : "bg-zinc-100 text-zinc-600 ring-zinc-500/20";
    return <span title="Workflow status" className={`inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[11px] font-medium ring-1 ring-inset ${style}`}><span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />{status}</span>;
}
