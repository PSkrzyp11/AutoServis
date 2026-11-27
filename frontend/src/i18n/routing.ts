import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["pl"],
  defaultLocale: "pl",
  localePrefix: "as-needed",
  pathnames: {
    "/": "/",
    "/login": { pl: "/logowanie" },
    "/register": { pl: "/rejestracja" },
    "/forgot-password": { pl: "/nie-pamietam-hasla" },
    "/reset-password": { pl: "/nowe-haslo" },
    "/account": { pl: "/konto" },
    "/admin/users": { pl: "/admin/uzytkownicy" },
  },
});

export type AppLocale = (typeof routing.locales)[number];
export type AppPathname = keyof typeof routing.pathnames;

export const APP_TIME_ZONE = "Europe/Warsaw";

export function localizePathname(pathname: AppPathname, locale: AppLocale): string {
  const localized = routing.pathnames[pathname];
  const path = typeof localized === "string" ? localized : localized[locale];
  const isDefaultLocale = locale === routing.defaultLocale;
  return isDefaultLocale ? path : `/${locale}${path === "/" ? "" : path}`;
}
