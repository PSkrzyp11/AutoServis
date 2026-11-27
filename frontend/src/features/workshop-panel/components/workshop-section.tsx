"use client";

import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { ConfirmButton } from "@/components/confirm-button";
import { FormField } from "@/components/form-field";
import { SectionCard } from "@/components/section-card";
import { StatusMessage } from "@/components/status-message";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useAddClosure,
  useClosures,
  useDeleteClosure,
  useReplaceOpeningHours,
  useStaffWorkshop,
  useUpdateWorkshop,
} from "@/features/workshop-panel/api";
import { usePanelWorkshop } from "@/features/workshop-panel/components/panel-shell";
import {
  type DaySchedule,
  findInvalidDays,
  toDaySchedules,
  toOpeningHoursPayload,
} from "@/features/workshop-panel/opening-hours";
import { WorkshopForm } from "@/features/workshops/components/workshop-form";
import { toWorkshopFormValues } from "@/features/workshops/workshop-form-schema";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import type { OpeningHoursEntry } from "@/lib/api/types";
import { formatDate, formatWeekday } from "@/lib/format";

const TIME_STEP_SECONDS = 900;

function OpeningHoursEditor({ initialEntries }: { initialEntries: OpeningHoursEntry[] }) {
  const t = useTranslations("panel.hours");
  const tCommon = useTranslations("common");
  const errorMessage = useApiErrorMessage();
  const { workshop, canManage } = usePanelWorkshop();
  const replaceOpeningHours = useReplaceOpeningHours(workshop.id);
  const [days, setDays] = useState<DaySchedule[]>(() => toDaySchedules(initialEntries));
  const [invalidDays, setInvalidDays] = useState<number[]>([]);

  const updateDay = (weekday: number, changes: Partial<DaySchedule>) =>
    setDays((previous) =>
      previous.map((day) => (day.weekday === weekday ? { ...day, ...changes } : day)),
    );

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const invalid = findInvalidDays(days);
    setInvalidDays(invalid);
    if (invalid.length === 0) {
      replaceOpeningHours.mutate(toOpeningHoursPayload(days));
    }
  };

  return (
    <form className="grid gap-4" method="post" noValidate onSubmit={onSubmit}>
      {replaceOpeningHours.isError ? (
        <StatusMessage tone="error" message={errorMessage(replaceOpeningHours.error)} />
      ) : null}
      {replaceOpeningHours.isSuccess ? <StatusMessage tone="success" message={t("saved")} /> : null}
      {invalidDays.map((weekday) => (
        <StatusMessage
          key={weekday}
          tone="error"
          message={t("invalidRange", { weekday: formatWeekday(weekday) })}
        />
      ))}
      <fieldset disabled={!canManage} className="grid gap-3">
        {days.map((day) => {
          const weekdayName = formatWeekday(day.weekday);
          const isInvalid = invalidDays.includes(day.weekday);
          return (
            <div
              key={day.weekday}
              className="grid grid-cols-[minmax(0,10rem)_1fr] items-center gap-3 sm:grid-cols-[10rem_auto_auto]"
            >
              <label className="flex items-center gap-2 text-sm font-medium">
                <input
                  type="checkbox"
                  className="size-4"
                  checked={day.isOpen}
                  aria-label={t("open", { weekday: weekdayName })}
                  onChange={(event) => updateDay(day.weekday, { isOpen: event.target.checked })}
                />
                {weekdayName}
              </label>
              <div className="flex items-center gap-2">
                <Input
                  type="time"
                  step={TIME_STEP_SECONDS}
                  className="w-28"
                  value={day.opensAt}
                  disabled={!day.isOpen}
                  aria-invalid={isInvalid ? true : undefined}
                  aria-label={t("opensAt", { weekday: weekdayName })}
                  onChange={(event) => updateDay(day.weekday, { opensAt: event.target.value })}
                />
                <span aria-hidden="true">–</span>
                <Input
                  type="time"
                  step={TIME_STEP_SECONDS}
                  className="w-28"
                  value={day.closesAt}
                  disabled={!day.isOpen}
                  aria-invalid={isInvalid ? true : undefined}
                  aria-label={t("closesAt", { weekday: weekdayName })}
                  onChange={(event) => updateDay(day.weekday, { closesAt: event.target.value })}
                />
              </div>
            </div>
          );
        })}
      </fieldset>
      {canManage ? (
        <Button
          type="submit"
          className="justify-self-start"
          disabled={replaceOpeningHours.isPending}
        >
          {replaceOpeningHours.isPending ? tCommon("saving") : tCommon("save")}
        </Button>
      ) : null}
    </form>
  );
}

