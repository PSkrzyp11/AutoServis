"use client";

import { CalendarCheckIcon, CarIcon, MapPinIcon } from "lucide-react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { type ReactNode, useMemo, useState } from "react";

import { SectionCard } from "@/components/section-card";
import { StatusMessage } from "@/components/status-message";
import { Button, buttonVariants } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useAvailability, useBookAppointment, usePublicWorkshop } from "@/features/booking/api";
import { buildBookingDays } from "@/features/booking/booking-days";
import { useVehicles } from "@/features/vehicles/api";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import { useFormatDuration } from "@/hooks/use-format-duration";
import { Link } from "@/i18n/navigation";
import { ApiError } from "@/lib/api/errors";
import type { Appointment, AvailableSlot, ServiceType, Vehicle } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { type DayKey, todayKey, utcDateOf } from "@/lib/day-keys";
import {
  formatCurrency,
  formatDate,
  formatDayMonth,
  formatLongDay,
  formatShortWeekday,
  formatTimeOfDay,
} from "@/lib/format";

const DESCRIPTION_MAX_LENGTH = 2000;
const STALE_SLOT_ERROR_CODES = new Set(["APPOINTMENT_SLOT_TAKEN", "SLOT_NOT_AVAILABLE"]);
const CHOICE_CLASS_NAME =
  "flex cursor-pointer items-start gap-3 rounded-lg border p-3 has-checked:border-primary has-checked:bg-primary/5 has-focus-visible:ring-3 has-focus-visible:ring-ring/50";

function ChoiceGroup({ legend, children }: { legend: string; children: ReactNode }) {
  return (
    <fieldset className="grid gap-3">
      <legend className="mb-3 text-lg font-semibold">{legend}</legend>
      {children}
    </fieldset>
  );
}

function ServiceChoice({
  service,
  checked,
  onSelect,
}: {
  service: ServiceType;
  checked: boolean;
  onSelect: () => void;
}) {
  const formatDuration = useFormatDuration();
  return (
    <label className={CHOICE_CLASS_NAME}>
      <input
        type="radio"
        name="service"
        value={service.id}
        className="mt-1 size-4"
        checked={checked}
        onChange={onSelect}
      />
      <span className="grid flex-1 gap-1">
        <span className="font-medium">{service.name}</span>
        <span className="text-sm text-muted-foreground">
          {formatDuration(service.duration_minutes)} · {formatCurrency(service.base_price_gross)}
        </span>
      </span>
    </label>
  );
}

function VehicleChoice({
  vehicle,
  checked,
  onSelect,
}: {
  vehicle: Vehicle;
  checked: boolean;
  onSelect: () => void;
}) {
  return (
    <label className={CHOICE_CLASS_NAME}>
      <input
        type="radio"
        name="vehicle"
        value={vehicle.id}
        className="mt-1 size-4"
        checked={checked}
        onChange={onSelect}
      />
      <span className="flex flex-1 items-center gap-2">
        <CarIcon aria-hidden="true" className="size-4 shrink-0" />
        <span className="font-medium">
          {vehicle.make} {vehicle.model}
        </span>
        <span className="font-mono text-sm text-muted-foreground">{vehicle.plate_number}</span>
      </span>
    </label>
  );
}

function BookingSuccess({ appointment }: { appointment: Appointment }) {
  const t = useTranslations("booking");
  return (
    <SectionCard title={t("successTitle")} description={t("successDescription")}>
      <div role="status" className="flex items-start gap-3">
        <CalendarCheckIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        <div className="grid gap-1">
          <p className="font-medium">{appointment.service_type.name}</p>
          <p>
            {t("whenValue", {
              date: formatDate(appointment.start_at),
              start: formatTimeOfDay(appointment.start_at),
              end: formatTimeOfDay(appointment.end_at),
            })}
          </p>
          <p className="text-muted-foreground">
            {appointment.workshop.name}, {appointment.workshop.street}, {appointment.workshop.city}
          </p>
        </div>
      </div>
      <Link href="/appointments" className={buttonVariants({ className: "justify-self-start" })}>
        {t("goToAppointments")}
      </Link>
    </SectionCard>
  );
}

