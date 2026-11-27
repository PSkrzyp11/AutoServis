"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";

import { AuthCard } from "@/components/auth-card";
import { FormField } from "@/components/form-field";
import { StatusMessage } from "@/components/status-message";
import { Button } from "@/components/ui/button";
import { useRegister } from "@/features/auth/api";
import { createRegisterSchema, type RegisterFormValues } from "@/features/auth/schemas";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import { Link, useRouter } from "@/i18n/navigation";

export function RegisterForm() {
  const t = useTranslations("auth");
  const tValidation = useTranslations("validation");
  const errorMessage = useApiErrorMessage();
  const router = useRouter();
  const registration = useRegister();

  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(createRegisterSchema(tValidation)),
    defaultValues: { fullName: "", email: "", phone: "", password: "", confirmPassword: "" },
  });
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit(({ fullName, email, phone, password }) => {
    registration.mutate(
      { fullName, email, phone, password },
      { onSuccess: () => router.replace("/account") },
    );
  });

  return (
    <AuthCard
      title={t("register.title")}
      description={t("register.description")}
      footer={
        <p>
          {t("register.hasAccount")}{" "}
          <Link href="/login" className="underline underline-offset-4">
            {t("register.loginLink")}
          </Link>
        </p>
      }
    >
      <form className="grid gap-4" method="post" onSubmit={onSubmit} noValidate>
        {registration.isError ? (
          <StatusMessage tone="error" message={errorMessage(registration.error)} />
        ) : null}
        <FormField
          id="fullName"
          autoComplete="name"
          label={t("fields.fullName")}
          error={errors.fullName?.message}
          {...form.register("fullName")}
        />
        <FormField
          id="email"
          type="email"
          autoComplete="email"
          label={t("fields.email")}
          error={errors.email?.message}
          {...form.register("email")}
        />
        <FormField
          id="phone"
          type="tel"
          autoComplete="tel"
          label={t("fields.phone")}
          error={errors.phone?.message}
          {...form.register("phone")}
        />
        <FormField
          id="password"
          type="password"
          autoComplete="new-password"
          label={t("fields.password")}
          error={errors.password?.message}
          {...form.register("password")}
        />
        <FormField
          id="confirmPassword"
          type="password"
          autoComplete="new-password"
          label={t("fields.confirmPassword")}
          error={errors.confirmPassword?.message}
          {...form.register("confirmPassword")}
        />
        <Button type="submit" size="lg" disabled={registration.isPending}>
          {registration.isPending ? t("register.submitting") : t("register.submit")}
        </Button>
      </form>
    </AuthCard>
  );
}
