import { describe, expect, it } from "vitest";

import {
  formatCurrency,
  formatDate,
  formatDateTime,
  formatNumber,
  formatTime,
  formatWeekday,
} from "@/lib/format";

const NON_BREAKING_SPACES = /[  ]/g;

function normalizeSpaces(value: string): string {
  return value.replace(NON_BREAKING_SPACES, " ");
}

describe("format", () => {
  it("formats dates as DD.MM.YYYY in the Warsaw time zone", () => {
    expect(formatDate("2026-11-27T23:30:00Z")).toBe("28.11.2026");
  });

  it("formats date and time in the Warsaw time zone", () => {
    expect(formatDateTime("2026-07-01T08:05:00Z")).toBe("01.07.2026, 10:05");
  });

  it("formats amounts in Polish zloty", () => {
    expect(normalizeSpaces(formatCurrency("12345.5"))).toBe("12 345,50 zł");
  });

  it("follows the Polish convention of not grouping four-digit amounts", () => {
    expect(normalizeSpaces(formatCurrency(1234.5))).toBe("1234,50 zł");
  });

  it("formats ISO weekdays as capitalized Polish names", () => {
    expect(formatWeekday(1)).toBe("Poniedziałek");
    expect(formatWeekday(7)).toBe("Niedziela");
  });

  it("trims seconds from API times", () => {
    expect(formatTime("08:30:00")).toBe("08:30");
  });

  it("formats numbers with Polish separators", () => {
    expect(normalizeSpaces(formatNumber(1234567.891))).toBe("1 234 567,891");
  });
});
