export function withReturnTo(destination: string, returnTo: string) {
    const separator = destination.includes("?") ? "&" : "?";
    return `${destination}${separator}${new URLSearchParams({ returnTo }).toString()}`;
}

export function safeInternalReturnTo(value: string | null, allowedPath: string, fallback = allowedPath) {
    if (!value || typeof window === "undefined") return fallback;
    try {
        const target = new URL(value, window.location.origin);
        return target.origin === window.location.origin && target.pathname === allowedPath
            ? `${target.pathname}${target.search}`
            : fallback;
    } catch {
        return fallback;
    }
}
