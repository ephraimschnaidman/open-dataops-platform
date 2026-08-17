import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import {
    authenticateWithBackend,
    authCookieOptions,
    isBackendTokenResponse,
    safeReturnTo,
} from "../lib/auth-core.ts";
import { buildBackendApiUrl, proxyBackendGet } from "../lib/bff-proxy.ts";
import { apiRequest, ApiError, buildApiUrl, normalizeApiError } from "../lib/api-client.ts";
import { isPublicPage, shouldRedirectToLogin } from "../lib/route-access.ts";

test("login uses form encoding and accepts the committed token contract", async () => {
    process.env.CORVETRA_API_BASE_URL = "http://api:8000";
    let captured: Request | undefined;
    const fetcher: typeof fetch = async (input, init) => {
        captured = new Request(input, init);
        return Response.json({ access_token: "server-secret", token_type: "bearer", expires_in: 1800 });
    };
    const response = await authenticateWithBackend("owner", "not-persisted", fetcher);
    assert.equal(captured?.url, "http://api:8000/api/v1/auth/token");
    assert.equal(captured?.headers.get("content-type"), "application/x-www-form-urlencoded");
    assert.equal(await captured?.text(), "username=owner&password=not-persisted");
    assert.equal(isBackendTokenResponse(await response.json()), true);
});

test("invalid token payload is rejected and cookie attributes follow expires_in", () => {
    assert.equal(isBackendTokenResponse({ access_token: "x", token_type: "bearer", expires_in: 0 }), false);
    const options = authCookieOptions(1799.9);
    assert.equal(options.httpOnly, true);
    assert.equal(options.sameSite, "lax");
    assert.equal(options.maxAge, 1799);
    assert.equal(options.path, "/");
    const previousNodeEnv = process.env.NODE_ENV;
    Reflect.set(process.env, "NODE_ENV", "production");
    assert.equal(authCookieOptions(60).secure, true);
    if (previousNodeEnv === undefined) Reflect.deleteProperty(process.env, "NODE_ENV");
    else Reflect.set(process.env, "NODE_ENV", previousNodeEnv);
});

test("returnTo accepts internal paths and rejects open redirects", () => {
    assert.equal(safeReturnTo("/pipelines?id=1"), "/pipelines?id=1");
    for (const unsafe of ["https://evil.example", "//evil.example", "/\\evil", "javascript:alert(1)", null]) {
        assert.equal(safeReturnTo(unsafe), "/");
    }
});

test("proxy attaches the bearer server-side, preserves query and response status/body", async () => {
    const url = buildBackendApiUrl("http://api:8000", ["pipeline-runs", "run/id"], "?limit=10&status=FAILED");
    assert.ok(url);
    assert.equal(url.href, "http://api:8000/api/v1/pipeline-runs/run%2Fid?limit=10&status=FAILED");
    let authorization: string | null = null;
    const response = await proxyBackendGet(url, "server-token", undefined, async (_input, init) => {
        authorization = new Headers(init?.headers).get("authorization");
        return Response.json({ detail: "preserved" }, { status: 422 });
    });
    assert.equal(authorization, "Bearer server-token");
    assert.equal(response.status, 422);
    assert.deepEqual(await response.json(), { detail: "preserved" });
    assert.equal(buildBackendApiUrl("http://api:8000", ["auth", "token"], ""), null);
});

test("proxy preserves authoritative backend status codes", async () => {
    const url = new URL("http://api:8000/api/v1/dashboard");
    for (const status of [401, 403, 404, 422, 503]) {
        const response = await proxyBackendGet(url, "secret", undefined, async () => Response.json({ detail: "error" }, { status }));
        assert.equal(response.status, status);
    }
});

test("route protection permits login/authenticated pages and redirects protected pages", () => {
    assert.equal(isPublicPage("/login"), true);
    assert.equal(shouldRedirectToLogin("/login", false), false);
    assert.equal(shouldRedirectToLogin("/pipelines", true), false);
    assert.equal(shouldRedirectToLogin("/pipelines", false), true);
});

test("API client builds same-origin query URLs and returns typed JSON", async () => {
    assert.equal(buildApiUrl("/api/v1/logs", { level: ["ERROR", "WARNING"], limit: 20 }), "/api/v1/logs?level=ERROR&level=WARNING&limit=20");
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => Response.json({ items: [1] });
    try {
        const result = await apiRequest<{ items: number[] }>("/api/v1/logs");
        assert.deepEqual(result, { items: [1] });
    } finally { globalThis.fetch = originalFetch; }
});

test("API client normalizes 401/403/404/422/503 without logging out on 403", async () => {
    const expected = new Map([[401, "authentication"], [403, "permission"], [404, "not_found"], [422, "validation"], [503, "unavailable"]]);
    for (const [status, kind] of expected) assert.equal(normalizeApiError(status).kind, kind);

    const originalFetch = globalThis.fetch;
    let unauthorizedCalls = 0;
    globalThis.fetch = async () => Response.json({ detail: "backend internals" }, { status: 401 });
    try {
        await assert.rejects(apiRequest("/api/v1/dashboard", { onUnauthorized: () => { unauthorizedCalls += 1; } }), (error: unknown) => error instanceof ApiError && error.code === "SESSION_EXPIRED");
        assert.equal(unauthorizedCalls, 1);
        globalThis.fetch = async () => Response.json({}, { status: 403 });
        await assert.rejects(apiRequest("/api/v1/dashboard", { onUnauthorized: () => { unauthorizedCalls += 1; } }), (error: unknown) => error instanceof ApiError && error.kind === "permission");
        assert.equal(unauthorizedCalls, 1);
    } finally { globalThis.fetch = originalFetch; }
});

test("API client forwards AbortSignal and normalizes cancellation", async () => {
    const originalFetch = globalThis.fetch;
    const controller = new AbortController();
    globalThis.fetch = async (_input, init) => new Promise((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    });
    const pending = apiRequest("/api/v1/dashboard", { signal: controller.signal });
    controller.abort();
    try {
        await assert.rejects(pending, (error: unknown) => error instanceof ApiError && error.kind === "cancelled");
    } finally { globalThis.fetch = originalFetch; }
});

test("security-sensitive values remain server-only", async () => {
    const root = fileURLToPath(new URL("..", import.meta.url));
    const [loginRoute, client, session, envExample] = await Promise.all([
        readFile(`${root}/app/api/auth/token/route.ts`, "utf8"),
        readFile(`${root}/lib/api-client.ts`, "utf8"),
        readFile(`${root}/lib/auth-core.ts`, "utf8"),
        readFile(`${root}/.env.example`, "utf8"),
    ]);
    assert.doesNotMatch(loginRoute, /access_token\s*:/);
    assert.doesNotMatch(`${client}\n${session}`, /localStorage|sessionStorage/);
    assert.match(session, /httpOnly:\s*true/);
    assert.match(session, /NODE_ENV === "production"/);
    assert.doesNotMatch(envExample, /NEXT_PUBLIC|JWT_SECRET|PASSWORD|access_token/);
});
