import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { CalendarSection } from "@/features/workshop-panel/components/calendar-section";

export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("panel");
  return { title: `${t("tabs.calendar")} | ${t("title")}` };
}

export default function PanelCalendarPage() {
  return <CalendarSection />;
}
