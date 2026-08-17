export const AUTH_COOKIE_NAME = "corvetra_access_token";

export interface BackendTokenResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
}

export function isSafeReturnTo(value: unknown): value is string {
    return typeof value === "string"
        && value.startsWith("/")
        && !value.startsWith("//")
        && !value.includes("\\")
        && !value.includes("\r")
        && !value.includes("\n");
}

export function safeReturnTo(value: unknown, fallback = "/"): string {
    return isSafeReturnTo(value) ? value : fallback;
}

export function authCookieOptions(expiresIn: number) {
    return {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax" as const,
        path: "/",
        maxAge: Math.max(1, Math.floor(expiresIn)),
    };
}

export function clearedAuthCookieOptions() {
    return { ...authCookieOptions(1), maxAge: 0, expires: new Date(0) };
}

export async function authenticateWithBackend(
    username: string,
    password: string,
    fetcher: typeof fetch = fetch,
): Promise<Response> {
    const baseUrl = process.env.CORVETRA_API_BASE_URL;
    if (!baseUrl) throw new Error("CORVETRA_API_BASE_URL is not configured");
    return fetcher(new URL("/api/v1/auth/token", baseUrl), {
        method: "POST",
        headers: { "content-type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username, password }),
        cache: "no-store",
    });
}

export function isBackendTokenResponse(value: unknown): value is BackendTokenResponse {
    if (!value || typeof value !== "object") return false;
    const token = value as Partial<BackendTokenResponse>;
    return typeof token.access_token === "string" && token.access_token.length > 0
        && typeof token.token_type === "string" && token.token_type.toLowerCase() === "bearer"
        && typeof token.expires_in === "number" && Number.isFinite(token.expires_in) && token.expires_in > 0;
}
