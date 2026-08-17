export function isPublicPage(pathname: string): boolean {
    return pathname === "/login";
}

export function shouldRedirectToLogin(pathname: string, hasAuthCookie: boolean): boolean {
    return !isPublicPage(pathname) && !hasAuthCookie;
}
