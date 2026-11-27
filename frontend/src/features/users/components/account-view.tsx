"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";

import { FormField } from "@/components/form-field";
import { StatusMessage } from "@/components/status-message";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useCurrentUser } from "@/features/auth/api";
import { useUpdateProfile } from "@/features/users/api";
import { RoleBadge } from "@/features/users/components/role-badge";
import { createProfileSchema, type ProfileFormValues } from "@/features/users/schemas";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import type { User } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

function ProfileForm({ user }: { user: User }) {
  const t = useTranslations();
  const tValidation = useTranslations("validation");
  const errorMessage = useApiErrorMessage();
  const updateProfile = useUpdateProfile();

  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(createProfileSchema(tValidation)),
    defaultValues: { fullName: user.full_name, phone: user.phone ?? "" },
  });
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit((values) => updateProfile.mutate(values));

  return (
    <form className="grid gap-4" method="post" onSubmit={onSubmit} noValidate>
      {updateProfile.isError ? (
        <StatusMessage tone="error" message={errorMessage(updateProfile.error)} />
      ) : null}
      {updateProfile.isSuccess ? (
        <StatusMessage tone="success" message={t("account.saved")} />
      ) : null}
      <FormField
        id="fullName"
        autoComplete="name"
        label={t("auth.fields.fullName")}
        error={errors.fullName?.message}
        {...form.register("fullName")}
      />
      <FormField
        id="phone"
        type="tel"
        autoComplete="tel"
        label={t("auth.fields.phone")}
        error={errors.phone?.message}
        {...form.register("phone")}
      />
      <Button type="submit" className="justify-self-start" disabled={updateProfile.isPending}>
        {updateProfile.isPending ? t("common.saving") : t("common.save")}
      </Button>
    </form>
  );
}

export function AccountView() {
  const t = useTranslations("account");
  const { data: user } = useCurrentUser();

  if (!user) {
    return null;
  }

  return (
    <div className="grid gap-6">
      <header className="grid gap-1">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </header>
      <Card>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-3">
            <div className="grid gap-1">
              <dt className="text-sm text-muted-foreground">{t("email")}</dt>
              <dd className="break-all">{user.email}</dd>
            </div>
            <div className="grid gap-1">
              <dt className="text-sm text-muted-foreground">{t("role")}</dt>
              <dd>
                <RoleBadge role={user.role} />
              </dd>
            </div>
            <div className="grid gap-1">
              <dt className="text-sm text-muted-foreground">{t("memberSince")}</dt>
              <dd>
                <time dateTime={user.created_at}>{formatDate(user.created_at)}</time>
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>
            <h2 className="text-lg font-semibold">{t("editTitle")}</h2>
          </CardTitle>
          <CardDescription>{t("description")}</CardDescription>
        </CardHeader>
        <CardContent>
          <ProfileForm user={user} />
        </CardContent>
      </Card>
    </div>
  );
}
