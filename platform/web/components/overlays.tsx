"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { CheckCircle2, Info, X } from "lucide-react";
import { Button } from "@/components/ui";

export interface MenuItem {
    label: string;
    onSelect: () => void;
    disabled?: boolean;
    tone?: "default" | "danger";
}

export function DropdownMenu({ open, onOpenChange, items, children, align = "right" }: { open: boolean; onOpenChange: (open: boolean) => void; items: MenuItem[]; children: ReactNode; align?: "left" | "right" }) {
    const ref = useRef<HTMLDivElement>(null);
    useEffect(() => { if (!open) return; const close = (event: MouseEvent) => { if (!ref.current?.contains(event.target as Node)) onOpenChange(false); }; const key = (event: KeyboardEvent) => { if (event.key === "Escape") onOpenChange(false); }; document.addEventListener("mousedown", close); document.addEventListener("keydown", key); return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", key); }; }, [open, onOpenChange]);
    return <div ref={ref} className="relative inline-flex">{children}{open && <div className={`animate-enter absolute top-8 z-30 w-44 rounded-lg border border-zinc-200 bg-white p-1.5 text-xs shadow-panel ${align === "right" ? "right-0" : "left-0"}`}>{items.map((item) => <button key={item.label} disabled={item.disabled} onClick={() => { item.onSelect(); onOpenChange(false); }} className={`flex w-full rounded-md px-2.5 py-2 text-left transition disabled:cursor-not-allowed disabled:opacity-40 ${item.tone === "danger" ? "text-rose-700 hover:bg-rose-50" : "text-zinc-700 hover:bg-zinc-50"}`}>{item.label}</button>)}</div>}</div>;
}

export function ConfirmationDialog({ open, title, description, confirmLabel, onCancel, onConfirm, confirmVariant = "primary", supportingText }: { open: boolean; title: string; description: string; confirmLabel: string; onCancel: () => void; onConfirm: () => void; confirmVariant?: "primary" | "danger"; supportingText?: string }) {
    useEffect(() => { if (!open) return; const key = (event: KeyboardEvent) => { if (event.key === "Escape") onCancel(); }; document.addEventListener("keydown", key); return () => document.removeEventListener("keydown", key); }, [open, onCancel]);
    if (!open) return null;
    return <div role="presentation" className="fixed inset-0 z-50 grid place-items-center bg-zinc-950/30 p-4 backdrop-blur-[2px]" onMouseDown={(event) => { if (event.target === event.currentTarget) onCancel(); }}><div role="dialog" aria-modal="true" aria-labelledby="confirmation-title" className="animate-enter w-full max-w-sm rounded-xl border border-zinc-200 bg-white p-5 shadow-panel"><h2 id="confirmation-title" className="text-base font-semibold tracking-[-0.02em] text-zinc-900">{title}</h2><p className="mt-2 text-sm leading-6 text-zinc-500">{description}</p>{supportingText && <p className="mt-2 text-xs leading-5 text-zinc-400">{supportingText}</p>}<div className="mt-5 flex justify-end gap-2"><Button onClick={onCancel}>Cancel</Button><Button variant={confirmVariant} onClick={onConfirm}>{confirmLabel}</Button></div></div></div>;
}

export function Toast({ message, onClose, action, tone = "success" }: { message: string; onClose: () => void; action?: { label: string; onSelect: () => void }; tone?: "success" | "neutral" }) {
    const Icon = tone === "success" ? CheckCircle2 : Info;
    return <div role="status" className="fixed bottom-5 right-5 z-50 flex max-w-sm items-center gap-3 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2.5 text-xs text-white shadow-panel"><Icon className={`h-4 w-4 shrink-0 ${tone === "success" ? "text-emerald-400" : "text-zinc-300"}`} /><span className="font-medium">{message}</span>{action && <button onClick={action.onSelect} className="ml-1 whitespace-nowrap font-semibold text-indigo-300 hover:text-indigo-200">{action.label}</button>}<button aria-label="Dismiss notification" onClick={onClose} className="ml-1 rounded p-0.5 text-zinc-400 hover:text-white"><X className="h-3.5 w-3.5" /></button></div>;
}
