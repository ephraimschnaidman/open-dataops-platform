import { cookies } from "next/headers";
export {
    AUTH_COOKIE_NAME,
    authenticateWithBackend,
    authCookieOptions,
    clearedAuthCookieOptions,
    isBackendTokenResponse,
    isSafeReturnTo,
    safeReturnTo,
} from "@/lib/auth-core";
import { AUTH_COOKIE_NAME } from "@/lib/auth-core";

export async function getAccessToken(): Promise<string | undefined> {
    return (await cookies()).get(AUTH_COOKIE_NAME)?.value;
}
