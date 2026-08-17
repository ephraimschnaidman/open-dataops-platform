export type ApiErrorKind = "authentication" | "permission" | "not_found" | "validation" | "unavailable" | "network" | "unexpected" | "cancelled";

export interface ApiErrorDetails {
    kind: ApiErrorKind;
    status: number | null;
    code: string;
    message: string;
    retryable: boolean;
}

export class ApiError extends Error {
    readonly kind: ApiErrorKind;
    readonly status: number | null;
    readonly code: string;
    readonly retryable: boolean;

    constructor(details: ApiErrorDetails) {
        super(details.message);
        this.name = "ApiError";
        this.kind = details.kind;
        this.status = details.status;
        this.code = details.code;
        this.retryable = details.retryable;
    }
}

export type ApiQueryValue = string | number | boolean | null | undefined | readonly (string | number | boolean)[];

export interface ApiRequestOptions {
    query?: Record<string, ApiQueryValue>;
    signal?: AbortSignal;
    onUnauthorized?: (returnTo: string) => void;
}

let redirectingToLogin = false;

export function buildApiUrl(path: string, query?: Record<string, ApiQueryValue>): string {
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    if (!normalizedPath.startsWith("/api/v1/") || normalizedPath.startsWith("//")) {
        throw new Error("API requests must use a same-origin /api/v1/ path");
    }
    const parameters = new URLSearchParams();
    for (const [key, rawValue] of Object.entries(query ?? {})) {
        if (rawValue == null) continue;
        const values = Array.isArray(rawValue) ? rawValue : [rawValue];
        for (const value of values) parameters.append(key, String(value));
    }
    const search = parameters.toString();
    return search ? `${normalizedPath}?${search}` : normalizedPath;
}

export function normalizeApiError(status: number, _body?: unknown): ApiError {
    if (status === 401) return new ApiError({ kind: "authentication", status, code: "SESSION_EXPIRED", message: "Your session has expired. Sign in again.", retryable: false });
    if (status === 403) return new ApiError({ kind: "permission", status, code: "PERMISSION_DENIED", message: "You do not have permission to perform this action.", retryable: false });
    if (status === 404) return new ApiError({ kind: "not_found", status, code: "RESOURCE_NOT_FOUND", message: "The requested resource was not found.", retryable: false });
    if (status === 422) return new ApiError({ kind: "validation", status, code: "REQUEST_INVALID", message: "The request contains invalid values.", retryable: false });
    if (status === 503) return new ApiError({ kind: "unavailable", status, code: "SERVICE_UNAVAILABLE", message: "The service is temporarily unavailable.", retryable: true });
    return new ApiError({ kind: "unexpected", status, code: "UNEXPECTED_API_ERROR", message: "An unexpected service error occurred.", retryable: status >= 500 });
}

function currentReturnTo(): string {
    if (typeof window === "undefined") return "/";
    return `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

function defaultUnauthorized(returnTo: string) {
    if (typeof window === "undefined" || redirectingToLogin || window.location.pathname === "/login") return;
    redirectingToLogin = true;
    window.location.assign(`/login?returnTo=${encodeURIComponent(returnTo)}`);
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
    let response: Response;
    try {
        response = await fetch(buildApiUrl(path, options.query), {
            method: "GET",
            headers: { accept: "application/json" },
            credentials: "same-origin",
            cache: "no-store",
            signal: options.signal,
        });
    } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
            throw new ApiError({ kind: "cancelled", status: null, code: "REQUEST_CANCELLED", message: "The request was cancelled.", retryable: false });
        }
        throw new ApiError({ kind: "network", status: null, code: "NETWORK_ERROR", message: "The service could not be reached.", retryable: true });
    }

    if (!response.ok) {
        let body: unknown;
        try { body = await response.json(); } catch { body = undefined; }
        const error = normalizeApiError(response.status, body);
        if (response.status === 401) (options.onUnauthorized ?? defaultUnauthorized)(currentReturnTo());
        throw error;
    }

    try {
        return await response.json() as T;
    } catch {
        throw new ApiError({ kind: "unexpected", status: response.status, code: "INVALID_API_RESPONSE", message: "The service returned an invalid response.", retryable: true });
    }
}
