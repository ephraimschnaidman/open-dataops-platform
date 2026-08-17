"use client";

import { useEffect, useRef, useState } from "react";
import { apiRequest, ApiError, type ApiQueryValue } from "@/lib/api-client";

export interface ApiQueryState<T> {
    data: T | null;
    error: ApiError | null;
    loading: boolean;
    retry: () => void;
}

export function useApiQuery<T>(path: string | null, query?: Record<string, ApiQueryValue>, debounceMs = 0): ApiQueryState<T> {
    const [data, setData] = useState<T | null>(null);
    const [error, setError] = useState<ApiError | null>(null);
    const [loading, setLoading] = useState(true);
    const [attempt, setAttempt] = useState(0);
    const requestNumber = useRef(0);
    const queryKey = JSON.stringify(query ?? {});

    useEffect(() => {
        if (!path) {
            setLoading(false);
            setData(null);
            setError(null);
            return;
        }
        const controller = new AbortController();
        const currentRequest = ++requestNumber.current;
        const timer = window.setTimeout(async () => {
            setLoading(true);
            setError(null);
            try {
                const result = await apiRequest<T>(path, { query, signal: controller.signal });
                if (currentRequest === requestNumber.current) setData(result);
            } catch (caught) {
                if (currentRequest !== requestNumber.current) return;
                if (caught instanceof ApiError && caught.kind === "cancelled") return;
                setError(caught instanceof ApiError ? caught : new ApiError({ kind: "unexpected", status: null, code: "UNEXPECTED_API_ERROR", message: "The request failed.", retryable: true }));
                setData(null);
            } finally {
                if (currentRequest === requestNumber.current) setLoading(false);
            }
        }, debounceMs);
        return () => { window.clearTimeout(timer); controller.abort(); };
        // queryKey is the stable request identity; query is reconstructed by callers.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [path, queryKey, debounceMs, attempt]);

    return { data, error, loading, retry: () => setAttempt((value) => value + 1) };
}
