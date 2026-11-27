import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { WorkshopSection } from "@/features/workshop-panel/components/workshop-section";

export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("panel");
  return { title: `${t("tabs.workshop")} | ${t("title")}` };
}

export default function PanelWorkshopPage() {
  return <WorkshopSection />;
}
