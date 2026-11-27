"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";

import { AuthCard } from "@/components/auth-card";
import { FormField } from "@/components/form-field";
import { StatusMessage } from "@/components/status-message";
import { Button } from "@/components/ui/button";
import { useRequestPasswordReset } from "@/features/auth/api";
import { createForgotPasswordSchema, type ForgotPasswordFormValues } from "@/features/auth/schemas";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import { Link } from "@/i18n/navigation";

export function ForgotPasswordForm() {
  const t = useTranslations("auth");
  const tValidation = useTranslations("validation");
  const errorMessage = useApiErrorMessage();
  const passwordReset = useRequestPasswordReset();

  const form = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(createForgotPasswordSchema(tValidation)),
    defaultValues: { email: "" },
  });
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit(({ email }) => passwordReset.mutate(email));

  return (
    <AuthCard
      title={t("forgotPassword.title")}
      description={t("forgotPassword.description")}
      footer={
        <Link href="/login" className="underline underline-offset-4">
          {t("forgotPassword.backToLogin")}
        </Link>
      }
    >
      {passwordReset.isSuccess ? (
        <StatusMessage tone="success" message={t("forgotPassword.success")} />
      ) : (
        <form className="grid gap-4" method="post" onSubmit={onSubmit} noValidate>
          {passwordReset.isError ? (
            <StatusMessage tone="error" message={errorMessage(passwordReset.error)} />
          ) : null}
          <FormField
            id="email"
            type="email"
            autoComplete="email"
            label={t("fields.email")}
            error={errors.email?.message}
            {...form.register("email")}
          />
          <Button type="submit" size="lg" disabled={passwordReset.isPending}>
            {passwordReset.isPending ? t("forgotPassword.submitting") : t("forgotPassword.submit")}
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
