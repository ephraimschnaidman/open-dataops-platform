import type { ValidationResult, ValidationSeverity } from "@/lib/validation-data";

export function ValidationResultBadge({ result }: { result: ValidationResult }) {
    const tone = result === "Passed" ? "bg-emerald-50 text-emerald-700 ring-emerald-600/20" : result === "Failed" ? "bg-rose-50 text-rose-700 ring-rose-600/20" : "bg-zinc-100 text-zinc-600 ring-zinc-500/20";
    return <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[11px] font-medium ring-1 ring-inset ${tone}`}><span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />{result}</span>;
}

export function ValidationSeverityBadge({ severity }: { severity: ValidationSeverity }) {
    const tone = severity === "Blocking" ? "bg-rose-50 text-rose-700 ring-rose-600/20" : "bg-amber-50 text-amber-700 ring-amber-600/20";
    return <span className={`inline-flex rounded-full px-2 py-1 text-[11px] font-semibold uppercase tracking-wide ring-1 ring-inset ${tone}`}>{severity}</span>;
}

export function ActualExpectedComparison({ actual, expected, result }: { actual: string; expected: string; result: ValidationResult }) {
    return <div className="grid grid-cols-2 overflow-hidden rounded-lg border border-zinc-200 bg-white"><div className="border-r border-zinc-200 p-4"><p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Expected</p><p className="mt-2 text-lg font-semibold text-zinc-900">{expected}</p></div><div className={`p-4 ${result === "Failed" ? "bg-rose-50/50" : result === "Passed" ? "bg-emerald-50/40" : "bg-zinc-50"}`}><p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Actual</p><p className={`mt-2 text-lg font-semibold ${result === "Failed" ? "text-rose-800" : result === "Passed" ? "text-emerald-800" : "text-zinc-600"}`}>{actual}</p></div></div>;
}
