import { AlertTriangle, Check, LoaderCircle, RotateCw } from "lucide-react";
import type { ReactNode } from "react";

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

export function EmptyState({ title = "Everything looks healthy.", description = "No pipelines, validations, or sources currently require attention." }: { title?: string; description?: string }) {
    return <div className="flex min-h-44 flex-col items-center justify-center rounded-lg border border-dashed border-zinc-200 bg-white p-6 text-center"><span className="mb-3 grid h-9 w-9 place-items-center rounded-full bg-emerald-50 text-emerald-600"><Check className="h-4 w-4" /></span><p className="text-sm font-medium text-zinc-900">{title}</p><p className="mt-1 max-w-sm text-xs leading-5 text-zinc-500">{description}</p></div>;
}

export function ErrorState({ onRetry }: { onRetry?: () => void }) {
    return <div className="flex min-h-44 flex-col items-center justify-center rounded-lg border border-zinc-200 bg-white p-6 text-center"><AlertTriangle className="mb-3 h-5 w-5 text-amber-500" /><p className="text-sm font-medium text-zinc-900">Unable to load recent pipeline runs.</p><p className="mt-1 text-xs text-zinc-500">Something went wrong while fetching the latest activity.</p><button onClick={onRetry} className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-zinc-200 px-2.5 py-1.5 text-xs font-medium hover:bg-zinc-50"><RotateCw className="h-3 w-3" /> Retry</button></div>;
}
