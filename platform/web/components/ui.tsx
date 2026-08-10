import { AlertTriangle, Check, CircleAlert, LoaderCircle, RotateCw, Search, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { OperationalResult } from "@/lib/operational-status";
export type { OperationalResult, OperationalState } from "@/lib/operational-status";

export function Breadcrumbs({ items }: { items: Array<{ label: string; href?: string }> }) {
    return <nav aria-label="Breadcrumb" className="mb-4"><ol className="flex flex-wrap items-center gap-1.5 text-xs text-zinc-400">{items.map((item, index) => <li key={item.label} className="flex items-center gap-1.5">{index > 0 && <span aria-hidden="true" className="text-zinc-300">/</span>}{item.href ? <Link href={item.href} className="hover:text-zinc-700">{item.label}</Link> : <span aria-current="page" className="font-medium text-zinc-600">{item.label}</span>}</li>)}</ol></nav>;
}

export function Button({ variant = "secondary", className = "", children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger" }) {
    const styles = variant === "primary" ? "bg-zinc-900 text-white shadow-sm hover:bg-zinc-800" : variant === "danger" ? "bg-rose-600 text-white shadow-sm hover:bg-rose-700" : variant === "ghost" ? "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900" : "border border-zinc-200 bg-white text-zinc-700 shadow-card hover:bg-zinc-50";
    return <button className={`inline-flex h-9 items-center justify-center gap-1.5 rounded-md px-3 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`} {...props}>{children}</button>;
}

export function SearchField({ value, onChange, placeholder, className = "" }: { value: string; onChange: (value: string) => void; placeholder: string; className?: string }) {
    return <div className={`relative w-full ${className}`}><Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" /><input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} aria-label={placeholder} className="h-9 w-full rounded-md border border-zinc-200 bg-white pl-8 pr-8 text-xs text-zinc-800 shadow-card outline-none placeholder:text-zinc-400 hover:border-zinc-300" />{value && <button aria-label="Clear search" onClick={() => onChange("")} className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-zinc-400 hover:text-zinc-700"><X className="h-3.5 w-3.5" /></button>}</div>;
}

export function FilterSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: Array<{ label: string; value: string }> }) {
    return <select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)} className="h-9 rounded-md border border-zinc-200 bg-white px-2.5 text-xs text-zinc-600 shadow-card outline-none hover:border-zinc-300">{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>;
}

export function Card({ title, description, action, children, className = "" }: { title?: string; description?: string; action?: ReactNode; children: ReactNode; className?: string }) {
    return <div className={`rounded-lg border border-zinc-200 bg-white shadow-card ${className}`}>{(title || description || action) && <div className="flex items-start justify-between gap-4 border-b border-zinc-100 px-4 py-3.5"><div>{title && <h2 className="text-[15px] font-semibold tracking-[-0.01em] text-zinc-900">{title}</h2>}{description && <p className="mt-0.5 text-xs text-zinc-500">{description}</p>}</div>{action}</div>}{children}</div>;
}

export function OperationalStatus({ result, statusLabel, details, action }: { result: OperationalResult; statusLabel?: "Success" | "Healthy" | "Warning" | "Critical" | "Failed" | "Running" | "Cancelled" | "Disabled"; details?: Array<{ label: string; value: string }>; action?: ReactNode }) {
    const tone = result.status === "Success" ? { box: "border-emerald-100 bg-emerald-50/60", icon: "bg-emerald-100 text-emerald-700", action: "text-emerald-800" } : result.status === "Warning" ? { box: "border-amber-100 bg-amber-50/60", icon: "bg-amber-100 text-amber-700", action: "text-amber-800" } : result.status === "Running" ? { box: "border-blue-100 bg-blue-50/60", icon: "bg-blue-100 text-blue-700", action: "text-blue-800" } : result.status === "Neutral" ? { box: "border-zinc-200 bg-zinc-50", icon: "bg-zinc-200 text-zinc-600", action: "text-zinc-700" } : { box: "border-rose-100 bg-rose-50/60", icon: "bg-rose-100 text-rose-700", action: "text-rose-800" };
    const badgeStatus = statusLabel ?? (result.status === "Neutral" ? "Disabled" : result.status);
    return <div className={`rounded-lg border p-4 ${tone.box}`}><div className="flex items-start gap-3"><span className={`mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full ${tone.icon}`}>{result.status === "Success" ? <Check className="h-4 w-4" /> : result.status === "Running" ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <CircleAlert className="h-4 w-4" />}</span><div className="min-w-0 flex-1"><p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Status</p><StatusBadge status={badgeStatus} /><p className="mt-2 text-sm font-medium leading-5 text-zinc-900">{result.message}</p><dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2"><div><dt className="text-zinc-500">Platform Code</dt><dd className="mt-0.5 font-mono font-medium text-zinc-800">{result.platformCode}</dd></div>{result.vendorCode && <div><dt className="text-zinc-500">Vendor Code</dt><dd className="mt-0.5 font-mono font-medium text-zinc-800">{result.vendorCode}</dd></div>}</dl>{details && <dl className="mt-3 grid gap-x-4 gap-y-2 border-t border-current/10 pt-3 text-xs sm:grid-cols-2">{details.map((detail) => <div key={detail.label}><dt className="text-zinc-500">{detail.label}</dt><dd className="mt-0.5 font-medium text-zinc-800">{detail.value}</dd></div>)}</dl>}<div className="mt-3 border-t border-current/10 pt-3"><p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Recommended Action</p><p className={`mt-1 text-xs leading-5 ${tone.action}`}>{result.recommendedAction}</p>{action && <div className="mt-3 flex flex-wrap gap-2">{action}</div>}</div></div></div></div>;
}

