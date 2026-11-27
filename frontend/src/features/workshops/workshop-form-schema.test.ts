import { createTranslator } from "next-intl";
import { describe, expect, it } from "vitest";

import {
  createWorkshopSchema,
  isValidTaxId,
  toWorkshopPayload,
} from "@/features/workshops/workshop-form-schema";

import messages from "../../../messages/pl.json";

const t = createTranslator({ locale: "pl", messages, namespace: "validation" });

const validWorkshop = {
  name: "Garaż pod Wawelem",
  taxId: "679-312-45-84",
  street: "ul. Zakopiańska 62",
  postalCode: "30-418",
  city: "Kraków",
  phone: "+48 12 345 67 89",
  email: "biuro@example.com",
};

describe("isValidTaxId", () => {
  it.each(["5252389141", "6793124584", "525-238-91-41"])("accepts %s", (taxId) => {
    expect(isValidTaxId(taxId)).toBe(true);
  });

  it.each(["5252389142", "123", "ABCDEFGHIJ", ""])("rejects %s", (taxId) => {
    expect(isValidTaxId(taxId)).toBe(false);
  });
});

describe("createWorkshopSchema", () => {
  it("accepts valid workshop data and normalizes the tax id in the payload", () => {
    const result = createWorkshopSchema(t).safeParse(validWorkshop);

    expect(result.success).toBe(true);
    expect(toWorkshopPayload(validWorkshop).tax_id).toBe("6793124584");
  });

  it("reports Polish messages for invalid tax id and postal code", () => {
    const result = createWorkshopSchema(t).safeParse({
      ...validWorkshop,
      taxId: "6793124585",
      postalCode: "30418",
    });

    expect(result.success).toBe(false);
    const messagesByField = Object.fromEntries(
      result.error?.issues.map((issue) => [issue.path.join("."), issue.message]) ?? [],
    );
    expect(messagesByField).toEqual({
      taxId: "Podaj poprawny NIP (10 cyfr).",
      postalCode: "Podaj kod pocztowy w formacie 00-000.",
    });
  });
});
