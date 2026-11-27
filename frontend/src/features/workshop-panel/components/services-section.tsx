"use client";

import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { FormField } from "@/components/form-field";
import { SelectField } from "@/components/native-select";
import { SectionCard } from "@/components/section-card";
import { StatusMessage } from "@/components/status-message";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useCreateServiceType,
  useServiceTypes,
  useUpdateServiceType,
} from "@/features/workshop-panel/api";
import { usePanelWorkshop } from "@/features/workshop-panel/components/panel-shell";
import {
  EMPTY_SERVICE_TYPE_DRAFT,
  type ServiceTypeDraft,
  type ServiceTypeDraftErrors,
  toServiceTypeDraft,
  toServiceTypePayload,
  toVatRateOption,
  validateServiceTypeDraft,
} from "@/features/workshop-panel/service-type-form";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import { useFormatDuration } from "@/hooks/use-format-duration";
import { type ServiceType, VAT_RATES } from "@/lib/api/types";
import { formatCurrency } from "@/lib/format";

function ServiceTypeFields({
  idPrefix,
  draft,
  errors,
  onChange,
}: {
  idPrefix: string;
  draft: ServiceTypeDraft;
  errors: ServiceTypeDraftErrors;
  onChange: (draft: ServiceTypeDraft) => void;
}) {
  const t = useTranslations();
  const errorText = (key: keyof ServiceTypeDraft) => {
    const code = errors[key];
    return code ? t(`validation.${code}`) : undefined;
  };

  return (
    <>
      <div className="sm:col-span-2">
        <FormField
          id={`${idPrefix}-name`}
          label={t("panel.services.name")}
          value={draft.name}
          maxLength={150}
          error={errorText("name")}
          onChange={(event) => onChange({ ...draft, name: event.target.value })}
        />
      </div>
      <div className="grid gap-1">
        <FormField
          id={`${idPrefix}-duration`}
          inputMode="numeric"
          label={t("panel.services.duration")}
          value={draft.durationMinutes}
          error={errorText("durationMinutes")}
          onChange={(event) => onChange({ ...draft, durationMinutes: event.target.value })}
        />
        <p className="text-sm text-muted-foreground">{t("panel.services.durationHint")}</p>
      </div>
      <FormField
        id={`${idPrefix}-price`}
        inputMode="decimal"
        label={t("panel.services.priceNet")}
        value={draft.priceNet}
        error={errorText("priceNet")}
        onChange={(event) => onChange({ ...draft, priceNet: event.target.value })}
      />
      <SelectField
        id={`${idPrefix}-vat`}
        label={t("panel.services.vatRate")}
        value={draft.vatRate}
        onChange={(event) => onChange({ ...draft, vatRate: toVatRateOption(event.target.value) })}
      >
        {VAT_RATES.map((rate) => (
          <option key={rate} value={rate}>
            {t("panel.services.vatOption", { rate })}
          </option>
        ))}
      </SelectField>
    </>
  );
}

function ServiceTypeEditor({
  idPrefix,
  initialDraft,
  submitLabel,
  isPending,
  error,
  onSubmit,
  onCancel,
}: {
  idPrefix: string;
  initialDraft: ServiceTypeDraft;
  submitLabel: string;
  isPending: boolean;
  error: unknown;
  onSubmit: (draft: ServiceTypeDraft, reset: () => void) => void;
  onCancel?: () => void;
}) {
  const t = useTranslations("common");
  const errorMessage = useApiErrorMessage();
  const [draft, setDraft] = useState(initialDraft);
  const [errors, setErrors] = useState<ServiceTypeDraftErrors>({});

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const validationErrors = validateServiceTypeDraft(draft);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length === 0) {
      onSubmit(draft, () => setDraft(initialDraft));
    }
  };

  return (
    <form className="grid gap-3 sm:grid-cols-2" method="post" noValidate onSubmit={handleSubmit}>
      {error ? (
        <div className="sm:col-span-2">
          <StatusMessage tone="error" message={errorMessage(error)} />
        </div>
      ) : null}
      <ServiceTypeFields idPrefix={idPrefix} draft={draft} errors={errors} onChange={setDraft} />
      <div className="flex flex-wrap gap-2 sm:col-span-2">
        <Button type="submit" disabled={isPending}>
          {isPending ? t("saving") : submitLabel}
        </Button>
        {onCancel ? (
          <Button type="button" variant="ghost" onClick={onCancel}>
            {t("cancel")}
          </Button>
        ) : null}
      </div>
    </form>
  );
}

