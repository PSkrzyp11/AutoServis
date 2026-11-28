import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";

import { BookingView } from "@/features/booking/components/booking-view";

export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("booking");
  return { title: t("title") };
}

export default function BookingPage() {
  return (
    <Suspense>
      <BookingView />
    </Suspense>
  );
}
