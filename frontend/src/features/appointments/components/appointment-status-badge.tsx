import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import type { AppointmentStatus } from "@/lib/api/types";

const STATUS_BADGE_VARIANTS = {
  SCHEDULED: "default",
  CHECKED_IN: "secondary",
  CANCELLED: "outline",
  NO_SHOW: "destructive",
} as const satisfies Record<AppointmentStatus, "default" | "secondary" | "outline" | "destructive">;

export function AppointmentStatusBadge({ status }: { status: AppointmentStatus }) {
  const t = useTranslations("appointmentStatus");
  return <Badge variant={STATUS_BADGE_VARIANTS[status]}>{t(status)}</Badge>;
}
