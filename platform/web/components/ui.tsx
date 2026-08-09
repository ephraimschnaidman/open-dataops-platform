import { AlertTriangle, Check, LoaderCircle, RotateCw } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function PageHeader({ title, description, eyebrow, action }: { title: string; description: string; eyebrow?: ReactNode; action?: ReactNode }) {
    return <div className="mb-7 flex items-end justify-between gap-4"><div>{eyebrow && <div className="mb-1.5 flex items-center gap-2 text-[11px] font-medium text-zinc-400">{eyebrow}</div>}<h1 className="text-2xl font-semibold tracking-[-0.035em] text-zinc-950">{title}</h1><p className="mt-1 text-sm text-zinc-500">{description}</p></div>{action}</div>;
}

export function MetricCard({ label, value, detail, icon: Icon, tone = "neutral" }: { label: string; value: string; detail: string; icon: LucideIcon; tone?: "neutral" | "positive" | "warning" | "danger" }) {
    const iconTone = tone === "warning" ? "bg-amber-50 text-amber-600" : tone === "danger" ? "bg-rose-50 text-rose-600" : tone === "positive" ? "bg-emerald-50 text-emerald-600" : "bg-zinc-100 text-zinc-500";
    const detailTone = tone === "warning" ? "text-amber-700" : tone === "danger" ? "text-rose-700" : "text-zinc-500";
    return <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-card"><div className="flex items-center justify-between"><p className="text-xs font-medium text-zinc-500">{label}</p><span className={`grid h-7 w-7 place-items-center rounded-md ${iconTone}`}><Icon className="h-3.5 w-3.5" /></span></div><p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-zinc-950">{value}</p><p className={`mt-1 text-[11px] ${detailTone}`}>{detail}</p></div>;
}

export function Section({ title, description, action, children, className = "" }: { title: string; description?: string; action?: ReactNode; children: ReactNode; className?: string }) {
    return (
        <section className={className}>
            <div className="mb-3 flex items-end justify-between gap-4">
                <div>
                    <h2 className="text-[15px] font-semibold tracking-[-0.01em] text-zinc-900">{title}</h2>
                    {description && <p className="mt-0.5 text-xs text-zinc-500">{description}</p>}
                </div>
                {action}
            </div>
            {children}
        </section>
    );
}

const badgeStyles = {
    Success: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
    Running: "bg-blue-50 text-blue-700 ring-blue-600/20",
    Failed: "bg-rose-50 text-rose-700 ring-rose-600/20",
    Critical: "bg-rose-50 text-rose-700 ring-rose-600/20",
    Warning: "bg-amber-50 text-amber-700 ring-amber-600/20",
    Healthy: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
    Disconnected: "bg-rose-50 text-rose-700 ring-rose-600/20",
    Disabled: "bg-zinc-100 text-zinc-600 ring-zinc-500/20",
};

export function StatusBadge({ status }: { status: keyof typeof badgeStyles }) {
    return (
        <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[11px] font-medium ring-1 ring-inset ${badgeStyles[status]}`}>
            {status === "Running" ? <LoaderCircle className="h-3 w-3 animate-spin" /> : <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />}
            {status}
        </span>
    );
}

export function Skeleton({ className = "h-4 w-full" }: { className?: string }) {
    return <div className={`relative overflow-hidden rounded bg-zinc-100 ${className}`}><span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/70 to-transparent animate-[shimmer_1.4s_infinite]" /></div>;
}

export function EmptyState({ title = "Everything looks healthy.", description = "No pipelines, validations, or sources currently require attention.", icon, action }: { title?: string; description?: string; icon?: ReactNode; action?: ReactNode }) {
    return <div className="flex min-h-44 flex-col items-center justify-center rounded-lg border border-dashed border-zinc-200 bg-white p-6 text-center"><span className="mb-3 grid h-9 w-9 place-items-center rounded-full bg-emerald-50 text-emerald-600">{icon ?? <Check className="h-4 w-4" />}</span><p className="text-sm font-medium text-zinc-900">{title}</p><p className="mt-1 max-w-sm text-xs leading-5 text-zinc-500">{description}</p>{action && <div className="mt-3">{action}</div>}</div>;
}

export function ErrorState({ onRetry, title = "Unable to load recent pipeline runs.", description = "Something went wrong while fetching the latest activity." }: { onRetry?: () => void; title?: string; description?: string }) {
    return <div className="flex min-h-44 flex-col items-center justify-center rounded-lg border border-zinc-200 bg-white p-6 text-center"><AlertTriangle className="mb-3 h-5 w-5 text-amber-500" /><p className="text-sm font-medium text-zinc-900">{title}</p><p className="mt-1 text-xs text-zinc-500">{description}</p>{onRetry && <button onClick={onRetry} className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-zinc-200 px-2.5 py-1.5 text-xs font-medium hover:bg-zinc-50"><RotateCw className="h-3 w-3" /> Retry</button>}</div>;
}
