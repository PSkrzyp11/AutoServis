import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";

import { WorkshopDetail } from "@/features/workshops/components/workshop-detail";
import { getWorkshopBySlug } from "@/features/workshops/server";

export async function generateMetadata({
  params,
}: PageProps<"/[locale]/workshops/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const workshop = await getWorkshopBySlug(slug);
  return {
    title: workshop.name,
    description: `${workshop.street}, ${workshop.postal_code} ${workshop.city}`,
  };
}

export default async function WorkshopDetailPage({
  params,
}: PageProps<"/[locale]/workshops/[slug]">) {
  const t = await getTranslations("common");
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <Suspense
        fallback={
          <p role="status" className="text-sm text-muted-foreground">
            {t("loading")}
          </p>
        }
      >
        <WorkshopDetail params={params} />
      </Suspense>
    </div>
  );
}
