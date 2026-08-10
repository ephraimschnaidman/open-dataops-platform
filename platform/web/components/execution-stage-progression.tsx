import { Check, Circle, CircleX, LoaderCircle, Minus } from "lucide-react";
import type { ExecutionStage, ExecutionStageState } from "@/lib/pipeline-run-detail-data";

const stageTone: Record<ExecutionStageState, { border: string; icon: string; label: string }> = {
    Completed: { border: "border-emerald-200", icon: "bg-emerald-100 text-emerald-700", label: "text-emerald-700" },
    Running: { border: "border-blue-200", icon: "bg-blue-100 text-blue-700", label: "text-blue-700" },
    Failed: { border: "border-rose-200", icon: "bg-rose-100 text-rose-700", label: "text-rose-700" },
    Pending: { border: "border-zinc-200", icon: "bg-zinc-100 text-zinc-400", label: "text-zinc-500" },
    Cancelled: { border: "border-zinc-300", icon: "bg-zinc-200 text-zinc-600", label: "text-zinc-600" },
};

function StageIcon({ state }: { state: ExecutionStageState }) {
    if (state === "Completed") return <Check className="h-4 w-4" />;
    if (state === "Running") return <LoaderCircle className="h-4 w-4 animate-spin" />;
    if (state === "Failed") return <CircleX className="h-4 w-4" />;
    if (state === "Cancelled") return <Minus className="h-4 w-4" />;
    return <Circle className="h-3.5 w-3.5" />;
}

export function ExecutionStageProgression({ stages }: { stages: ExecutionStage[] }) {
    return <ol aria-label="Execution stages" className="grid gap-3 md:grid-cols-4">{stages.map((stage, index) => { const tone = stageTone[stage.state]; return <li key={`${stage.name}-${index}`} className={`relative rounded-lg border bg-white p-4 ${tone.border}`}><div className="flex items-center gap-2.5"><span className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${tone.icon}`}><StageIcon state={stage.state} /></span><div><p className="text-sm font-semibold text-zinc-900">{stage.name}</p><p className={`text-[11px] font-medium ${tone.label}`}>{stage.state === "Pending" ? "Not executed" : stage.state}</p></div></div><dl className="mt-4 space-y-2 text-xs"><div className="flex items-center justify-between gap-3"><dt className="text-zinc-500">Duration</dt><dd className="font-medium tabular-nums text-zinc-700">{stage.duration ?? "—"}</dd></div>{stage.recordDetail && <div><dt className="text-zinc-500">Records</dt><dd className="mt-0.5 font-medium text-zinc-700">{stage.recordDetail}</dd></div>}{stage.platformCode && <div className="border-t border-zinc-100 pt-2"><dt className="text-zinc-500">Platform Code</dt><dd className="mt-0.5 break-all font-mono text-[10px] font-medium text-zinc-800">{stage.platformCode}</dd></div>}{stage.vendorCode && <div><dt className="text-zinc-500">Vendor Code</dt><dd className="mt-0.5 break-all font-mono text-[10px] font-medium text-zinc-800">{stage.vendorCode}</dd></div>}</dl>{stage.message && <p className="mt-3 border-t border-zinc-100 pt-3 text-xs leading-5 text-zinc-600">{stage.message}</p>}</li>; })}</ol>;
}
