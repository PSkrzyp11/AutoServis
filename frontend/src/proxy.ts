import { type NextRequest, NextResponse } from "next/server";
import createMiddleware from "next-intl/middleware";

import { localizePathname, routing, type StaticAppPathname } from "@/i18n/routing";
import { REDIRECT_QUERY_PARAM, SESSION_HINT_COOKIE } from "@/lib/session";

const PROTECTED_PATHNAMES: readonly StaticAppPathname[] = [
  "/account",
  "/vehicles",
  "/panel/workshop",
  "/panel/bays",
  "/panel/services",
  "/panel/team",
  "/admin/users",
  "/admin/workshops",
];

const handleI18nRouting = createMiddleware(routing);

function isProtectedPath(pathname: string): boolean {
  return routing.locales.some((locale) =>
    PROTECTED_PATHNAMES.some((protectedPathname) => {
      const localizedPath = localizePathname(protectedPathname, locale);
      return pathname === localizedPath || pathname.startsWith(`${localizedPath}/`);
    }),
  );
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
