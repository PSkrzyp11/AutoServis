import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { WorkshopSearchResults } from "@/features/workshops/components/workshop-search-results";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("workshopSearch");
  return { title: t("title"), description: t("description") };
}

export default async function WorkshopSearchPage({
  searchParams,
}: PageProps<"/[locale]/workshops">) {
  const t = await getTranslations();
  return (
    <div className="mx-auto grid w-full max-w-5xl gap-6 px-4 py-8">
      <PageHeader title={t("workshopSearch.title")} description={t("workshopSearch.description")} />
      <Suspense
        fallback={
          <p role="status" className="text-sm text-muted-foreground">
            {t("common.loading")}
          </p>
        }
      >
        <WorkshopSearchResults searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
