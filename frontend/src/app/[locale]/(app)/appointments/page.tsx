import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { MyAppointmentsView } from "@/features/appointments/components/my-appointments-view";

export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("appointments");
  return { title: t("title") };
}

export default function AppointmentsPage() {
  return <MyAppointmentsView />;
}
