import { type NextRequest, NextResponse } from "next/server";
import createMiddleware from "next-intl/middleware";

import {
  type AppPathname,
  localizedPathnamePattern,
  localizePathname,
  routing,
} from "@/i18n/routing";
import { REDIRECT_QUERY_PARAM, SESSION_HINT_COOKIE } from "@/lib/session";

const PROTECTED_PATHNAMES: readonly AppPathname[] = [
  "/account",
  "/vehicles",
  "/appointments",
  "/workshops/[slug]/booking",
  "/panel/calendar",
  "/panel/workshop",
  "/panel/bays",
  "/panel/services",
  "/panel/team",
  "/admin/users",
  "/admin/workshops",
];

const PROTECTED_PATTERNS: readonly RegExp[] = routing.locales.flatMap((locale) =>
  PROTECTED_PATHNAMES.map((pathname) => localizedPathnamePattern(pathname, locale)),
);

const handleI18nRouting = createMiddleware(routing);

function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PATTERNS.some((pattern) => pattern.test(pathname));
}

export default function proxy(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  if (isProtectedPath(pathname) && !request.cookies.has(SESSION_HINT_COOKIE)) {
    const loginUrl = new URL(localizePathname("/login", routing.defaultLocale), request.url);
    loginUrl.searchParams.set(REDIRECT_QUERY_PARAM, pathname);
    return NextResponse.redirect(loginUrl);
  }
  return handleI18nRouting(request);
}

export const config = {
  matcher: ["/((?!api|health|_next|_vercel|.*\\..*).*)"],
};
