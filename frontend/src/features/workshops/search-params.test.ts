import { describe, expect, it } from "vitest";

import {
  buildWorkshopSearchQuery,
  parseWorkshopSearchParams,
} from "@/features/workshops/search-params";

describe("workshop search params", () => {
  it("parses values and falls back to the first page", () => {
    expect(
      parseWorkshopSearchParams({ city: " Kraków ", search: ["auto", "x"], page: "-3" }),
    ).toEqual({ city: "Kraków", search: "auto", page: 1 });
    expect(parseWorkshopSearchParams({ page: "3" }).page).toBe(3);
    expect(parseWorkshopSearchParams({ page: "abc" }).page).toBe(1);
  });

  it("builds compact query strings for pagination links", () => {
    const query = { city: "Warszawa", search: "", page: 2 };

    expect(buildWorkshopSearchQuery(query, 1)).toEqual({ city: "Warszawa" });
    expect(buildWorkshopSearchQuery(query, 3)).toEqual({ city: "Warszawa", page: "3" });
  });
});
