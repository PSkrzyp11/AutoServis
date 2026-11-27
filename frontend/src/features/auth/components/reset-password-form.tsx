"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";

import { AuthCard } from "@/components/auth-card";
import { FormField } from "@/components/form-field";
import { StatusMessage } from "@/components/status-message";
import { Button, buttonVariants } from "@/components/ui/button";
import { useConfirmPasswordReset } from "@/features/auth/api";
import { createResetPasswordSchema, type ResetPasswordFormValues } from "@/features/auth/schemas";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import { Link } from "@/i18n/navigation";

const TOKEN_QUERY_PARAM = "token";

export function ResetPasswordForm() {
  const t = useTranslations("auth");
  const tValidation = useTranslations("validation");
  const errorMessage = useApiErrorMessage();
  const token = useSearchParams().get(TOKEN_QUERY_PARAM);
  const confirmation = useConfirmPasswordReset();

  const form = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(createResetPasswordSchema(tValidation)),
    defaultValues: { newPassword: "", confirmPassword: "" },
  });
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit(({ newPassword }) => {
    if (token) {
      confirmation.mutate({ token, newPassword });
    }
  });

  if (!token) {
    return (
      <AuthCard title={t("resetPassword.title")} description={t("resetPassword.missingToken")}>
        <Link href="/forgot-password" className={buttonVariants({ size: "lg" })}>
          {t("resetPassword.requestNewLink")}
        </Link>
      </AuthCard>
    );
  }

  if (confirmation.isSuccess) {
    return (
      <AuthCard title={t("resetPassword.title")} description={t("resetPassword.description")}>
        <StatusMessage tone="success" message={t("resetPassword.success")} />
        <Link href="/login" className={buttonVariants({ size: "lg" })}>
          {t("resetPassword.goToLogin")}
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title={t("resetPassword.title")} description={t("resetPassword.description")}>
      <form className="grid gap-4" method="post" onSubmit={onSubmit} noValidate>
        {confirmation.isError ? (
          <StatusMessage tone="error" message={errorMessage(confirmation.error)} />
        ) : null}
        <FormField
          id="newPassword"
          type="password"
          autoComplete="new-password"
          label={t("fields.newPassword")}
          error={errors.newPassword?.message}
          {...form.register("newPassword")}
        />
        <FormField
          id="confirmPassword"
          type="password"
          autoComplete="new-password"
          label={t("fields.confirmPassword")}
          error={errors.confirmPassword?.message}
          {...form.register("confirmPassword")}
        />
        <Button type="submit" size="lg" disabled={confirmation.isPending}>
          {confirmation.isPending ? t("resetPassword.submitting") : t("resetPassword.submit")}
        </Button>
      </form>
    </AuthCard>
  );
}
