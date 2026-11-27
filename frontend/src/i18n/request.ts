import { locale as rootLocale } from "next/root-params";
import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";

import { APP_TIME_ZONE, routing } from "@/i18n/routing";

export default getRequestConfig(async () => {
  const requestedLocale = await rootLocale();
  const locale = hasLocale(routing.locales, requestedLocale)
    ? requestedLocale
    : routing.defaultLocale;

  return {
    locale,
    timeZone: APP_TIME_ZONE,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
