import { describe, expect, it } from "vitest";

import { buildBookingDays } from "@/features/booking/booking-days";

describe("buildBookingDays", () => {
  it("marks days without opening hours and closure days as closed", () => {
    const days = buildBookingDays(
      "2026-12-21",
      [1, 2, 3, 4, 5].map((weekday) => ({ weekday })),
      [{ closed_on: "2026-12-24" }],
      7,
    );

    expect(days).toEqual([
      { key: "2026-12-21", isOpen: true },
      { key: "2026-12-22", isOpen: true },
      { key: "2026-12-23", isOpen: true },
      { key: "2026-12-24", isOpen: false },
      { key: "2026-12-25", isOpen: true },
      { key: "2026-12-26", isOpen: false },
      { key: "2026-12-27", isOpen: false },
    ]);
  });
});
