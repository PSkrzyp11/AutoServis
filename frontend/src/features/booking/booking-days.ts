import { addDays, type DayKey, isoWeekdayOf } from "@/lib/day-keys";

export const BOOKING_DAYS_SHOWN = 21;

export type BookingDay = {
  key: DayKey;
  isOpen: boolean;
};

type WeekdayHours = { weekday: number };
type ClosureDay = { closed_on: string };

export function buildBookingDays(
  today: DayKey,
  openingHours: readonly WeekdayHours[],
  closures: readonly ClosureDay[],
  count: number = BOOKING_DAYS_SHOWN,
): BookingDay[] {
  const openWeekdays = new Set(openingHours.map((entry) => entry.weekday));
  const closedDays = new Set(closures.map((closure) => closure.closed_on));
  return Array.from({ length: count }, (_, index) => {
    const key = addDays(today, index);
    return { key, isOpen: openWeekdays.has(isoWeekdayOf(key)) && !closedDays.has(key) };
  });
}
