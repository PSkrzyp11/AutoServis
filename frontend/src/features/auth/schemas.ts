import type { useTranslations } from "next-intl";
import { z } from "zod";

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;
export const FULL_NAME_MIN_LENGTH = 2;
export const FULL_NAME_MAX_LENGTH = 200;
export const PHONE_PATTERN = /^\+?[0-9 ]{9,20}$/;

export type ValidationTranslator = ReturnType<typeof useTranslations<"validation">>;

export function emailField(t: ValidationTranslator) {
  return z
    .string()
    .trim()
    .min(1, { error: t("required") })
    .pipe(z.email({ error: t("invalidEmail") }));
}

export function newPasswordField(t: ValidationTranslator) {
  return z
    .string()
    .min(PASSWORD_MIN_LENGTH, { error: t("passwordTooShort", { min: PASSWORD_MIN_LENGTH }) })
    .max(PASSWORD_MAX_LENGTH, { error: t("passwordTooLong", { max: PASSWORD_MAX_LENGTH }) });
}

export function fullNameField(t: ValidationTranslator) {
  return z
    .string()
    .trim()
    .min(FULL_NAME_MIN_LENGTH, { error: t("fullNameTooShort", { min: FULL_NAME_MIN_LENGTH }) })
    .max(FULL_NAME_MAX_LENGTH, { error: t("fullNameTooLong", { max: FULL_NAME_MAX_LENGTH }) });
}

export function optionalPhoneField(t: ValidationTranslator) {
  return z
    .string()
    .trim()
    .refine((value) => value === "" || PHONE_PATTERN.test(value), { error: t("invalidPhone") });
}

export function createLoginSchema(t: ValidationTranslator) {
  return z.object({
    email: emailField(t),
    password: z.string().min(1, { error: t("required") }),
  });
}

export function createRegisterSchema(t: ValidationTranslator) {
  return z
    .object({
      fullName: fullNameField(t),
      email: emailField(t),
      phone: optionalPhoneField(t),
      password: newPasswordField(t),
      confirmPassword: z.string(),
    })
    .refine((values) => values.password === values.confirmPassword, {
      error: t("passwordsMismatch"),
      path: ["confirmPassword"],
    });
}

export function createForgotPasswordSchema(t: ValidationTranslator) {
  return z.object({ email: emailField(t) });
}

export function createResetPasswordSchema(t: ValidationTranslator) {
  return z
    .object({
      newPassword: newPasswordField(t),
      confirmPassword: z.string(),
    })
    .refine((values) => values.newPassword === values.confirmPassword, {
      error: t("passwordsMismatch"),
      path: ["confirmPassword"],
    });
}

export type LoginFormValues = z.infer<ReturnType<typeof createLoginSchema>>;
export type RegisterFormValues = z.infer<ReturnType<typeof createRegisterSchema>>;
export type ForgotPasswordFormValues = z.infer<ReturnType<typeof createForgotPasswordSchema>>;
export type ResetPasswordFormValues = z.infer<ReturnType<typeof createResetPasswordSchema>>;
