import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import type { UserRole } from "@/lib/api/types";

const ROLE_BADGE_VARIANTS = {
  CLIENT: "secondary",
  MECHANIC: "outline",
  MANAGER: "outline",
  ADMIN: "default",
} as const satisfies Record<UserRole, "default" | "secondary" | "outline">;

export function RoleBadge({ role }: { role: UserRole }) {
  const t = useTranslations("roles");
  return <Badge variant={ROLE_BADGE_VARIANTS[role]}>{t(role)}</Badge>;
}
