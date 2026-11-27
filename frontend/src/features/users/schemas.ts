import { z } from "zod";

import {
  fullNameField,
  optionalPhoneField,
  type ValidationTranslator,
} from "@/features/auth/schemas";

export function createProfileSchema(t: ValidationTranslator) {
  return z.object({
    fullName: fullNameField(t),
    phone: optionalPhoneField(t),
  });
}

export type ProfileFormValues = z.infer<ReturnType<typeof createProfileSchema>>;