export function TechnicalDetails({ items, className = "" }: { items: Array<{ label: string; value: string }>; className?: string }) {
    return <dl className={`grid gap-2 text-xs sm:grid-cols-2 ${className}`}>{items.map((item) => <div key={item.label}><dt className="text-zinc-500">{item.label}</dt><dd className="mt-0.5 font-mono font-medium text-zinc-800">{item.value}</dd></div>)}</dl>;
}

export function KeyValueGrid({ items }: { items: Array<{ label: string; value: string; mono?: boolean }> }) {
    return <dl className="grid sm:grid-cols-2">{items.map((item) => <div key={item.label} className="border-b border-zinc-100 px-4 py-3 last:border-b-0 sm:[&:nth-last-child(-n+2)]:border-b-0"><dt className="text-[11px] text-zinc-500">{item.label}</dt><dd className={`mt-1 truncate text-xs font-medium text-zinc-800 ${item.mono ? "font-mono" : ""}`} title={item.value}>{item.value}</dd></div>)}</dl>;
}

export function PageHeader({ title, description, eyebrow, action }: { title: string; description: string; eyebrow?: ReactNode; action?: ReactNode }) {
    return <div className="mb-7 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end"><div>{eyebrow && <div className="mb-1.5 flex items-center gap-2 text-[11px] font-medium text-zinc-400">{eyebrow}</div>}<h1 className="text-2xl font-semibold tracking-[-0.035em] text-zinc-950">{title}</h1><p className="mt-1 text-sm text-zinc-500">{description}</p></div>{action}</div>;
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
    Error: "bg-rose-50 text-rose-700 ring-rose-600/20",
    Cancelled: "bg-zinc-100 text-zinc-600 ring-zinc-500/20",
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

export function EmptyState({ title = "Everything looks healthy.", description = "No pipelines, validations, or sources currently require attention.", icon, action, tone = "positive" }: { title?: string; description?: string; icon?: ReactNode; action?: ReactNode; tone?: "positive" | "neutral" }) {
    const iconTone = tone === "neutral" ? "bg-zinc-100 text-zinc-500" : "bg-emerald-50 text-emerald-600";
    return <div className="flex min-h-44 flex-col items-center justify-center rounded-lg border border-dashed border-zinc-200 bg-white p-6 text-center"><span className={`mb-3 grid h-9 w-9 place-items-center rounded-full ${iconTone}`}>{icon ?? <Check className="h-4 w-4" />}</span><p className="text-sm font-medium text-zinc-900">{title}</p><p className="mt-1 max-w-sm text-xs leading-5 text-zinc-500">{description}</p>{action && <div className="mt-3">{action}</div>}</div>;
}

export function ErrorState({ onRetry, title = "Unable to load recent pipeline runs.", description = "Something went wrong while fetching the latest activity.", actionLabel = "Retry", technicalDetails }: { onRetry?: () => void; title?: string; description?: string; actionLabel?: string; technicalDetails?: Array<{ label: string; value: string }> }) {
    return <div className="flex min-h-44 flex-col items-center justify-center rounded-lg border border-zinc-200 bg-white p-6 text-center"><AlertTriangle className="mb-3 h-5 w-5 text-amber-500" /><p className="text-sm font-medium text-zinc-900">{title}</p><p className="mt-1 text-xs text-zinc-500">{description}</p>{technicalDetails && <TechnicalDetails items={technicalDetails} className="mt-4 w-full max-w-sm rounded-md bg-zinc-50 p-3 text-left" />}{onRetry && <button onClick={onRetry} className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-zinc-200 px-2.5 py-1.5 text-xs font-medium hover:bg-zinc-50"><RotateCw className="h-3 w-3" /> {actionLabel}</button>}</div>;
}
