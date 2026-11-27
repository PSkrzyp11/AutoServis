import type { ServiceTypeCreatePayload } from "@/features/workshop-panel/api";
import type { ServiceType } from "@/lib/api/types";
import { VAT_RATES } from "@/lib/api/types";

const PRICE_PATTERN = /^\d{1,10}([.,]\d{1,2})?$/;
const DURATION_PATTERN = /^\d{1,3}$/;
const SLOT_MINUTES = 15;
const MAX_DURATION_MINUTES = 480;
const DEFAULT_VAT_RATE = "23";
const DECIMAL_COMMA = ",";
const DECIMAL_POINT = ".";

export type VatRateOption = (typeof VAT_RATES)[number];

export type ServiceTypeDraft = {
  name: string;
  durationMinutes: string;
  priceNet: string;
  vatRate: VatRateOption;
};

export type ServiceTypeDraftErrors = Partial<
  Record<keyof ServiceTypeDraft, "required" | "invalidDuration" | "invalidPrice">
>;

export const EMPTY_SERVICE_TYPE_DRAFT: ServiceTypeDraft = {
  name: "",
  durationMinutes: "60",
  priceNet: "",
  vatRate: DEFAULT_VAT_RATE,
};

function isVatRateOption(value: string): value is VatRateOption {
  return VAT_RATES.some((rate) => rate === value);
}

export function toVatRateOption(value: string): VatRateOption {
  const integerRate = String(Number(value));
  return isVatRateOption(integerRate) ? integerRate : DEFAULT_VAT_RATE;
}

export function toServiceTypeDraft(serviceType: ServiceType): ServiceTypeDraft {
  return {
    name: serviceType.name,
    durationMinutes: String(serviceType.duration_minutes),
    priceNet: serviceType.base_price_net.replace(DECIMAL_POINT, DECIMAL_COMMA),
    vatRate: toVatRateOption(serviceType.vat_rate),
  };
}

export function validateServiceTypeDraft(draft: ServiceTypeDraft): ServiceTypeDraftErrors {
  const errors: ServiceTypeDraftErrors = {};
  if (draft.name.trim() === "") {
    errors.name = "required";
  }
  const duration = Number(draft.durationMinutes);
  const isValidDuration =
    DURATION_PATTERN.test(draft.durationMinutes) &&
    duration >= SLOT_MINUTES &&
    duration <= MAX_DURATION_MINUTES &&
    duration % SLOT_MINUTES === 0;
  if (!isValidDuration) {
    errors.durationMinutes = "invalidDuration";
  }
  if (!PRICE_PATTERN.test(draft.priceNet.trim())) {
    errors.priceNet = "invalidPrice";
  }
  return errors;
}

export function toServiceTypePayload(draft: ServiceTypeDraft): ServiceTypeCreatePayload {
  return {
    name: draft.name.trim(),
    duration_minutes: Number(draft.durationMinutes),
    base_price_net: draft.priceNet.trim().replace(DECIMAL_COMMA, DECIMAL_POINT),
    vat_rate: draft.vatRate,
  };
}
