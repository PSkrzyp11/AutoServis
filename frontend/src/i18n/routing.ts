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
    "/workshops": { pl: "/warsztaty" },
    "/workshops/[slug]": { pl: "/warsztaty/[slug]" },
    "/account": { pl: "/konto" },
    "/vehicles": { pl: "/pojazdy" },
    "/panel/workshop": { pl: "/panel/warsztat" },
    "/panel/bays": { pl: "/panel/stanowiska" },
    "/panel/services": { pl: "/panel/uslugi" },
    "/panel/team": { pl: "/panel/zespol" },
    "/admin/users": { pl: "/admin/uzytkownicy" },
    "/admin/workshops": { pl: "/admin/warsztaty" },
  },
});

export type AppLocale = (typeof routing.locales)[number];
export type AppPathname = keyof typeof routing.pathnames;
export type StaticAppPathname = Exclude<AppPathname, `${string}[${string}]${string}`>;

export const APP_TIME_ZONE = "Europe/Warsaw";

export function localizePathname(pathname: StaticAppPathname, locale: AppLocale): string {
  const localized = routing.pathnames[pathname];
  const path = typeof localized === "string" ? localized : localized[locale];
  const isDefaultLocale = locale === routing.defaultLocale;
  return isDefaultLocale ? path : `/${locale}${path === "/" ? "" : path}`;
}
