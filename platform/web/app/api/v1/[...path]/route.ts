import { NextRequest, NextResponse } from "next/server";
import { getAccessToken } from "@/lib/auth-session";
import { buildBackendApiUrl, proxyBackendGet } from "@/lib/bff-proxy";

export async function GET(
    request: NextRequest,
    context: { params: Promise<{ path: string[] }> },
) {
    const token = await getAccessToken();
    if (!token) {
        return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
    }

    const { path } = await context.params;
    const baseUrl = process.env.CORVETRA_API_BASE_URL;
    if (!baseUrl) {
        return NextResponse.json({ detail: "API service unavailable" }, { status: 503 });
    }

    const backendUrl = buildBackendApiUrl(baseUrl, path, request.nextUrl.search);
    if (!backendUrl) return NextResponse.json({ detail: "Not found" }, { status: 404 });

    try {
        return await proxyBackendGet(backendUrl, token, request.signal);
    } catch {
        return NextResponse.json({ detail: "API service unavailable" }, { status: 503 });
    }
}
