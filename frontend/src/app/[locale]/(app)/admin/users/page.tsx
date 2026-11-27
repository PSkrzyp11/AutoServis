import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { AuthGuard } from "@/features/auth/components/auth-guard";
import { AdminUsersView } from "@/features/users/components/admin-users-view";

export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("adminUsers");
  return { title: t("title") };
}

export default function AdminUsersPage() {
  return (
    <AuthGuard requiredRole="ADMIN">
      <AdminUsersView />
    </AuthGuard>
  );
}
