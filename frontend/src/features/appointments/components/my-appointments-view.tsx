"use client";

import { CalendarIcon, MapPinIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { ConfirmButton } from "@/components/confirm-button";
import { PageHeader } from "@/components/page-header";
import { StatusMessage } from "@/components/status-message";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AppointmentStatusBadge } from "@/features/appointments/components/appointment-status-badge";
import { useCancelMyAppointment, useMyAppointments } from "@/features/booking/api";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import { Link } from "@/i18n/navigation";
import type { Appointment, AppointmentScope } from "@/lib/api/types";
import { formatDate, formatTimeOfDay } from "@/lib/format";

const SCOPES: readonly AppointmentScope[] = ["upcoming", "past"];

function AppointmentCard({
  appointment,
  onCancelled,
}: {
  appointment: Appointment;
  onCancelled: () => void;
}) {
  const t = useTranslations("appointments");
  const tCommon = useTranslations("common");
  const errorMessage = useApiErrorMessage();
  const cancelAppointment = useCancelMyAppointment();
  const when = t("when", {
    date: formatDate(appointment.start_at),
    start: formatTimeOfDay(appointment.start_at),
    end: formatTimeOfDay(appointment.end_at),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2 className="flex flex-wrap items-center gap-2 text-lg font-semibold">
            <CalendarIcon aria-hidden="true" className="size-5" />
            <time dateTime={appointment.start_at}>{when}</time>
            <AppointmentStatusBadge status={appointment.status} />
          </h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        <p className="flex items-start gap-2">
          <MapPinIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <span>
            <Link
              href={{ pathname: "/workshops/[slug]", params: { slug: appointment.workshop.slug } }}
              className="font-medium underline-offset-4 hover:underline"
            >
              {appointment.workshop.name}
            </Link>
            , {appointment.workshop.street}, {appointment.workshop.city}
          </span>
        </p>
        <dl className="grid gap-2 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-muted-foreground">{t("service")}</dt>
            <dd>{appointment.service_type.name}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">{t("vehicle")}</dt>
            <dd>
              {appointment.vehicle.make} {appointment.vehicle.model}{" "}
              <span className="font-mono">{appointment.vehicle.plate_number}</span>
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">{t("bay")}</dt>
            <dd>{appointment.bay.name}</dd>
          </div>
          {appointment.problem_description ? (
            <div className="sm:col-span-3">
              <dt className="text-muted-foreground">{t("problem")}</dt>
              <dd className="whitespace-pre-line">{appointment.problem_description}</dd>
            </div>
          ) : null}
        </dl>
        {cancelAppointment.isError ? (
          <StatusMessage tone="error" message={errorMessage(cancelAppointment.error)} />
        ) : null}
        {appointment.status === "SCHEDULED" ? (
          <ConfirmButton
            label={t("cancel")}
            question={t("cancelQuestion", { date: when })}
            confirmLabel={tCommon("confirmCancel")}
            dismissLabel={tCommon("keep")}
            disabled={cancelAppointment.isPending}
            onConfirm={() => cancelAppointment.mutate(appointment.id, { onSuccess: onCancelled })}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}

export function MyAppointmentsView() {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const [scope, setScope] = useState<AppointmentScope>("upcoming");
  const [showCancelled, setShowCancelled] = useState(false);
  const appointments = useMyAppointments(scope);

  return (
    <div className="grid gap-6">
      <PageHeader title={t("appointments.title")} description={t("appointments.description")} />
      <div role="group" aria-label={t("appointments.tabsLabel")} className="flex gap-2">
        {SCOPES.map((item) => (
          <Button
            key={item}
            variant={scope === item ? "secondary" : "ghost"}
            aria-pressed={scope === item}
            onClick={() => {
              setScope(item);
              setShowCancelled(false);
            }}
          >
            {t(`appointments.${item}`)}
          </Button>
        ))}
      </div>
      {scope === "upcoming" ? (
        <p className="text-sm text-muted-foreground">{t("appointments.cancellationNote")}</p>
      ) : null}
      {showCancelled ? (
        <StatusMessage tone="success" message={t("appointments.cancelled")} />
      ) : null}
      {appointments.isError ? (
        <StatusMessage tone="error" message={errorMessage(appointments.error)} />
      ) : null}
      {appointments.isPending ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("common.loading")}
        </p>
      ) : null}
      {appointments.data?.items.length === 0 ? (
        <div className="grid gap-3">
          <p className="text-muted-foreground">
            {scope === "upcoming" ? t("appointments.emptyUpcoming") : t("appointments.emptyPast")}
          </p>
          <Link
            href="/workshops"
            className={buttonVariants({ variant: "outline", className: "justify-self-start" })}
          >
            {t("appointments.findWorkshop")}
          </Link>
        </div>
      ) : null}
      {appointments.data && appointments.data.items.length > 0 ? (
        <ul className="grid gap-4" aria-label={t("appointments.listLabel")}>
          {appointments.data.items.map((appointment) => (
            <li key={appointment.id}>
              <AppointmentCard
                appointment={appointment}
                onCancelled={() => setShowCancelled(true)}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
