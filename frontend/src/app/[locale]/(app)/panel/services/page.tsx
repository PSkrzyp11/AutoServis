import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { ServicesSection } from "@/features/workshop-panel/components/services-section";

export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("panel");
  return { title: `${t("tabs.services")} | ${t("title")}` };
}

export default function PanelServicesPage() {
  return <ServicesSection />;
}
