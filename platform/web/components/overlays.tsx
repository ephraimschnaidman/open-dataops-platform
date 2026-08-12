"use client";

import { useEffect, useId, useRef, useState, type ReactNode, type RefObject } from "react";
import { CheckCircle2, Info, X } from "lucide-react";
import { Button } from "@/components/ui";

export interface MenuItem {
    label: string;
    onSelect: () => void;
    disabled?: boolean;
    tone?: "default" | "danger";
}

const focusableSelector = 'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function useOverlayFocus(open: boolean, onClose: () => void, containerRef: RefObject<HTMLElement | null>, initialFocusRef?: RefObject<HTMLElement | null>) {
    const returnFocusRef = useRef<HTMLElement | null>(null);
    const closeRef = useRef(onClose); closeRef.current = onClose;
    useEffect(() => {
        if (!open) return;
        returnFocusRef.current = document.activeElement as HTMLElement | null;
        const frame = window.requestAnimationFrame(() => (initialFocusRef?.current ?? containerRef.current?.querySelector<HTMLElement>(focusableSelector))?.focus());
        const key = (event: KeyboardEvent) => {
            if (event.key === "Escape") { event.preventDefault(); closeRef.current(); return; }
            if (event.key !== "Tab" || !containerRef.current) return;
            const focusable = Array.from(containerRef.current.querySelectorAll<HTMLElement>(focusableSelector)).filter((element) => !element.hidden);
            if (!focusable.length) { event.preventDefault(); containerRef.current.focus(); return; }
            const first = focusable[0]; const last = focusable.at(-1)!;
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        };
        document.addEventListener("keydown", key);
        return () => { window.cancelAnimationFrame(frame); document.removeEventListener("keydown", key); returnFocusRef.current?.focus(); };
    }, [open, containerRef, initialFocusRef]);
}

export function DropdownMenu({ open: controlledOpen, onOpenChange, items, children, align = "right" }: { open?: boolean; onOpenChange?: (open: boolean) => void; items: MenuItem[]; children: ReactNode; align?: "left" | "right" }) {
    const [internalOpen, setInternalOpen] = useState(false);
    const open = controlledOpen ?? internalOpen;
    const changeOpen = onOpenChange ?? setInternalOpen;
    const ref = useRef<HTMLDivElement>(null);
    const triggerRef = useRef<HTMLElement | null>(null);
    useEffect(() => { if (!open) return; triggerRef.current = document.activeElement as HTMLElement; const menu = ref.current?.querySelector<HTMLElement>('[role="menu"]'); menu?.querySelector<HTMLElement>('[role="menuitem"]:not([disabled])')?.focus(); const close = (event: MouseEvent) => { if (!ref.current?.contains(event.target as Node)) changeOpen(false); }; const key = (event: KeyboardEvent) => { if (event.key === "Escape") { changeOpen(false); triggerRef.current?.focus(); } if ((event.key === "ArrowDown" || event.key === "ArrowUp") && menu) { event.preventDefault(); const enabled = Array.from(menu.querySelectorAll<HTMLElement>('[role="menuitem"]:not([disabled])')); const index = enabled.indexOf(document.activeElement as HTMLElement); enabled[(index + (event.key === "ArrowDown" ? 1 : -1) + enabled.length) % enabled.length]?.focus(); } }; document.addEventListener("mousedown", close); document.addEventListener("keydown", key); return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", key); }; }, [open, changeOpen]);
    return <div ref={ref} className="relative inline-flex" onClick={() => { if (!open) changeOpen(true); }}>{children}{open && <div role="menu" className={`animate-enter absolute top-8 z-30 w-44 max-w-[calc(100vw-2rem)] rounded-lg border border-zinc-200 bg-white p-1.5 text-xs shadow-panel ${align === "right" ? "right-0" : "left-0"}`}>{items.map((item) => <button role="menuitem" tabIndex={-1} key={item.label} disabled={item.disabled} onClick={() => { item.onSelect(); changeOpen(false); }} className={`flex w-full rounded-md px-2.5 py-2 text-left transition disabled:cursor-not-allowed disabled:opacity-40 ${item.tone === "danger" ? "text-rose-700 hover:bg-rose-50" : "text-zinc-700 hover:bg-zinc-50"}`}>{item.label}</button>)}</div>}</div>;
}

export function ConfirmationDialog({ open, title, description, confirmLabel, cancelLabel = "Cancel", onCancel, onConfirm, confirmVariant = "primary", supportingText, details }: { open: boolean; title: string; description: string; confirmLabel: string; cancelLabel?: string; onCancel: () => void; onConfirm: () => void; confirmVariant?: "primary" | "danger"; supportingText?: string; details?: Array<{ label: string; value: string }> }) {
    const dialogRef = useRef<HTMLDivElement>(null); const cancelRef = useRef<HTMLButtonElement>(null);
    const titleId = useId(); const descriptionId = useId();
    useOverlayFocus(open, onCancel, dialogRef, cancelRef);
    if (!open) return null;
    return <div role="presentation" className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-zinc-950/30 p-3 backdrop-blur-[2px] sm:p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) onCancel(); }}><div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={descriptionId} tabIndex={-1} className="animate-enter my-auto w-full max-w-sm rounded-xl border border-zinc-200 bg-white p-5 shadow-panel"><h2 id={titleId} className="text-base font-semibold tracking-[-0.02em] text-zinc-900">{title}</h2><p id={descriptionId} className="mt-2 text-sm leading-6 text-zinc-500">{description}</p>{supportingText && <p className="mt-2 text-xs leading-5 text-zinc-400">{supportingText}</p>}{details && <dl className="mt-4 grid gap-2 rounded-md bg-zinc-50 p-3 text-xs">{details.map((detail) => <div key={detail.label} className="grid min-w-0 grid-cols-[88px_1fr] gap-2"><dt className="text-zinc-500">{detail.label}</dt><dd className="truncate font-medium text-zinc-800" title={detail.value}>{detail.value}</dd></div>)}</dl>}<div className="mt-5 flex flex-wrap justify-end gap-2"><Button ref={cancelRef} onClick={onCancel}>{cancelLabel}</Button><Button variant={confirmVariant} onClick={onConfirm}>{confirmLabel}</Button></div></div></div>;
}

export function Toast({ message, onClose, action, tone = "success" }: { message: string; onClose: () => void; action?: { label: string; onSelect: () => void }; tone?: "success" | "neutral" }) {
    const Icon = tone === "success" ? CheckCircle2 : Info;
    return <div role="status" className="fixed bottom-5 right-5 z-50 flex max-w-sm items-center gap-3 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2.5 text-xs text-white shadow-panel"><Icon className={`h-4 w-4 shrink-0 ${tone === "success" ? "text-emerald-400" : "text-zinc-300"}`} /><span className="font-medium">{message}</span>{action && <button onClick={action.onSelect} className="ml-1 whitespace-nowrap font-semibold text-indigo-300 hover:text-indigo-200">{action.label}</button>}<button aria-label="Dismiss notification" onClick={onClose} className="ml-1 rounded p-0.5 text-zinc-400 hover:text-white"><X className="h-3.5 w-3.5" /></button></div>;
}
