import { NextRequest, NextResponse } from "next/server";
import { getAccessToken } from "@/lib/auth-session";
import { buildBackendApiUrl, proxyBackendGet, proxyBackendMutation } from "@/lib/bff-proxy";

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

async function mutate(request: NextRequest, context: { params: Promise<{ path: string[] }> }, method: "POST" | "PUT" | "DELETE") {
    const token = await getAccessToken();
    if (!token) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
    const { path } = await context.params;
    if (path[0] !== "settings") return NextResponse.json({ detail: "Not found" }, { status: 404 });
    const baseUrl = process.env.CORVETRA_API_BASE_URL;
    if (!baseUrl) return NextResponse.json({ detail: "API service unavailable" }, { status: 503 });
    const backendUrl = buildBackendApiUrl(baseUrl, path, request.nextUrl.search);
    if (!backendUrl) return NextResponse.json({ detail: "Not found" }, { status: 404 });
    try {
        const body = method === "DELETE" ? null : await request.text();
        return await proxyBackendMutation(backendUrl, token, method, body || null, request.signal);
    } catch {
        return NextResponse.json({ detail: "API service unavailable" }, { status: 503 });
    }
}

export const POST = (request: NextRequest, context: { params: Promise<{ path: string[] }> }) => mutate(request, context, "POST");
export const PUT = (request: NextRequest, context: { params: Promise<{ path: string[] }> }) => mutate(request, context, "PUT");
export const DELETE = (request: NextRequest, context: { params: Promise<{ path: string[] }> }) => mutate(request, context, "DELETE");
