"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useMemo } from "react";
import { useForm } from "react-hook-form";

import { FormField } from "@/components/form-field";
import { StatusMessage } from "@/components/status-message";
import { Button } from "@/components/ui/button";
import {
  createWorkshopSchema,
  type WorkshopFormValues,
  type WorkshopPayload,
  toWorkshopPayload,
} from "@/features/workshops/workshop-form-schema";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";

type WorkshopFormProps = {
  idPrefix: string;
  defaultValues: WorkshopFormValues;
  submitLabel: string;
  isPending: boolean;
  error: unknown;
  disabled?: boolean;
  onSubmit: (payload: WorkshopPayload) => void;
  onCancel?: () => void;
};

export function WorkshopForm({
  idPrefix,
  defaultValues,
  submitLabel,
  isPending,
  error,
  disabled = false,
  onSubmit,
  onCancel,
}: WorkshopFormProps) {
  const t = useTranslations();
  const tValidation = useTranslations("validation");
  const errorMessage = useApiErrorMessage();
  const schema = useMemo(() => createWorkshopSchema(tValidation), [tValidation]);
  const form = useForm<WorkshopFormValues>({ resolver: zodResolver(schema), defaultValues });
  const { errors } = form.formState;
  const fieldId = (name: string) => `${idPrefix}-${name}`;

  return (
    <form
      className="grid gap-4"
      method="post"
      noValidate
      onSubmit={form.handleSubmit((values) => onSubmit(toWorkshopPayload(values)))}
    >
      <fieldset disabled={disabled} className="grid gap-4 sm:grid-cols-2">
        {error ? (
          <div className="sm:col-span-2">
            <StatusMessage tone="error" message={errorMessage(error)} />
          </div>
        ) : null}
        <div className="sm:col-span-2">
          <FormField
            id={fieldId("name")}
            label={t("workshopFields.name")}
            error={errors.name?.message}
            {...form.register("name")}
          />
        </div>
        <FormField
          id={fieldId("taxId")}
          inputMode="numeric"
          label={t("workshopFields.taxId")}
          error={errors.taxId?.message}
          {...form.register("taxId")}
        />
        <FormField
          id={fieldId("phone")}
          type="tel"
          label={t("workshopFields.phone")}
          error={errors.phone?.message}
          {...form.register("phone")}
        />
        <div className="sm:col-span-2">
          <FormField
            id={fieldId("street")}
            autoComplete="street-address"
            label={t("workshopFields.street")}
            error={errors.street?.message}
            {...form.register("street")}
          />
        </div>
        <FormField
          id={fieldId("postalCode")}
          autoComplete="postal-code"
          label={t("workshopFields.postalCode")}
          error={errors.postalCode?.message}
          {...form.register("postalCode")}
        />
        <FormField
          id={fieldId("city")}
          autoComplete="address-level2"
          label={t("workshopFields.city")}
          error={errors.city?.message}
          {...form.register("city")}
        />
        <div className="sm:col-span-2">
          <FormField
            id={fieldId("email")}
            type="email"
            label={t("workshopFields.email")}
            error={errors.email?.message}
            {...form.register("email")}
          />
        </div>
      </fieldset>
      {disabled ? null : (
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={isPending}>
            {isPending ? t("common.saving") : submitLabel}
          </Button>
          {onCancel ? (
            <Button type="button" variant="ghost" onClick={onCancel}>
              {t("common.cancel")}
            </Button>
          ) : null}
        </div>
      )}
    </form>
  );
}
