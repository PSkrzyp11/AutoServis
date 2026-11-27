import { describe, expect, it } from "vitest";

import {
  DEFAULT_CLOSES_AT,
  DEFAULT_OPENS_AT,
  findInvalidDays,
  toDaySchedules,
  toOpeningHoursPayload,
} from "@/features/workshop-panel/opening-hours";

describe("opening hours editor logic", () => {
  it("builds a full week with closed days using defaults", () => {
    const days = toDaySchedules([{ weekday: 2, opens_at: "07:30:00", closes_at: "17:00:00" }]);

    expect(days).toHaveLength(7);
    expect(days[1]).toEqual({ weekday: 2, isOpen: true, opensAt: "07:30", closesAt: "17:00" });
    expect(days[0]).toEqual({
      weekday: 1,
      isOpen: false,
      opensAt: DEFAULT_OPENS_AT,
      closesAt: DEFAULT_CLOSES_AT,
    });
  });

  it("finds open days whose closing time is not after opening", () => {
    const days = toDaySchedules([]).map((day) =>
      day.weekday === 3 ? { ...day, isOpen: true, opensAt: "18:00", closesAt: "08:00" } : day,
    );

    expect(findInvalidDays(days)).toEqual([3]);
  });

  it("sends only open days to the API", () => {
    const days = toDaySchedules([
      { weekday: 1, opens_at: "08:00:00", closes_at: "16:00:00" },
      { weekday: 6, opens_at: "09:00:00", closes_at: "13:00:00" },
    ]);

    expect(toOpeningHoursPayload(days)).toEqual({
      days: [
        { weekday: 1, opens_at: "08:00", closes_at: "16:00" },
        { weekday: 6, opens_at: "09:00", closes_at: "13:00" },
      ],
    });
  });
});
