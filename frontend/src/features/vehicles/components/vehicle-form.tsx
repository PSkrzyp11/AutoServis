"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useMemo } from "react";
import { useForm } from "react-hook-form";

import { FormField } from "@/components/form-field";
import { StatusMessage } from "@/components/status-message";
import { Button } from "@/components/ui/button";
import {
  createVehicleSchema,
  type VehicleFormValues,
  type VehiclePayload,
  toVehiclePayload,
} from "@/features/vehicles/schemas";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";

type VehicleFormProps = {
  idPrefix: string;
  defaultValues: VehicleFormValues;
  isPending: boolean;
  error: unknown;
  onSubmit: (payload: VehiclePayload) => void;
  onCancel: () => void;
};

export function VehicleForm({
  idPrefix,
  defaultValues,
  isPending,
  error,
  onSubmit,
  onCancel,
}: VehicleFormProps) {
  const t = useTranslations();
  const tValidation = useTranslations("validation");
  const errorMessage = useApiErrorMessage();
  const schema = useMemo(
    () => createVehicleSchema(tValidation, new Date().getFullYear()),
    [tValidation],
  );
  const form = useForm<VehicleFormValues>({ resolver: zodResolver(schema), defaultValues });
  const { errors } = form.formState;
  const fieldId = (name: string) => `${idPrefix}-${name}`;

  return (
    <form
      className="grid gap-4"
      method="post"
      noValidate
      onSubmit={form.handleSubmit((values) => onSubmit(toVehiclePayload(values)))}
    >
      {error ? <StatusMessage tone="error" message={errorMessage(error)} /> : null}
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField
          id={fieldId("make")}
          label={t("vehicles.fields.make")}
          error={errors.make?.message}
          {...form.register("make")}
        />
        <FormField
          id={fieldId("model")}
          label={t("vehicles.fields.model")}
          error={errors.model?.message}
          {...form.register("model")}
        />
        <FormField
          id={fieldId("productionYear")}
          inputMode="numeric"
          label={t("vehicles.fields.productionYear")}
          error={errors.productionYear?.message}
          {...form.register("productionYear")}
        />
        <FormField
          id={fieldId("plateNumber")}
          autoCapitalize="characters"
          label={t("vehicles.fields.plateNumber")}
          error={errors.plateNumber?.message}
          {...form.register("plateNumber")}
        />
        <div className="grid gap-1 sm:col-span-2">
          <FormField
            id={fieldId("vin")}
            autoCapitalize="characters"
            label={t("vehicles.fields.vin")}
            error={errors.vin?.message}
            {...form.register("vin")}
          />
          <p className="text-sm text-muted-foreground">{t("vehicles.vinHint")}</p>
        </div>
        <FormField
          id={fieldId("mileageKm")}
          inputMode="numeric"
          label={t("vehicles.fields.mileage")}
          error={errors.mileageKm?.message}
          {...form.register("mileageKm")}
        />
        <FormField
          id={fieldId("engine")}
          label={t("vehicles.fields.engine")}
          error={errors.engine?.message}
          {...form.register("engine")}
        />
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={isPending}>
          {isPending ? t("common.saving") : t("common.save")}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
      </div>
    </form>
  );
}
