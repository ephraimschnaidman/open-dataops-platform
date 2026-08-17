import { NextResponse } from "next/server";
import {
    AUTH_COOKIE_NAME,
    authenticateWithBackend,
    authCookieOptions,
    isBackendTokenResponse,
    safeReturnTo,
} from "@/lib/auth-session";

export async function POST(request: Request) {
    let form: FormData;
    try {
        form = await request.formData();
    } catch {
        return NextResponse.json({ error: "Invalid login request." }, { status: 400 });
    }

    const username = form.get("username");
    const password = form.get("password");
    const returnTo = safeReturnTo(form.get("returnTo"));
    if (typeof username !== "string" || !username || typeof password !== "string" || !password) {
        return NextResponse.json({ error: "Username and password are required." }, { status: 422 });
    }

    let backendResponse: Response;
    try {
        backendResponse = await authenticateWithBackend(username, password);
    } catch {
        return NextResponse.json({ error: "Authentication service is unavailable." }, { status: 503 });
    }

    if (!backendResponse.ok) {
        const status = backendResponse.status === 401 ? 401 : backendResponse.status === 422 ? 422 : 503;
        const error = status === 401 ? "Invalid username or password." : "Authentication failed.";
        return NextResponse.json({ error }, { status });
    }

    let token: unknown;
    try {
        token = await backendResponse.json();
    } catch {
        return NextResponse.json({ error: "Authentication service returned an invalid response." }, { status: 503 });
    }
    if (!isBackendTokenResponse(token)) {
        return NextResponse.json({ error: "Authentication service returned an invalid response." }, { status: 503 });
    }

    const response = NextResponse.json({ ok: true, returnTo });
    response.cookies.set(AUTH_COOKIE_NAME, token.access_token, authCookieOptions(token.expires_in));
    return response;
}
