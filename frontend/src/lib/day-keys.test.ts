import { describe, expect, it } from "vitest";

import { addDays, dayKeyOf, isoWeekdayOf, todayKey } from "@/lib/day-keys";

describe("day keys", () => {
  it("uses the Warsaw calendar day for today", () => {
    expect(todayKey(new Date("2026-11-30T23:30:00Z"))).toBe("2026-12-01");
    expect(todayKey(new Date("2026-07-15T21:59:00Z"))).toBe("2026-07-15");
  });

  it("maps timestamps to Warsaw days", () => {
    expect(dayKeyOf("2026-12-31T23:15:00Z")).toBe("2027-01-01");
  });

  it("adds days across month and year boundaries", () => {
    expect(addDays("2026-12-30", 3)).toBe("2027-01-02");
    expect(addDays("2027-03-01", -1)).toBe("2027-02-28");
    expect(addDays("2027-03-27", 2)).toBe("2027-03-29");
  });

  it("returns ISO weekdays with Monday as 1 and Sunday as 7", () => {
    expect(isoWeekdayOf("2026-11-30")).toBe(1);
    expect(isoWeekdayOf("2026-12-06")).toBe(7);
  });
});
