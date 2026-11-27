import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { AdminWorkshopsView } from "@/features/admin-workshops/components/admin-workshops-view";
import { AuthGuard } from "@/features/auth/components/auth-guard";
import { ADMIN_ROLES } from "@/lib/api/types";

export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("adminWorkshops");
  return { title: t("title") };
}

export default function AdminWorkshopsPage() {
  return (
    <AuthGuard allowedRoles={ADMIN_ROLES}>
      <AdminWorkshopsView />
    </AuthGuard>
  );
}
