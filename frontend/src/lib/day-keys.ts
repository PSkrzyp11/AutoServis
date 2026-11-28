import { APP_TIME_ZONE } from "@/i18n/routing";

export type DayKey = string;

const DAY_KEY_FORMATTER = new Intl.DateTimeFormat("en-CA", {
  timeZone: APP_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});
const MILLISECONDS_PER_DAY = 86_400_000;
const DAY_KEY_LENGTH = 10;
const SUNDAY_JS_INDEX = 0;
const ISO_SUNDAY = 7;

function dayKeyToUtcMidnight(dayKey: DayKey): number {
  const [year = 0, month = 1, day = 1] = dayKey.split("-").map(Number);
  return Date.UTC(year, month - 1, day);
}

export function todayKey(now: Date = new Date()): DayKey {
  return DAY_KEY_FORMATTER.format(now);
}

export function dayKeyOf(isoTimestamp: string): DayKey {
  return DAY_KEY_FORMATTER.format(new Date(isoTimestamp));
}

export function addDays(dayKey: DayKey, days: number): DayKey {
  return new Date(dayKeyToUtcMidnight(dayKey) + days * MILLISECONDS_PER_DAY)
    .toISOString()
    .slice(0, DAY_KEY_LENGTH);
}

export function isoWeekdayOf(dayKey: DayKey): number {
  const jsWeekday = new Date(dayKeyToUtcMidnight(dayKey)).getUTCDay();
  return jsWeekday === SUNDAY_JS_INDEX ? ISO_SUNDAY : jsWeekday;
}

export function utcDateOf(dayKey: DayKey): Date {
  return new Date(dayKeyToUtcMidnight(dayKey));
}
