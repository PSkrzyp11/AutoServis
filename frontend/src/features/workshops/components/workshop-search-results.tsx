import { MapPinIcon, PhoneIcon } from "lucide-react";
import Form from "next/form";
import { getLocale, getTranslations } from "next-intl/server";

import { NativeSelect } from "@/components/native-select";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  buildWorkshopSearchQuery,
  parseWorkshopSearchParams,
  type RawSearchParams,
  WORKSHOP_SEARCH_PAGE_SIZE,
  type WorkshopSearchQuery,
} from "@/features/workshops/search-params";
import { listWorkshopCities, searchWorkshops } from "@/features/workshops/server";
import { getPathname, Link } from "@/i18n/navigation";
import type { WorkshopSummary } from "@/lib/api/types";

async function WorkshopCard({ workshop }: { workshop: WorkshopSummary }) {
  const t = await getTranslations("workshopSearch");
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>
          <h2 className="text-lg font-semibold">{workshop.name}</h2>
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 text-sm">
        <p className="flex items-start gap-2">
          <MapPinIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          <span>
            {workshop.street}, {workshop.postal_code} {workshop.city}
          </span>
        </p>
        <p className="flex items-center gap-2">
          <PhoneIcon aria-hidden="true" className="size-4 shrink-0" />
          <a
            href={`tel:${workshop.phone.replaceAll(" ", "")}`}
            className="underline-offset-4 hover:underline"
          >
            {workshop.phone}
          </a>
        </p>
        <Link
          href={{ pathname: "/workshops/[slug]", params: { slug: workshop.slug } }}
          className={buttonVariants({ variant: "outline", className: "justify-self-start" })}
          aria-label={t("showDetails", { name: workshop.name })}
        >
          {t("detailsLink")}
        </Link>
      </CardContent>
    </Card>
  );
}

async function SearchForm({ cities, query }: { cities: string[]; query: WorkshopSearchQuery }) {
  const t = await getTranslations("workshopSearch");
  const locale = await getLocale();
  return (
    <Form
      action={getPathname({ href: "/workshops", locale })}
      role="search"
      className="grid gap-4 sm:grid-cols-[minmax(0,12rem)_minmax(0,1fr)_auto] sm:items-end"
    >
      <div className="grid gap-2">
        <Label htmlFor="city">{t("cityLabel")}</Label>
        <NativeSelect id="city" name="city" defaultValue={query.city}>
          <option value="">{t("allCities")}</option>
          {cities.map((city) => (
            <option key={city} value={city}>
              {city}
            </option>
          ))}
        </NativeSelect>
      </div>
      <div className="grid gap-2">
        <Label htmlFor="search">{t("nameLabel")}</Label>
        <Input
          id="search"
          name="search"
          type="search"
          defaultValue={query.search}
          placeholder={t("namePlaceholder")}
        />
      </div>
      <Button type="submit">{t("submit")}</Button>
    </Form>
  );
}

async function SearchPagination({ query, total }: { query: WorkshopSearchQuery; total: number }) {
  const t = await getTranslations("common");
  const lastPage = Math.max(Math.ceil(total / WORKSHOP_SEARCH_PAGE_SIZE), 1);
  if (lastPage === 1) {
    return null;
  }
  const from = (query.page - 1) * WORKSHOP_SEARCH_PAGE_SIZE + 1;
  const to = Math.min(query.page * WORKSHOP_SEARCH_PAGE_SIZE, total);
  return (
    <nav aria-label={t("pagination")} className="flex flex-wrap items-center justify-between gap-4">
      <p className="text-sm text-muted-foreground">{t("summary", { from, to, total })}</p>
      <div className="flex gap-2">
        {query.page > 1 ? (
          <Link
            href={{
              pathname: "/workshops",
              query: buildWorkshopSearchQuery(query, query.page - 1),
            }}
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            {t("previousPage")}
          </Link>
        ) : null}
        {query.page < lastPage ? (
          <Link
            href={{
              pathname: "/workshops",
              query: buildWorkshopSearchQuery(query, query.page + 1),
            }}
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            {t("nextPage")}
          </Link>
        ) : null}
      </div>
    </nav>
  );
}

export async function WorkshopSearchResults({
  searchParams,
}: {
  searchParams: Promise<RawSearchParams>;
}) {
  const query = parseWorkshopSearchParams(await searchParams);
  const [cities, results, t] = await Promise.all([
    listWorkshopCities(),
    searchWorkshops(query),
    getTranslations("workshopSearch"),
  ]);

  return (
    <div className="grid gap-6">
      <SearchForm cities={cities} query={query} />
      <div className="grid gap-1" role="status">
        <p className="font-medium">{t("resultsCount", { total: results.total })}</p>
        {results.total === 0 ? <p className="text-muted-foreground">{t("empty")}</p> : null}
      </div>
      {results.items.length > 0 ? (
        <ul className="grid gap-4 sm:grid-cols-2">
          {results.items.map((workshop) => (
            <li key={workshop.id}>
              <WorkshopCard workshop={workshop} />
            </li>
          ))}
        </ul>
      ) : null}
      <SearchPagination query={query} total={results.total} />
    </div>
  );
}
