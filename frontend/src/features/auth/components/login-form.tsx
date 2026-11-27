"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter as useNextRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";

import { AuthCard } from "@/components/auth-card";
import { FormField } from "@/components/form-field";
import { StatusMessage } from "@/components/status-message";
import { Button } from "@/components/ui/button";
import { useLogin } from "@/features/auth/api";
import { createLoginSchema, type LoginFormValues } from "@/features/auth/schemas";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import { Link, useRouter } from "@/i18n/navigation";
import { REDIRECT_QUERY_PARAM, resolveSafeRedirect } from "@/lib/session";

export function LoginForm() {
  const t = useTranslations("auth");
  const tValidation = useTranslations("validation");
  const errorMessage = useApiErrorMessage();
  const router = useRouter();
  const nextRouter = useNextRouter();
  const searchParams = useSearchParams();
  const login = useLogin();

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(createLoginSchema(tValidation)),
    defaultValues: { email: "", password: "" },
  });
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit((values) => {
    login.mutate(values, {
      onSuccess: () => {
        const redirectTarget = resolveSafeRedirect(searchParams.get(REDIRECT_QUERY_PARAM));
        if (redirectTarget) {
          nextRouter.replace(redirectTarget);
          return;
        }
        router.replace("/account");
      },
    });
  });

  return (
    <AuthCard
      title={t("login.title")}
      description={t("login.description")}
      footer={
        <>
          <Link href="/forgot-password" className="underline underline-offset-4">
            {t("login.forgotPassword")}
          </Link>
          <p>
            {t("login.noAccount")}{" "}
            <Link href="/register" className="underline underline-offset-4">
              {t("login.registerLink")}
            </Link>
          </p>
        </>
      }
    >
      <form className="grid gap-4" method="post" onSubmit={onSubmit} noValidate>
        {login.isError ? <StatusMessage tone="error" message={errorMessage(login.error)} /> : null}
        <FormField
          id="email"
          type="email"
          autoComplete="email"
          label={t("fields.email")}
          error={errors.email?.message}
          {...form.register("email")}
        />
        <FormField
          id="password"
          type="password"
          autoComplete="current-password"
          label={t("fields.password")}
          error={errors.password?.message}
          {...form.register("password")}
        />
        <Button type="submit" size="lg" disabled={login.isPending}>
          {login.isPending ? t("login.submitting") : t("login.submit")}
        </Button>
      </form>
    </AuthCard>
  );
}
