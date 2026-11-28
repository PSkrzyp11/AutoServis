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
    "/workshops/[slug]/booking": { pl: "/warsztaty/[slug]/rezerwacja" },
    "/account": { pl: "/konto" },
    "/vehicles": { pl: "/pojazdy" },
    "/appointments": { pl: "/wizyty" },
    "/panel/calendar": { pl: "/panel/kalendarz" },
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

const DYNAMIC_SEGMENT_PATTERN = /^\[[^\]]+\]$/;
const REGEXP_SPECIAL_CHARACTERS = /[.*+?^${}()|[\]\\]/g;

function localizedTemplate(pathname: AppPathname, locale: AppLocale): string {
  const localized = routing.pathnames[pathname];
  const path = typeof localized === "string" ? localized : localized[locale];
  const isDefaultLocale = locale === routing.defaultLocale;
  return isDefaultLocale ? path : `/${locale}${path === "/" ? "" : path}`;
}

export function localizePathname(pathname: StaticAppPathname, locale: AppLocale): string {
  return localizedTemplate(pathname, locale);
}

export function localizedPathnamePattern(pathname: AppPathname, locale: AppLocale): RegExp {
  const source = localizedTemplate(pathname, locale)
    .split("/")
    .map((segment) =>
      DYNAMIC_SEGMENT_PATTERN.test(segment)
        ? "[^/]+"
        : segment.replace(REGEXP_SPECIAL_CHARACTERS, "\\$&"),
    )
    .join("/");
  return new RegExp(`^${source}(?:/.*)?$`);
}
