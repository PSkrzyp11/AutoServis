"use client";

import { ChevronLeftIcon, ChevronRightIcon, MailIcon, PhoneIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { type CSSProperties, useState } from "react";

import { ConfirmButton } from "@/components/confirm-button";
import { SectionCard } from "@/components/section-card";
import { StatusMessage } from "@/components/status-message";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AppointmentStatusBadge } from "@/features/appointments/components/appointment-status-badge";
import {
  type AppointmentAction,
  useAppointmentAction,
  useStaffWorkshop,
  useWorkshopAppointments,
} from "@/features/workshop-panel/api";
import {
  type CalendarWindow,
  calendarWindow,
  formatMinutes,
  isFullHour,
  placeBlock,
  timeRowStarts,
} from "@/features/workshop-panel/calendar-layout";
import { usePanelWorkshop } from "@/features/workshop-panel/components/panel-shell";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import type { AppointmentStatus, StaffAppointment } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { addDays, type DayKey, isoWeekdayOf, todayKey, utcDateOf } from "@/lib/day-keys";
import { formatLongDay, formatTimeOfDay } from "@/lib/format";

type CalendarBay = {
  id: string;
  name: string;
};

const ROW_HEIGHT = "1.75rem";
const TIME_COLUMN_WIDTH = "4rem";
const BAY_COLUMN_MIN_WIDTH = "9rem";

const BLOCK_CLASS_NAMES: Record<AppointmentStatus, string> = {
  SCHEDULED: "border-primary/40 bg-primary/10",
  CHECKED_IN: "border-emerald-600/50 bg-emerald-500/15",
  NO_SHOW: "border-destructive/40 bg-destructive/10 line-through",
  CANCELLED: "border-border bg-muted",
};

function collectBays(
  activeBays: readonly CalendarBay[],
  appointments: readonly StaffAppointment[],
): CalendarBay[] {
  const bays = new Map(activeBays.map((bay) => [bay.id, bay]));
  for (const appointment of appointments) {
    if (!bays.has(appointment.bay.id)) {
      bays.set(appointment.bay.id, appointment.bay);
    }
  }
  return [...bays.values()];
}

function useAppointmentLabel(): (appointment: StaffAppointment) => string {
  const t = useTranslations();
  return (appointment) =>
    t("calendar.openLabel", {
      time: `${formatTimeOfDay(appointment.start_at)}–${formatTimeOfDay(appointment.end_at)}`,
      client: appointment.client.full_name,
      service: appointment.service_type.name,
      status: t(`appointmentStatus.${appointment.status}`),
    });
}