function ClosuresManager() {
  const t = useTranslations("panel.closures");
  const tCommon = useTranslations("common");
  const tValidation = useTranslations("validation");
  const errorMessage = useApiErrorMessage();
  const { workshop, canManage } = usePanelWorkshop();
  const closures = useClosures(workshop.id);
  const addClosure = useAddClosure(workshop.id);
  const deleteClosure = useDeleteClosure(workshop.id);
  const [closedOn, setClosedOn] = useState("");
  const [reason, setReason] = useState("");
  const [dateError, setDateError] = useState<string | undefined>(undefined);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (closedOn === "") {
      setDateError(tValidation("required"));
      return;
    }
    setDateError(undefined);
    addClosure.mutate(
      { closed_on: closedOn, reason: reason.trim() === "" ? null : reason.trim() },
      {
        onSuccess: () => {
          setClosedOn("");
          setReason("");
        },
      },
    );
  };

  const mutationError = addClosure.error ?? deleteClosure.error;

  return (
    <div className="grid gap-4">
      {mutationError ? <StatusMessage tone="error" message={errorMessage(mutationError)} /> : null}
      {closures.isError ? (
        <StatusMessage tone="error" message={errorMessage(closures.error)} />
      ) : null}
      {closures.data?.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("empty")}</p>
      ) : null}
      {closures.data && closures.data.length > 0 ? (
        <ul className="grid gap-2">
          {closures.data.map((closure) => (
            <li
              key={closure.id}
              className="flex flex-wrap items-center justify-between gap-2 text-sm"
            >
              <span>
                <time dateTime={closure.closed_on} className="font-medium">
                  {formatDate(closure.closed_on)}
                </time>
                {closure.reason ? ` – ${closure.reason}` : null}
              </span>
              {canManage ? (
                <ConfirmButton
                  label={tCommon("delete")}
                  accessibleLabel={t("deleteLabel", { date: formatDate(closure.closed_on) })}
                  question={t("deleteLabel", { date: formatDate(closure.closed_on) })}
                  disabled={deleteClosure.isPending}
                  onConfirm={() => deleteClosure.mutate(closure.id)}
                />
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      {canManage ? (
        <form
          className="grid gap-4 sm:grid-cols-[12rem_minmax(0,1fr)_auto] sm:items-end"
          method="post"
          noValidate
          onSubmit={onSubmit}
        >
          <FormField
            id="closure-date"
            type="date"
            label={t("date")}
            value={closedOn}
            error={dateError}
            onChange={(event) => setClosedOn(event.target.value)}
          />
          <FormField
            id="closure-reason"
            label={t("reason")}
            value={reason}
            maxLength={200}
            onChange={(event) => setReason(event.target.value)}
          />
          <Button type="submit" disabled={addClosure.isPending}>
            {t("add")}
          </Button>
        </form>
      ) : null}
    </div>
  );
}

export function WorkshopSection() {
  const t = useTranslations("panel");
  const tCommon = useTranslations("common");
  const errorMessage = useApiErrorMessage();
  const { workshop, canManage } = usePanelWorkshop();
  const detail = useStaffWorkshop(workshop.id);
  const updateWorkshop = useUpdateWorkshop(workshop.id);

  if (detail.isPending) {
    return (
      <p role="status" className="text-sm text-muted-foreground">
        {tCommon("loading")}
      </p>
    );
  }
  if (detail.isError) {
    return <StatusMessage tone="error" message={errorMessage(detail.error)} />;
  }

  return (
    <div className="grid gap-6">
      <SectionCard title={t("details.title")}>
        {updateWorkshop.isSuccess ? (
          <StatusMessage tone="success" message={t("details.saved")} />
        ) : null}
        <WorkshopForm
          key={detail.data.id}
          idPrefix="workshop-details"
          defaultValues={toWorkshopFormValues(detail.data)}
          submitLabel={tCommon("save")}
          isPending={updateWorkshop.isPending}
          error={updateWorkshop.error}
          disabled={!canManage}
          onSubmit={(payload) => updateWorkshop.mutate(payload)}
        />
      </SectionCard>
      <SectionCard title={t("hours.title")} description={t("hours.description")}>
        <OpeningHoursEditor key={detail.data.id} initialEntries={detail.data.opening_hours} />
      </SectionCard>
      <SectionCard title={t("closures.title")} description={t("closures.description")}>
        <ClosuresManager />
      </SectionCard>
    </div>
  );
}
