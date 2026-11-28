import { describe, expect, it } from "vitest";

import {
  calendarWindow,
  formatMinutes,
  minutesOfDayInZone,
  placeBlock,
  timeRowStarts,
} from "@/features/workshop-panel/calendar-layout";

const OPENING = { opens_at: "08:00:00", closes_at: "16:00:00" };

describe("calendar layout", () => {
  it("reads minutes of day in the Warsaw time zone", () => {
    expect(minutesOfDayInZone("2026-12-01T07:30:00Z")).toBe(8 * 60 + 30);
    expect(minutesOfDayInZone("2026-07-01T07:30:00Z")).toBe(9 * 60 + 30);
  });

  it("uses opening hours as the default window", () => {
    const window = calendarWindow(OPENING, []);

    expect(window).toEqual({ startMinutes: 480, endMinutes: 960 });
    expect(timeRowStarts(window)).toHaveLength(32);
  });

  it("extends the window to show appointments outside opening hours", () => {
    const window = calendarWindow(OPENING, [
      { start_at: "2026-12-01T06:10:00Z", end_at: "2026-12-01T07:10:00Z" },
      { start_at: "2026-12-01T15:30:00Z", end_at: "2026-12-01T16:20:00Z" },
    ]);

    expect(window).toEqual({ startMinutes: 7 * 60, endMinutes: 17 * 60 + 30 });
  });

  it("places appointments on 15 minute rows", () => {
    const window = calendarWindow(OPENING, []);

    expect(
      placeBlock({ start_at: "2026-12-01T08:30:00Z", end_at: "2026-12-01T09:15:00Z" }, window),
    ).toEqual({ rowStart: 7, rowSpan: 3 });
  });

  it("formats minutes as clock times", () => {
    expect(formatMinutes(7 * 60 + 5)).toBe("07:05");
  });
});
