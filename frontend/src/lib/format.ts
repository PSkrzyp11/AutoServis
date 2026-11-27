import { APP_TIME_ZONE } from "@/i18n/routing";

export const APP_FORMAT_LOCALE = "pl-PL";
export const APP_CURRENCY = "PLN";

const dateFormatter = new Intl.DateTimeFormat(APP_FORMAT_LOCALE, {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  timeZone: APP_TIME_ZONE,
});

const dateTimeFormatter = new Intl.DateTimeFormat(APP_FORMAT_LOCALE, {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: APP_TIME_ZONE,
});

const currencyFormatter = new Intl.NumberFormat(APP_FORMAT_LOCALE, {
  style: "currency",
  currency: APP_CURRENCY,
});

const numberFormatter = new Intl.NumberFormat(APP_FORMAT_LOCALE);

function toDate(value: Date | string): Date {
  return value instanceof Date ? value : new Date(value);
}

export function formatDate(value: Date | string): string {
  return dateFormatter.format(toDate(value));
}

export function formatDateTime(value: Date | string): string {
  return dateTimeFormatter.format(toDate(value));
}

export function formatCurrency(amount: number | string): string {
  return currencyFormatter.format(Number(amount));
}

export function formatNumber(value: number | string): string {
  return numberFormatter.format(Number(value));
}
