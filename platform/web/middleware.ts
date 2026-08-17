import { NextRequest, NextResponse } from "next/server";
import { AUTH_COOKIE_NAME } from "@/lib/auth-core";
import { shouldRedirectToLogin } from "@/lib/route-access";

export function middleware(request: NextRequest) {
    if (!shouldRedirectToLogin(request.nextUrl.pathname, request.cookies.has(AUTH_COOKIE_NAME))) {
        return NextResponse.next();
    }

    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("returnTo", `${request.nextUrl.pathname}${request.nextUrl.search}`);
    return NextResponse.redirect(loginUrl);
}

export const config = {
    matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
