import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { TeamSection } from "@/features/workshop-panel/components/team-section";

export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("panel");
  return { title: `${t("tabs.team")} | ${t("title")}` };
}

export default function PanelTeamPage() {
  return <TeamSection />;
}
