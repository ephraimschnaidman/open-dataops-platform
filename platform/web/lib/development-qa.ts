export const isDevelopmentQaEnabled = process.env.NODE_ENV === "development";

export function getDevelopmentQaParam(params: Pick<URLSearchParams, "get">) {
    return isDevelopmentQaEnabled ? params.get("qa") : null;
}
