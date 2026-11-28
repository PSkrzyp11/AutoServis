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

const weekdayFormatter = new Intl.DateTimeFormat(APP_FORMAT_LOCALE, {
  weekday: "long",
  timeZone: "UTC",
});

const timeOfDayFormatter = new Intl.DateTimeFormat(APP_FORMAT_LOCALE, {
  hour: "2-digit",
  minute: "2-digit",
  timeZone: APP_TIME_ZONE,
});

const shortWeekdayFormatter = new Intl.DateTimeFormat(APP_FORMAT_LOCALE, {
  weekday: "short",
  timeZone: "UTC",
});

const dayMonthFormatter = new Intl.DateTimeFormat(APP_FORMAT_LOCALE, {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

const longDayFormatter = new Intl.DateTimeFormat(APP_FORMAT_LOCALE, {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

const REFERENCE_MONDAY_UTC = Date.UTC(2024, 0, 1);
const MILLISECONDS_PER_DAY = 86_400_000;
const TIME_PREFIX_LENGTH = 5;

export function formatWeekday(isoWeekday: number): string {
  const date = new Date(REFERENCE_MONDAY_UTC + (isoWeekday - 1) * MILLISECONDS_PER_DAY);
  const name = weekdayFormatter.format(date);
  return name.charAt(0).toLocaleUpperCase(APP_FORMAT_LOCALE) + name.slice(1);
}

export function formatTime(value: string): string {
  return value.slice(0, TIME_PREFIX_LENGTH);
}

export function formatTimeOfDay(value: Date | string): string {
  return timeOfDayFormatter.format(toDate(value));
}

export function formatShortWeekday(utcDate: Date): string {
  return shortWeekdayFormatter.format(utcDate);
}

export function formatDayMonth(utcDate: Date): string {
  return dayMonthFormatter.format(utcDate);
}

export function formatLongDay(utcDate: Date): string {
  return longDayFormatter.format(utcDate);
}

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
