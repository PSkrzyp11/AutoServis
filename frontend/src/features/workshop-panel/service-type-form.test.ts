import { describe, expect, it } from "vitest";

import {
  EMPTY_SERVICE_TYPE_DRAFT,
  toServiceTypeDraft,
  toServiceTypePayload,
  toVatRateOption,
  validateServiceTypeDraft,
} from "@/features/workshop-panel/service-type-form";

describe("service type form logic", () => {
  it("accepts a valid draft with a decimal comma", () => {
    const draft = { ...EMPTY_SERVICE_TYPE_DRAFT, name: "Geometria kół", priceNet: "179,50" };

    expect(validateServiceTypeDraft(draft)).toEqual({});
    expect(toServiceTypePayload(draft)).toEqual({
      name: "Geometria kół",
      duration_minutes: 60,
      base_price_net: "179.50",
      vat_rate: "23",
    });
  });

  it.each(["0", "50", "490", "abc"])("rejects duration %s", (durationMinutes) => {
    const errors = validateServiceTypeDraft({
      ...EMPTY_SERVICE_TYPE_DRAFT,
      name: "Usługa",
      priceNet: "100",
      durationMinutes,
    });

    expect(errors.durationMinutes).toBe("invalidDuration");
  });

  it.each(["", "12,345", "-5", "cena"])("rejects price %s", (priceNet) => {
    const errors = validateServiceTypeDraft({
      ...EMPTY_SERVICE_TYPE_DRAFT,
      name: "Usługa",
      priceNet,
    });

    expect(errors.priceNet).toBe("invalidPrice");
  });

  it("requires a name", () => {
    expect(validateServiceTypeDraft({ ...EMPTY_SERVICE_TYPE_DRAFT, priceNet: "1" }).name).toBe(
      "required",
    );
  });

  it("maps API values back to the form", () => {
    const draft = toServiceTypeDraft({
      id: "1",
      name: "Wymiana oleju",
      duration_minutes: 45,
      base_price_net: "199.00",
      vat_rate: "8.00",
      required_bay_type: null,
      base_price_gross: "214.92",
      is_active: true,
    });

    expect(draft).toEqual({
      name: "Wymiana oleju",
      durationMinutes: "45",
      priceNet: "199,00",
      vatRate: "8",
    });
    expect(toVatRateOption("13.00")).toBe("23");
  });
});