export function BookingView() {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const { slug } = useParams<{ slug: string }>();
  const workshop = usePublicWorkshop(slug);
  const vehicles = useVehicles();
  const bookAppointment = useBookAppointment();
  const [serviceTypeId, setServiceTypeId] = useState<string | null>(null);
  const [chosenVehicleId, setChosenVehicleId] = useState<string | null>(null);
  const [day, setDay] = useState<DayKey | null>(null);
  const [slot, setSlot] = useState<AvailableSlot | null>(null);
  const [description, setDescription] = useState("");
  const [showIncomplete, setShowIncomplete] = useState(false);
  const availability = useAvailability(workshop.data?.id, serviceTypeId, day);

  const vehicleItems = vehicles.data?.items ?? [];
  const onlyVehicle = vehicleItems.length === 1 ? vehicleItems[0] : undefined;
  const vehicleId = chosenVehicleId ?? onlyVehicle?.id ?? null;
  const bookingDays = useMemo(
    () =>
      workshop.data
        ? buildBookingDays(todayKey(), workshop.data.opening_hours, workshop.data.upcoming_closures)
        : [],
    [workshop.data],
  );

  if (workshop.isPending) {
    return (
      <p role="status" className="text-sm text-muted-foreground">
        {t("common.loading")}
      </p>
    );
  }
  if (workshop.isError) {
    return <StatusMessage tone="error" message={errorMessage(workshop.error)} />;
  }
  if (bookAppointment.isSuccess) {
    return <BookingSuccess appointment={bookAppointment.data} />;
  }

  const services = workshop.data.service_types;
  const selectedService = services.find((service) => service.id === serviceTypeId);
  const selectedVehicle = vehicleItems.find((vehicle) => vehicle.id === vehicleId);

  const selectService = (id: string) => {
    setServiceTypeId(id);
    setSlot(null);
  };
  const selectDay = (key: DayKey) => {
    setDay(key);
    setSlot(null);
  };

  const submit = () => {
    if (!serviceTypeId || !vehicleId || !slot) {
      setShowIncomplete(true);
      return;
    }
    setShowIncomplete(false);
    bookAppointment.mutate(
      {
        workshop_id: workshop.data.id,
        service_type_id: serviceTypeId,
        vehicle_id: vehicleId,
        start_at: slot.start_at,
        problem_description: description.trim() === "" ? null : description.trim(),
      },
      {
        onError: (error) => {
          if (error instanceof ApiError && STALE_SLOT_ERROR_CODES.has(error.code)) {
            setSlot(null);
          }
        },
      },
    );
  };

  return (
    <div className="grid gap-6">
      <header className="grid gap-1">
        <h1 className="text-2xl font-semibold">{t("booking.title")}</h1>
        <p className="flex items-center gap-2 text-muted-foreground">
          <MapPinIcon aria-hidden="true" className="size-4" />
          {workshop.data.name}, {workshop.data.street}, {workshop.data.city}
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
        <div className="grid gap-8">
          <ChoiceGroup legend={t("booking.serviceStep")}>
            {services.length === 0 ? (
              <p className="text-muted-foreground">{t("booking.noServices")}</p>
            ) : (
              services.map((service) => (
                <ServiceChoice
                  key={service.id}
                  service={service}
                  checked={service.id === serviceTypeId}
                  onSelect={() => selectService(service.id)}
                />
              ))
            )}
          </ChoiceGroup>

          <ChoiceGroup legend={t("booking.vehicleStep")}>
            {vehicles.isPending ? (
              <p role="status" className="text-sm text-muted-foreground">
                {t("common.loading")}
              </p>
            ) : null}
            {vehicles.data && vehicleItems.length === 0 ? (
              <div className="grid gap-3">
                <p className="text-muted-foreground">{t("booking.noVehicles")}</p>
                <Link
                  href="/vehicles"
                  className={buttonVariants({
                    variant: "outline",
                    className: "justify-self-start",
                  })}
                >
                  {t("booking.addVehicle")}
                </Link>
              </div>
            ) : null}
            {vehicleItems.map((vehicle) => (
              <VehicleChoice
                key={vehicle.id}
                vehicle={vehicle}
                checked={vehicle.id === vehicleId}
                onSelect={() => setChosenVehicleId(vehicle.id)}
              />
            ))}
          </ChoiceGroup>

          <section className="grid gap-3" aria-labelledby="booking-day-heading">
            <h2 id="booking-day-heading" className="text-lg font-semibold">
              {t("booking.dayStep")}
            </h2>
            <ul className="flex gap-2 overflow-x-auto pb-2" aria-label={t("booking.daysLabel")}>
              {bookingDays.map((bookingDay) => {
                const date = utcDateOf(bookingDay.key);
                const isSelected = bookingDay.key === day;
                return (
                  <li key={bookingDay.key}>
                    <button
                      type="button"
                      disabled={!bookingDay.isOpen}
                      aria-pressed={isSelected}
                      aria-label={formatLongDay(date)}
                      onClick={() => selectDay(bookingDay.key)}
                      className={cn(
                        "grid w-20 gap-0.5 rounded-lg border p-2 text-center text-sm transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50",
                        isSelected
                          ? "border-primary bg-primary text-primary-foreground"
                          : "hover:bg-muted",
                      )}
                    >
                      <span className="capitalize">{formatShortWeekday(date)}</span>
                      <span className="font-medium">{formatDayMonth(date)}</span>
                      {bookingDay.isOpen ? null : (
                        <span className="text-xs">{t("booking.closedDay")}</span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="grid gap-3" aria-labelledby="booking-time-heading">
            <h2 id="booking-time-heading" className="text-lg font-semibold">
              {t("booking.timeStep")}
            </h2>
            <div aria-live="polite">
              {!serviceTypeId || !day ? (
                <p className="text-muted-foreground">{t("booking.chooseFirst")}</p>
              ) : null}
              {availability.isFetching && !availability.data ? (
                <p className="text-muted-foreground">{t("booking.loadingSlots")}</p>
              ) : null}
              {availability.isError ? (
                <StatusMessage tone="error" message={errorMessage(availability.error)} />
              ) : null}
              {availability.data && availability.data.slots.length === 0 ? (
                <p className="text-muted-foreground">{t("booking.noSlots")}</p>
              ) : null}
            </div>
            {availability.data && availability.data.slots.length > 0 && day ? (
              <ul
                className="grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-6"
                aria-label={t("booking.slotsLabel", { date: formatLongDay(utcDateOf(day)) })}
              >
                {availability.data.slots.map((availableSlot) => {
                  const isSelected = slot?.start_at === availableSlot.start_at;
                  return (
                    <li key={availableSlot.start_at}>
                      <Button
                        type="button"
                        variant={isSelected ? "default" : "outline"}
                        className="w-full tabular-nums"
                        aria-pressed={isSelected}
                        onClick={() => setSlot(availableSlot)}
                      >
                        {formatTimeOfDay(availableSlot.start_at)}
                      </Button>
                    </li>
                  );
                })}
              </ul>
            ) : null}
          </section>

          <section className="grid gap-3" aria-labelledby="booking-description-heading">
            <h2 id="booking-description-heading" className="text-lg font-semibold">
              {t("booking.descriptionStep")}
            </h2>
            <Label htmlFor="booking-description" className="sr-only">
              {t("booking.descriptionLabel")}
            </Label>
            <textarea
              id="booking-description"
              rows={4}
              maxLength={DESCRIPTION_MAX_LENGTH}
              value={description}
              placeholder={t("booking.descriptionPlaceholder")}
              onChange={(event) => setDescription(event.target.value)}
              className="w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-base outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm dark:bg-input/30"
            />
          </section>
        </div>

        <aside className="lg:sticky lg:top-4">
          <SectionCard title={t("booking.summaryTitle")}>
            <dl className="grid gap-3 text-sm">
              <div>
                <dt className="text-muted-foreground">{t("booking.summaryService")}</dt>
                <dd className="font-medium">{selectedService?.name ?? t("booking.notSelected")}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t("booking.summaryVehicle")}</dt>
                <dd className="font-medium">
                  {selectedVehicle
                    ? t("booking.vehicleOption", {
                        make: selectedVehicle.make,
                        model: selectedVehicle.model,
                        plate: selectedVehicle.plate_number,
                      })
                    : t("booking.notSelected")}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">{t("booking.summaryWhen")}</dt>
                <dd className="font-medium">
                  {slot
                    ? t("booking.whenValue", {
                        date: formatDate(slot.start_at),
                        start: formatTimeOfDay(slot.start_at),
                        end: formatTimeOfDay(slot.end_at),
                      })
                    : t("booking.notSelected")}
                </dd>
              </div>
              {selectedService ? (
                <div>
                  <dt className="text-muted-foreground">{t("booking.summaryPrice")}</dt>
                  <dd className="font-medium">
                    {formatCurrency(selectedService.base_price_gross)}
                  </dd>
                </div>
              ) : null}
            </dl>
            {showIncomplete ? (
              <StatusMessage tone="error" message={t("booking.incomplete")} />
            ) : null}
            {bookAppointment.isError ? (
              <StatusMessage tone="error" message={errorMessage(bookAppointment.error)} />
            ) : null}
            <Button size="lg" disabled={bookAppointment.isPending} onClick={submit}>
              {bookAppointment.isPending ? t("booking.submitting") : t("booking.submit")}
            </Button>
          </SectionCard>
        </aside>
      </div>
    </div>
  );
}
