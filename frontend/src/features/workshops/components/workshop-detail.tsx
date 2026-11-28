import { ArrowLeftIcon, CalendarPlusIcon, MailIcon, MapPinIcon, PhoneIcon } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getWorkshopBySlug } from "@/features/workshops/server";
import { buttonVariants } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";
import type { OpeningHoursEntry, ServiceType } from "@/lib/api/types";
import { splitDuration } from "@/lib/duration";
import { formatCurrency, formatDate, formatTime, formatWeekday } from "@/lib/format";

const ISO_WEEKDAYS = [1, 2, 3, 4, 5, 6, 7] as const;

async function OpeningHoursCard({ openingHours }: { openingHours: OpeningHoursEntry[] }) {
  const t = await getTranslations("workshopDetail");
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <h2 className="text-lg font-semibold">{t("openingHours")}</h2>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableCaption className="sr-only">{t("openingHours")}</TableCaption>
          <TableHeader className="sr-only">
            <TableRow>
              <TableHead scope="col">{t("weekday")}</TableHead>
              <TableHead scope="col">{t("hours")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {ISO_WEEKDAYS.map((weekday) => {
              const entry = openingHours.find((day) => day.weekday === weekday);
              return (
                <TableRow key={weekday}>
                  <TableHead scope="row" className="font-normal">
                    {formatWeekday(weekday)}
                  </TableHead>
                  <TableCell className="text-right tabular-nums">
                    {entry
                      ? `${formatTime(entry.opens_at)}–${formatTime(entry.closes_at)}`
                      : t("closed")}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

async function ServicesCard({ services }: { services: ServiceType[] }) {
  const t = await getTranslations("workshopDetail");
  const tCommon = await getTranslations("common");
  const formatDuration = (totalMinutes: number) => {
    const { hours, minutes } = splitDuration(totalMinutes);
    return hours === 0
      ? tCommon("durationMinutes", { minutes })
      : tCommon("durationHours", { hours, minutes });
  };

  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <CardTitle>
          <h2 className="text-lg font-semibold">{t("services")}</h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        {services.length === 0 ? (
          <p className="text-muted-foreground">{t("noServices")}</p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableCaption className="sr-only">{t("services")}</TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">{t("serviceName")}</TableHead>
                  <TableHead scope="col">{t("duration")}</TableHead>
                  <TableHead scope="col" className="text-right">
                    {t("priceGross")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {services.map((service) => (
                  <TableRow key={service.id}>
                    <TableCell className="whitespace-normal">{service.name}</TableCell>
                    <TableCell>{formatDuration(service.duration_minutes)}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatCurrency(service.base_price_gross)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        <p className="text-sm text-muted-foreground">{t("priceNote")}</p>
      </CardContent>
    </Card>
  );
}

export async function WorkshopDetail({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const [workshop, t] = await Promise.all([
    getWorkshopBySlug(slug),
    getTranslations("workshopDetail"),
  ]);

  return (
    <div className="grid gap-6">
      <Link
        href="/workshops"
        className="flex items-center gap-2 text-sm underline-offset-4 hover:underline"
      >
        <ArrowLeftIcon aria-hidden="true" className="size-4" />
        {t("backToSearch")}
      </Link>
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid gap-1">
          <h1 className="text-3xl font-semibold text-balance">{workshop.name}</h1>
          <p className="text-muted-foreground">
            {workshop.street}, {workshop.postal_code} {workshop.city}
          </p>
        </div>
        {workshop.service_types.length > 0 ? (
          <Link
            href={{ pathname: "/workshops/[slug]/booking", params: { slug: workshop.slug } }}
            className={buttonVariants({ size: "lg" })}
          >
            <CalendarPlusIcon aria-hidden="true" />
            {t("book")}
          </Link>
        ) : null}
      </header>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>
              <h2 className="text-lg font-semibold">{t("contact")}</h2>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-3 text-sm">
              <div className="flex items-start gap-2">
                <MapPinIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
                <dt className="sr-only">{t("address")}</dt>
                <dd>
                  {workshop.street}, {workshop.postal_code} {workshop.city}
                </dd>
              </div>
              <div className="flex items-center gap-2">
                <PhoneIcon aria-hidden="true" className="size-4 shrink-0" />
                <dt className="sr-only">{t("phone")}</dt>
                <dd>
                  <a
                    href={`tel:${workshop.phone.replaceAll(" ", "")}`}
                    className="underline-offset-4 hover:underline"
                  >
                    {workshop.phone}
                  </a>
                </dd>
              </div>
              <div className="flex items-center gap-2">
                <MailIcon aria-hidden="true" className="size-4 shrink-0" />
                <dt className="sr-only">{t("email")}</dt>
                <dd className="break-all">
                  <a
                    href={`mailto:${workshop.email}`}
                    className="underline-offset-4 hover:underline"
                  >
                    {workshop.email}
                  </a>
                </dd>
              </div>
            </dl>
            <h3 className="mt-6 mb-2 font-medium">{t("upcomingClosures")}</h3>
            {workshop.upcoming_closures.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("noClosures")}</p>
            ) : (
              <ul className="grid gap-1 text-sm">
                {workshop.upcoming_closures.map((closure) => (
                  <li key={closure.id}>
                    <time dateTime={closure.closed_on}>{formatDate(closure.closed_on)}</time>
                    {closure.reason ? ` – ${closure.reason}` : null}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
        <OpeningHoursCard openingHours={workshop.opening_hours} />
        <ServicesCard services={workshop.service_types} />
      </div>
    </div>
  );
}