function ServiceTypeRow({ serviceType }: { serviceType: ServiceType }) {
  const t = useTranslations();
  const formatDuration = useFormatDuration();
  const { workshop, canManage } = usePanelWorkshop();
  const updateServiceType = useUpdateServiceType(workshop.id);
  const [isEditing, setIsEditing] = useState(false);

  if (isEditing) {
    return (
      <TableRow>
        <TableCell colSpan={6}>
          <ServiceTypeEditor
            idPrefix={`service-${serviceType.id}`}
            initialDraft={toServiceTypeDraft(serviceType)}
            submitLabel={t("common.save")}
            isPending={updateServiceType.isPending}
            error={updateServiceType.error}
            onCancel={() => setIsEditing(false)}
            onSubmit={(draft) =>
              updateServiceType.mutate(
                { serviceTypeId: serviceType.id, payload: toServiceTypePayload(draft) },
                { onSuccess: () => setIsEditing(false) },
              )
            }
          />
        </TableCell>
      </TableRow>
    );
  }

  return (
    <TableRow>
      <TableCell className="font-medium whitespace-normal">{serviceType.name}</TableCell>
      <TableCell>{formatDuration(serviceType.duration_minutes)}</TableCell>
      <TableCell className="tabular-nums">{formatCurrency(serviceType.base_price_net)}</TableCell>
      <TableCell className="tabular-nums">{formatCurrency(serviceType.base_price_gross)}</TableCell>
      <TableCell>
        <Badge variant={serviceType.is_active ? "secondary" : "outline"}>
          {serviceType.is_active ? t("common.active") : t("common.inactive")}
        </Badge>
      </TableCell>
      <TableCell>
        {canManage ? (
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
              {t("common.edit")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={updateServiceType.isPending}
              onClick={() =>
                updateServiceType.mutate({
                  serviceTypeId: serviceType.id,
                  payload: { is_active: !serviceType.is_active },
                })
              }
            >
              {serviceType.is_active ? t("common.deactivate") : t("common.activate")}
            </Button>
          </div>
        ) : null}
      </TableCell>
    </TableRow>
  );
}

export function ServicesSection() {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const { workshop, canManage } = usePanelWorkshop();
  const serviceTypes = useServiceTypes(workshop.id);
  const createServiceType = useCreateServiceType(workshop.id);

  return (
    <div className="grid gap-6">
      <SectionCard title={t("panel.services.title")} description={t("panel.services.description")}>
        {serviceTypes.isError ? (
          <StatusMessage tone="error" message={errorMessage(serviceTypes.error)} />
        ) : null}
        {serviceTypes.isPending ? (
          <p role="status" className="text-sm text-muted-foreground">
            {t("common.loading")}
          </p>
        ) : null}
        {serviceTypes.data?.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("panel.services.empty")}</p>
        ) : null}
        {serviceTypes.data && serviceTypes.data.length > 0 ? (
          <div className="overflow-x-auto">
            <Table>
              <TableCaption className="sr-only">{t("panel.services.title")}</TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">{t("panel.services.name")}</TableHead>
                  <TableHead scope="col">{t("workshopDetail.duration")}</TableHead>
                  <TableHead scope="col">{t("panel.services.priceNet")}</TableHead>
                  <TableHead scope="col">{t("panel.services.priceGross")}</TableHead>
                  <TableHead scope="col">{t("panel.services.status")}</TableHead>
                  <TableHead scope="col">
                    {canManage ? t("panel.services.actions") : null}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {serviceTypes.data.map((serviceType) => (
                  <ServiceTypeRow key={serviceType.id} serviceType={serviceType} />
                ))}
              </TableBody>
            </Table>
          </div>
        ) : null}
      </SectionCard>
      {canManage ? (
        <SectionCard title={t("panel.services.add")}>
          <ServiceTypeEditor
            idPrefix="new-service"
            initialDraft={EMPTY_SERVICE_TYPE_DRAFT}
            submitLabel={t("panel.services.add")}
            isPending={createServiceType.isPending}
            error={createServiceType.error}
            onSubmit={(draft, reset) =>
              createServiceType.mutate(toServiceTypePayload(draft), { onSuccess: reset })
            }
          />
        </SectionCard>
      ) : null}
    </div>
  );
}