function CalendarGrid({
  bays,
  appointments,
  window,
  selectedId,
  onSelect,
}: {
  bays: readonly CalendarBay[];
  appointments: readonly StaffAppointment[];
  window: CalendarWindow;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const t = useTranslations("calendar");
  const appointmentLabel = useAppointmentLabel();
  const rows = timeRowStarts(window);
  const gridStyle: CSSProperties = {
    gridTemplateColumns: `${TIME_COLUMN_WIDTH} repeat(${bays.length}, minmax(${BAY_COLUMN_MIN_WIDTH}, 1fr))`,
    gridTemplateRows: `auto repeat(${rows.length}, ${ROW_HEIGHT})`,
  };

  return (
    <div className="hidden overflow-x-auto rounded-lg border md:block">
      <div role="group" aria-label={t("gridLabel")} className="grid min-w-fit" style={gridStyle}>
        <div className="sticky left-0 z-10 border-b bg-card p-2 text-xs text-muted-foreground">
          {t("time")}
        </div>
        {bays.map((bay, index) => (
          <div
            key={bay.id}
            className="border-b border-l p-2 text-sm font-medium"
            style={{ gridColumn: index + 2, gridRow: 1 }}
          >
            {bay.name}
          </div>
        ))}
        {rows.map((minutes, index) => (
          <div
            key={minutes}
            aria-hidden="true"
            className={cn(
              "sticky left-0 z-10 border-r bg-card pr-2 text-right text-xs text-muted-foreground tabular-nums",
              isFullHour(minutes) ? "border-t" : "",
            )}
            style={{ gridColumn: 1, gridRow: index + 2 }}
          >
            {isFullHour(minutes) ? formatMinutes(minutes) : null}
          </div>
        ))}
        {rows.map((minutes, rowIndex) =>
          bays.map((bay, bayIndex) => (
            <div
              key={`${bay.id}-${minutes}`}
              aria-hidden="true"
              className={cn(
                "border-l",
                isFullHour(minutes) ? "border-t" : "border-t border-dashed border-t-border/40",
              )}
              style={{ gridColumn: bayIndex + 2, gridRow: rowIndex + 2 }}
            />
          )),
        )}
        {appointments.map((appointment) => {
          const bayIndex = bays.findIndex((bay) => bay.id === appointment.bay.id);
          const placement = placeBlock(appointment, window);
          return (
            <button
              key={appointment.id}
              type="button"
              aria-pressed={appointment.id === selectedId}
              aria-label={appointmentLabel(appointment)}
              onClick={() => onSelect(appointment.id)}
              className={cn(
                "z-20 m-0.5 overflow-hidden rounded-md border p-1.5 text-left text-xs outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                BLOCK_CLASS_NAMES[appointment.status],
                appointment.id === selectedId ? "ring-2 ring-primary" : "",
              )}
              style={{
                gridColumn: bayIndex + 2,
                gridRow: `${placement.rowStart + 1} / span ${placement.rowSpan}`,
              }}
            >
              <span className="block font-medium tabular-nums">
                {formatTimeOfDay(appointment.start_at)}–{formatTimeOfDay(appointment.end_at)}
              </span>
              <span className="block truncate">{appointment.client.full_name}</span>
              <span className="block truncate text-muted-foreground">
                {appointment.service_type.name}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function CalendarList({
  bays,
  appointments,
  selectedId,
  onSelect,
}: {
  bays: readonly CalendarBay[];
  appointments: readonly StaffAppointment[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const appointmentLabel = useAppointmentLabel();
  return (
    <div className="grid gap-4 md:hidden">
      {bays.map((bay) => {
        const bayAppointments = appointments.filter((item) => item.bay.id === bay.id);
        if (bayAppointments.length === 0) {
          return null;
        }
        return (
          <section key={bay.id} className="grid gap-2" aria-labelledby={`bay-heading-${bay.id}`}>
            <h3 id={`bay-heading-${bay.id}`} className="font-medium">
              {bay.name}
            </h3>
            <ul className="grid gap-2">
              {bayAppointments.map((appointment) => (
                <li key={appointment.id}>
                  <button
                    type="button"
                    aria-pressed={appointment.id === selectedId}
                    aria-label={appointmentLabel(appointment)}
                    onClick={() => onSelect(appointment.id)}
                    className={cn(
                      "grid w-full gap-0.5 rounded-lg border p-3 text-left text-sm",
                      BLOCK_CLASS_NAMES[appointment.status],
                    )}
                  >
                    <span className="font-medium tabular-nums">
                      {formatTimeOfDay(appointment.start_at)}–{formatTimeOfDay(appointment.end_at)}
                    </span>
                    <span>{appointment.client.full_name}</span>
                    <span className="text-muted-foreground">{appointment.service_type.name}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

function AppointmentDetails({ appointment }: { appointment: StaffAppointment }) {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const { workshop } = usePanelWorkshop();
  const appointmentAction = useAppointmentAction(workshop.id);
  const [openedAt] = useState(() => Date.now());
  const hasStarted = new Date(appointment.start_at).getTime() <= openedAt;
  const run = (action: AppointmentAction) =>
    appointmentAction.mutate({ appointmentId: appointment.id, action });

  return (
    <SectionCard title={t("calendar.details")}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium tabular-nums">
          {formatTimeOfDay(appointment.start_at)}–{formatTimeOfDay(appointment.end_at)}
        </span>
        <AppointmentStatusBadge status={appointment.status} />
      </div>
      <dl className="grid gap-3 text-sm">
        <div>
          <dt className="text-muted-foreground">{t("calendar.client")}</dt>
          <dd className="font-medium">{appointment.client.full_name}</dd>
          {appointment.client.phone ? (
            <dd>
              <a
                href={`tel:${appointment.client.phone.replaceAll(" ", "")}`}
                className="inline-flex items-center gap-1 underline-offset-4 hover:underline"
              >
                <PhoneIcon aria-hidden="true" className="size-3.5" />
                {appointment.client.phone}
              </a>
            </dd>
          ) : null}
          <dd>
            <a
              href={`mailto:${appointment.client.email}`}
              className="inline-flex items-center gap-1 break-all underline-offset-4 hover:underline"
            >
              <MailIcon aria-hidden="true" className="size-3.5" />
              {appointment.client.email}
            </a>
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">{t("calendar.vehicle")}</dt>
          <dd>
            {appointment.vehicle.make} {appointment.vehicle.model} (
            {appointment.vehicle.production_year}){" "}
            <span className="font-mono">{appointment.vehicle.plate_number}</span>
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">{t("calendar.service")}</dt>
          <dd>{appointment.service_type.name}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">{t("calendar.bay")}</dt>
          <dd>{appointment.bay.name}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">{t("calendar.problem")}</dt>
          <dd className="whitespace-pre-line">
            {appointment.problem_description ?? t("calendar.noProblem")}
          </dd>
        </div>
      </dl>
      {appointmentAction.isError ? (
        <StatusMessage tone="error" message={errorMessage(appointmentAction.error)} />
      ) : null}
      {appointmentAction.isSuccess ? (
        <StatusMessage tone="success" message={t("calendar.updated")} />
      ) : null}
      <div className="flex flex-wrap gap-2">
        {appointment.status === "SCHEDULED" ? (
          <>
            <Button
              size="sm"
              disabled={appointmentAction.isPending}
              onClick={() => run("check-in")}
            >
              {t("calendar.checkIn")}
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={appointmentAction.isPending || !hasStarted}
              onClick={() => run("no-show")}
            >
              {t("calendar.noShow")}
            </Button>
          </>
        ) : null}
        {appointment.status === "SCHEDULED" || appointment.status === "CHECKED_IN" ? (
          <ConfirmButton
            label={t("calendar.cancel")}
            question={t("calendar.cancelQuestion", { name: appointment.client.full_name })}
            confirmLabel={t("common.confirmCancel")}
            dismissLabel={t("common.keep")}
            disabled={appointmentAction.isPending}
            onConfirm={() => run("cancel")}
          />
        ) : null}
      </div>
    </SectionCard>
  );
}

export function CalendarSection() {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const { workshop } = usePanelWorkshop();
  const [day, setDay] = useState<DayKey>(() => todayKey());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const detail = useStaffWorkshop(workshop.id);
  const appointments = useWorkshopAppointments(workshop.id, day);

  const allAppointments = appointments.data ?? [];
  const visibleAppointments = allAppointments.filter((item) => item.status !== "CANCELLED");
  const cancelledAppointments = allAppointments.filter((item) => item.status === "CANCELLED");
  const opening = detail.data?.opening_hours.find((entry) => entry.weekday === isoWeekdayOf(day));
  const activeBays = (detail.data?.bays ?? []).filter((bay) => bay.is_active);
  const bays = collectBays(activeBays, visibleAppointments);
  const window = calendarWindow(opening, visibleAppointments);
  const selected = allAppointments.find((item) => item.id === selectedId);

  const changeDay = (nextDay: DayKey) => {
    setDay(nextDay);
    setSelectedId(null);
  };

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid gap-1">
          <h2 className="text-lg font-semibold">{t("calendar.title")}</h2>
          <p className="text-muted-foreground first-letter:uppercase">
            {formatLongDay(utcDateOf(day))}
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <Button
            variant="outline"
            size="icon"
            aria-label={t("calendar.previousDay")}
            onClick={() => changeDay(addDays(day, -1))}
          >
            <ChevronLeftIcon aria-hidden="true" />
          </Button>
          <Button variant="outline" onClick={() => changeDay(todayKey())}>
            {t("calendar.today")}
          </Button>
          <Button
            variant="outline"
            size="icon"
            aria-label={t("calendar.nextDay")}
            onClick={() => changeDay(addDays(day, 1))}
          >
            <ChevronRightIcon aria-hidden="true" />
          </Button>
          <div className="grid gap-1">
            <Label htmlFor="calendar-day" className="sr-only">
              {t("calendar.dateLabel")}
            </Label>
            <Input
              id="calendar-day"
              type="date"
              className="w-40"
              value={day}
              onChange={(event) => {
                if (event.target.value) {
                  changeDay(event.target.value);
                }
              }}
            />
          </div>
        </div>
      </div>

      {detail.isError ? <StatusMessage tone="error" message={errorMessage(detail.error)} /> : null}
      {appointments.isError ? (
        <StatusMessage tone="error" message={errorMessage(appointments.error)} />
      ) : null}
      {appointments.isPending || detail.isPending ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("common.loading")}
        </p>
      ) : null}
      {detail.data && !opening ? (
        <StatusMessage tone="info" message={t("calendar.closed")} />
      ) : null}
      {appointments.data && visibleAppointments.length === 0 ? (
        <p className="text-muted-foreground">{t("calendar.empty")}</p>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem] xl:items-start">
        <div className="grid gap-4">
          {detail.data && bays.length > 0 ? (
            <CalendarGrid
              bays={bays}
              appointments={visibleAppointments}
              window={window}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          ) : null}
          <CalendarList
            bays={bays}
            appointments={visibleAppointments}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          {cancelledAppointments.length > 0 ? (
            <details className="rounded-lg border p-3 text-sm">
              <summary className="cursor-pointer font-medium">
                {t("calendar.cancelledList", { count: cancelledAppointments.length })}
              </summary>
              <ul className="mt-2 grid gap-1">
                {cancelledAppointments.map((appointment) => (
                  <li key={appointment.id}>
                    <button
                      type="button"
                      className="underline-offset-4 hover:underline"
                      onClick={() => setSelectedId(appointment.id)}
                    >
                      {formatTimeOfDay(appointment.start_at)} · {appointment.client.full_name} ·{" "}
                      {appointment.service_type.name}
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
        <aside className="xl:sticky xl:top-4">
          {selected ? (
            <AppointmentDetails key={selected.id} appointment={selected} />
          ) : (
            <p className="text-sm text-muted-foreground">{t("calendar.selectHint")}</p>
          )}
        </aside>
      </div>
    </div>
  );
}
