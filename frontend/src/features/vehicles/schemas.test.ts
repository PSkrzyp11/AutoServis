import { createTranslator } from "next-intl";
import { describe, expect, it } from "vitest";

import {
  createVehicleSchema,
  EMPTY_VEHICLE_FORM,
  isValidPlateNumber,
  isValidVin,
  normalizeIdentifier,
  toVehicleFormValues,
  toVehiclePayload,
} from "@/features/vehicles/schemas";

import messages from "../../../messages/pl.json";

const t = createTranslator({ locale: "pl", messages, namespace: "validation" });
const CURRENT_YEAR = 2026;

const validForm = {
  ...EMPTY_VEHICLE_FORM,
  make: "Skoda",
  model: "Octavia",
  productionYear: "2017",
  plateNumber: "we 3k721",
  vin: "tmbjj7ne8h0218734",
};

function issues(values: typeof validForm): Record<string, string> {
  const result = createVehicleSchema(t, CURRENT_YEAR).safeParse(values);
  return result.success
    ? {}
    : Object.fromEntries(result.error.issues.map((issue) => [issue.path.join("."), issue.message]));
}

describe("vehicle identifiers", () => {
  it("normalizes spaces, hyphens and case", () => {
    expect(normalizeIdentifier(" wa 582-13 ")).toBe("WA58213");
  });

  it.each(["SB1K93BE10E412873", "sb1k 93be 10e4 12873"])("accepts VIN %s", (vin) => {
    expect(isValidVin(vin)).toBe(true);
  });

  it.each(["SB1K93BE10E41287", "SB1K93BE10E41287O", "IB1K93BE10E412873"])(
    "rejects VIN %s",
    (vin) => {
      expect(isValidVin(vin)).toBe(false);
    },
  );

  it.each(["WA 58213", "KRA 2M48", "kr4f21c"])("accepts plate %s", (plate) => {
    expect(isValidPlateNumber(plate)).toBe(true);
  });

  it.each(["W1", "1WA2345", "WA123456789"])("rejects plate %s", (plate) => {
    expect(isValidPlateNumber(plate)).toBe(false);
  });
});

describe("createVehicleSchema", () => {
  it("accepts a valid vehicle with empty optional fields", () => {
    expect(issues({ ...validForm, vin: "", mileageKm: "", engine: "" })).toEqual({});
  });

  it("reports Polish messages for invalid fields", () => {
    const result = issues({
      ...validForm,
      make: "",
      productionYear: "1899",
      plateNumber: "1",
      vin: "123",
      mileageKm: "dużo",
    });

    expect(result).toEqual({
      make: "To pole jest wymagane.",
      productionYear: "Podaj rok produkcji z zakresu 1900–2027.",
      plateNumber: "Podaj poprawny numer rejestracyjny, np. WA 12345.",
      vin: "VIN musi mieć 17 znaków i nie może zawierać liter I, O ani Q.",
      mileageKm: "Podaj przebieg jako liczbę kilometrów.",
    });
  });
});

describe("vehicle payload mapping", () => {
  it("converts form values into the API payload", () => {
    expect(toVehiclePayload({ ...validForm, mileageKm: "164200", engine: "2.0 TDI" })).toEqual({
      make: "Skoda",
      model: "Octavia",
      production_year: 2017,
      plate_number: "WE3K721",
      vin: "TMBJJ7NE8H0218734",
      mileage_km: 164200,
      engine: "2.0 TDI",
    });
  });

  it("sends null for cleared optional fields", () => {
    const payload = toVehiclePayload({ ...validForm, vin: "", mileageKm: "", engine: "" });

    expect(payload.vin).toBeNull();
    expect(payload.mileage_km).toBeNull();
    expect(payload.engine).toBeNull();
  });

  it("round-trips an API vehicle through the form", () => {
    const vehicle = {
      id: "1",
      make: "Toyota",
      model: "Corolla",
      production_year: 2019,
      plate_number: "WA58213",
      vin: null,
      mileage_km: null,
      engine: null,
      created_at: "2026-11-27T10:00:00Z",
    };

    expect(toVehiclePayload(toVehicleFormValues(vehicle))).toEqual({
      make: "Toyota",
      model: "Corolla",
      production_year: 2019,
      plate_number: "WA58213",
      vin: null,
      mileage_km: null,
      engine: null,
    });
  });
});
