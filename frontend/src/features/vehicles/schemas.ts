import { z } from "zod";

import type { ValidationTranslator } from "@/features/auth/schemas";
import type { Vehicle } from "@/lib/api/types";

export const VIN_PATTERN = /^[A-HJ-NPR-Z0-9]{17}$/;
export const PLATE_NUMBER_PATTERN = /^[A-Z]{1,3}[A-Z0-9]{2,5}$/;
const PLATE_NUMBER_MIN_LENGTH = 4;
const PLATE_NUMBER_MAX_LENGTH = 8;
const YEAR_PATTERN = /^\d{4}$/;
const MILEAGE_PATTERN = /^\d{1,7}$/;
const EARLIEST_PRODUCTION_YEAR = 1900;
const MAKE_MAX_LENGTH = 60;
const MODEL_MAX_LENGTH = 80;
const ENGINE_MAX_LENGTH = 60;
const IDENTIFIER_SEPARATORS = /[\s-]/g;

export function normalizeIdentifier(value: string): string {
  return value.replace(IDENTIFIER_SEPARATORS, "").toUpperCase();
}

export function isValidVin(value: string): boolean {
  return VIN_PATTERN.test(normalizeIdentifier(value));
}

export function isValidPlateNumber(value: string): boolean {
  const normalized = normalizeIdentifier(value);
  return (
    normalized.length >= PLATE_NUMBER_MIN_LENGTH &&
    normalized.length <= PLATE_NUMBER_MAX_LENGTH &&
    PLATE_NUMBER_PATTERN.test(normalized)
  );
}

function requiredText(t: ValidationTranslator, maxLength: number) {
  return z
    .string()
    .trim()
    .min(1, { error: t("required") })
    .max(maxLength, { error: t("textTooLong", { max: maxLength }) });
}

export function createVehicleSchema(t: ValidationTranslator, currentYear: number) {
  const latestYear = currentYear + 1;
  return z.object({
    make: requiredText(t, MAKE_MAX_LENGTH),
    model: requiredText(t, MODEL_MAX_LENGTH),
    productionYear: z
      .string()
      .trim()
      .refine(
        (value) => {
          const year = Number(value);
          return YEAR_PATTERN.test(value) && year >= EARLIEST_PRODUCTION_YEAR && year <= latestYear;
        },
        { error: t("invalidYear", { min: EARLIEST_PRODUCTION_YEAR, max: latestYear }) },
      ),
    plateNumber: z
      .string()
      .trim()
      .min(1, { error: t("required") })
      .refine(isValidPlateNumber, { error: t("invalidPlate") }),
    vin: z
      .string()
      .trim()
      .refine((value) => value === "" || isValidVin(value), { error: t("invalidVin") }),
    mileageKm: z
      .string()
      .trim()
      .refine((value) => value === "" || MILEAGE_PATTERN.test(value), {
        error: t("invalidMileage"),
      }),
    engine: z
      .string()
      .trim()
      .max(ENGINE_MAX_LENGTH, { error: t("textTooLong", { max: ENGINE_MAX_LENGTH }) }),
  });
}

export type VehicleFormValues = z.infer<ReturnType<typeof createVehicleSchema>>;

export type VehiclePayload = {
  make: string;
  model: string;
  production_year: number;
  plate_number: string;
  vin: string | null;
  mileage_km: number | null;
  engine: string | null;
};

export const EMPTY_VEHICLE_FORM: VehicleFormValues = {
  make: "",
  model: "",
  productionYear: "",
  plateNumber: "",
  vin: "",
  mileageKm: "",
  engine: "",
};

export function toVehicleFormValues(vehicle: Vehicle): VehicleFormValues {
  return {
    make: vehicle.make,
    model: vehicle.model,
    productionYear: String(vehicle.production_year),
    plateNumber: vehicle.plate_number,
    vin: vehicle.vin ?? "",
    mileageKm: vehicle.mileage_km === null ? "" : String(vehicle.mileage_km),
    engine: vehicle.engine ?? "",
  };
}

export function toVehiclePayload(values: VehicleFormValues): VehiclePayload {
  return {
    make: values.make,
    model: values.model,
    production_year: Number(values.productionYear),
    plate_number: normalizeIdentifier(values.plateNumber),
    vin: values.vin === "" ? null : normalizeIdentifier(values.vin),
    mileage_km: values.mileageKm === "" ? null : Number(values.mileageKm),
    engine: values.engine === "" ? null : values.engine,
  };
}
