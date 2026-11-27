import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { BaysSection } from "@/features/workshop-panel/components/bays-section";

export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("panel");
  return { title: `${t("tabs.bays")} | ${t("title")}` };
}

export default function PanelBaysPage() {
  return <BaysSection />;
}
