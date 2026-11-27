import { z } from "zod";

import { emailField, PHONE_PATTERN, type ValidationTranslator } from "@/features/auth/schemas";
import type { WorkshopRead } from "@/lib/api/types";

export const POSTAL_CODE_PATTERN = /^\d{2}-\d{3}$/;
const TAX_ID_WEIGHTS = [6, 5, 7, 2, 3, 4, 5, 6, 7] as const;
const TAX_ID_PATTERN = /^\d{10}$/;
const TAX_ID_MODULO = 11;
const TAX_ID_SEPARATORS = /[\s-]/g;
const NAME_MAX_LENGTH = 200;
const STREET_MAX_LENGTH = 200;
const CITY_MAX_LENGTH = 100;

export function normalizeTaxId(value: string): string {
  return value.replace(TAX_ID_SEPARATORS, "");
}

export function isValidTaxId(value: string): boolean {
  const digits = normalizeTaxId(value);
  if (!TAX_ID_PATTERN.test(digits)) {
    return false;
  }
  const checksum = TAX_ID_WEIGHTS.reduce(
    (sum, weight, index) => sum + weight * Number(digits.charAt(index)),
    0,
  );
  return checksum % TAX_ID_MODULO === Number(digits.charAt(TAX_ID_WEIGHTS.length));
}

function requiredText(t: ValidationTranslator, maxLength: number) {
  return z
    .string()
    .trim()
    .min(1, { error: t("required") })
    .max(maxLength, { error: t("textTooLong", { max: maxLength }) });
}

export function createWorkshopSchema(t: ValidationTranslator) {
  return z.object({
    name: requiredText(t, NAME_MAX_LENGTH),
    taxId: z
      .string()
      .trim()
      .refine(isValidTaxId, { error: t("invalidTaxId") }),
    street: requiredText(t, STREET_MAX_LENGTH),
    postalCode: z
      .string()
      .trim()
      .regex(POSTAL_CODE_PATTERN, { error: t("invalidPostalCode") }),
    city: requiredText(t, CITY_MAX_LENGTH),
    phone: z
      .string()
      .trim()
      .regex(PHONE_PATTERN, { error: t("invalidPhone") }),
    email: emailField(t),
  });
}

export type WorkshopFormValues = z.infer<ReturnType<typeof createWorkshopSchema>>;

export type WorkshopPayload = {
  name: string;
  tax_id: string;
  street: string;
  postal_code: string;
  city: string;
  phone: string;
  email: string;
};

export const EMPTY_WORKSHOP_FORM: WorkshopFormValues = {
  name: "",
  taxId: "",
  street: "",
  postalCode: "",
  city: "",
  phone: "",
  email: "",
};

export function toWorkshopFormValues(workshop: WorkshopRead): WorkshopFormValues {
  return {
    name: workshop.name,
    taxId: workshop.tax_id,
    street: workshop.street,
    postalCode: workshop.postal_code,
    city: workshop.city,
    phone: workshop.phone,
    email: workshop.email,
  };
}

export function toWorkshopPayload(values: WorkshopFormValues): WorkshopPayload {
  return {
    name: values.name,
    tax_id: normalizeTaxId(values.taxId),
    street: values.street,
    postal_code: values.postalCode,
    city: values.city,
    phone: values.phone,
    email: values.email,
  };
}
