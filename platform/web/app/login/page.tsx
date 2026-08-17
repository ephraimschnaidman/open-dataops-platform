"use client";

import { FormEvent, useState } from "react";
import { CircleGauge, LoaderCircle } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";

export default function LoginPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setSubmitting(true);
        setError(null);
        const form = new FormData(event.currentTarget);
        form.set("returnTo", searchParams.get("returnTo") ?? "/");
        try {
            const response = await fetch("/api/auth/token", { method: "POST", body: form });
            const result = await response.json() as { error?: string; returnTo?: string };
            if (!response.ok) {
                setError(result.error ?? "Unable to sign in.");
                return;
            }
            router.replace(result.returnTo ?? "/");
            router.refresh();
        } catch {
            setError("Authentication service is unavailable.");
        } finally {
            setSubmitting(false);
        }
    }

    return <main className="grid min-h-screen place-items-center bg-[#f7f8fa] p-4">
        <section className="animate-enter w-full max-w-sm rounded-xl border border-zinc-200 bg-white p-6 shadow-panel sm:p-8">
            <div className="flex items-center gap-2.5"><span className="grid h-8 w-8 place-items-center rounded-md bg-zinc-900 text-white"><CircleGauge className="h-4 w-4" /></span><span className="text-base font-semibold tracking-[-0.02em]">Corvetra</span></div>
            <h1 className="mt-8 text-xl font-semibold tracking-tight text-zinc-950">Sign in</h1>
            <p className="mt-1.5 text-sm text-zinc-500">Use your Corvetra platform credentials.</p>
            <form className="mt-6 space-y-4" onSubmit={submit}>
                <div><label className="text-xs font-medium text-zinc-700" htmlFor="username">Username</label><input autoComplete="username" autoFocus required id="username" name="username" className="mt-1.5 h-10 w-full rounded-md border border-zinc-200 bg-white px-3 text-sm text-zinc-900 shadow-sm outline-none transition focus:border-indigo-500" /></div>
                <div><label className="text-xs font-medium text-zinc-700" htmlFor="password">Password</label><input autoComplete="current-password" required id="password" name="password" type="password" className="mt-1.5 h-10 w-full rounded-md border border-zinc-200 bg-white px-3 text-sm text-zinc-900 shadow-sm outline-none transition focus:border-indigo-500" /></div>
                {error && <p role="alert" className="rounded-md border border-rose-100 bg-rose-50 px-3 py-2 text-xs text-rose-700">{error}</p>}
                <button disabled={submitting} className="flex h-10 w-full items-center justify-center gap-2 rounded-md bg-zinc-900 px-4 text-sm font-medium text-white shadow-sm transition hover:bg-zinc-800 disabled:cursor-wait disabled:opacity-70">{submitting && <LoaderCircle className="h-4 w-4 animate-spin" />}Sign in</button>
            </form>
        </section>
    </main>;
}
