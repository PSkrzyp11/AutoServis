export const SESSION_HINT_COOKIE = "session_present";
export const REDIRECT_QUERY_PARAM = "next";

export function resolveSafeRedirect(value: string | null): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) {
    return null;
  }
  return value;
}
