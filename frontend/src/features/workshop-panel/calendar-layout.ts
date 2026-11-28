import { APP_TIME_ZONE } from "@/i18n/routing";

export const SLOT_MINUTES = 15;
const MINUTES_PER_HOUR = 60;
const MINUTES_PER_DAY = 24 * MINUTES_PER_HOUR;
const DEFAULT_START_MINUTES = 8 * MINUTES_PER_HOUR;
const DEFAULT_END_MINUTES = 16 * MINUTES_PER_HOUR;
const TIME_PART_LENGTH = 2;

const zonedTimeFormatter = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: APP_TIME_ZONE,
});

export type CalendarWindow = {
  startMinutes: number;
  endMinutes: number;
};

export type TimedItem = {
  start_at: string;
  end_at: string;
};

export type OpeningTimes = {
  opens_at: string;
  closes_at: string;
};

export type BlockPlacement = {
  rowStart: number;
  rowSpan: number;
};

export function minutesFromTimeString(value: string): number {
  const [hours = 0, minutes = 0] = value.split(":").map(Number);
  return hours * MINUTES_PER_HOUR + minutes;
}

export function minutesOfDayInZone(isoTimestamp: string): number {
  const parts = zonedTimeFormatter.formatToParts(new Date(isoTimestamp));
  const hour = Number(parts.find((part) => part.type === "hour")?.value ?? 0);
  const minute = Number(parts.find((part) => part.type === "minute")?.value ?? 0);
  return hour * MINUTES_PER_HOUR + minute;
}

function floorToSlot(minutes: number): number {
  return Math.floor(minutes / SLOT_MINUTES) * SLOT_MINUTES;
}

function ceilToSlot(minutes: number): number {
  return Math.ceil(minutes / SLOT_MINUTES) * SLOT_MINUTES;
}

function itemEndMinutes(item: TimedItem): number {
  const start = minutesOfDayInZone(item.start_at);
  const end = minutesOfDayInZone(item.end_at);
  return end <= start ? MINUTES_PER_DAY : end;
}

export function calendarWindow(
  opening: OpeningTimes | undefined,
  items: readonly TimedItem[],
): CalendarWindow {
  let startMinutes = opening ? minutesFromTimeString(opening.opens_at) : DEFAULT_START_MINUTES;
  let endMinutes = opening ? minutesFromTimeString(opening.closes_at) : DEFAULT_END_MINUTES;
  for (const item of items) {
    startMinutes = Math.min(startMinutes, floorToSlot(minutesOfDayInZone(item.start_at)));
    endMinutes = Math.max(endMinutes, ceilToSlot(itemEndMinutes(item)));
  }
  return { startMinutes, endMinutes };
}

export function timeRowStarts(window: CalendarWindow): number[] {
  const rows: number[] = [];
  for (let minutes = window.startMinutes; minutes < window.endMinutes; minutes += SLOT_MINUTES) {
    rows.push(minutes);
  }
  return rows;
}

export function formatMinutes(minutes: number): string {
  const hours = String(Math.floor(minutes / MINUTES_PER_HOUR)).padStart(TIME_PART_LENGTH, "0");
  const rest = String(minutes % MINUTES_PER_HOUR).padStart(TIME_PART_LENGTH, "0");
  return `${hours}:${rest}`;
}

export function placeBlock(item: TimedItem, window: CalendarWindow): BlockPlacement {
  const start = minutesOfDayInZone(item.start_at);
  const end = itemEndMinutes(item);
  const rowStart = Math.floor((start - window.startMinutes) / SLOT_MINUTES) + 1;
  const rowSpan = Math.max(1, Math.ceil((end - start) / SLOT_MINUTES));
  return { rowStart, rowSpan };
}

export function isFullHour(minutes: number): boolean {
  return minutes % MINUTES_PER_HOUR === 0;
}
