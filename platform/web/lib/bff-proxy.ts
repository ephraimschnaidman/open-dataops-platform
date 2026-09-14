const ALLOWED_RESOURCES = new Set([
    "alerts", "dashboard", "data-sources", "health-metrics", "logs",
    "monitoring", "pipeline-runs", "pipelines", "settings", "validation",
]);

export function buildBackendApiUrl(baseUrl: string, path: readonly string[], search: string): URL | null {
    if (!path.length || !ALLOWED_RESOURCES.has(path[0]) || path.some((segment) => !segment || segment === "." || segment === "..")) return null;
    const url = new URL(`/api/v1/${path.map(encodeURIComponent).join("/")}`, baseUrl);
    url.search = search;
    return url;
}

export async function proxyBackendGet(
    url: URL,
    token: string,
    signal?: AbortSignal,
    fetcher: typeof fetch = fetch,
): Promise<Response> {
    const response = await fetcher(url, {
        method: "GET",
        headers: { authorization: `Bearer ${token}`, accept: "application/json" },
        cache: "no-store",
        signal,
    });
    const body = await response.text();
    return new Response(body || null, { status: response.status, headers: { "content-type": "application/json" } });
}

export async function proxyBackendMutation(
    url: URL,
    token: string,
    method: "POST" | "PUT" | "DELETE",
    body: string | null,
    signal?: AbortSignal,
    fetcher: typeof fetch = fetch,
): Promise<Response> {
    const response = await fetcher(url, {
        method,
        headers: { authorization: `Bearer ${token}`, accept: "application/json", ...(body === null ? {} : { "content-type": "application/json" }) },
        body,
        cache: "no-store",
        signal,
    });
    const responseBody = await response.text();
    return new Response(responseBody || null, { status: response.status, headers: responseBody ? { "content-type": "application/json" } : undefined });
}
