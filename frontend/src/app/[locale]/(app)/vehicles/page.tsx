import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { VehiclesView } from "@/features/vehicles/components/vehicles-view";

export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("vehicles");
  return { title: t("title") };
}

export default function VehiclesPage() {
  return <VehiclesView />;
}
