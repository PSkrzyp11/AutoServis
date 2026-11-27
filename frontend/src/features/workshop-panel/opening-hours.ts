import type { OpeningHoursPayload } from "@/features/workshop-panel/api";
import type { OpeningHoursEntry } from "@/lib/api/types";
import { formatTime } from "@/lib/format";

export const ISO_WEEKDAYS = [1, 2, 3, 4, 5, 6, 7] as const;
export type IsoWeekday = (typeof ISO_WEEKDAYS)[number];

export const DEFAULT_OPENS_AT = "08:00";
export const DEFAULT_CLOSES_AT = "16:00";

export type DaySchedule = {
  weekday: IsoWeekday;
  isOpen: boolean;
  opensAt: string;
  closesAt: string;
};

export function toDaySchedules(entries: readonly OpeningHoursEntry[]): DaySchedule[] {
  return ISO_WEEKDAYS.map((weekday) => {
    const entry = entries.find((item) => item.weekday === weekday);
    return {
      weekday,
      isOpen: entry !== undefined,
      opensAt: entry ? formatTime(entry.opens_at) : DEFAULT_OPENS_AT,
      closesAt: entry ? formatTime(entry.closes_at) : DEFAULT_CLOSES_AT,
    };
  });
}

export function findInvalidDays(days: readonly DaySchedule[]): IsoWeekday[] {
  return days
    .filter((day) => day.isOpen && (day.opensAt === "" || day.closesAt <= day.opensAt))
    .map((day) => day.weekday);
}

export function toOpeningHoursPayload(days: readonly DaySchedule[]): OpeningHoursPayload {
  return {
    days: days
      .filter((day) => day.isOpen)
      .map((day) => ({ weekday: day.weekday, opens_at: day.opensAt, closes_at: day.closesAt })),
  };
}
