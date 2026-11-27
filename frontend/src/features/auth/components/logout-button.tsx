"use client";

import { LogOutIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { useLogout } from "@/features/auth/api";
import { useRouter } from "@/i18n/navigation";

export function LogoutButton() {
  const t = useTranslations("navigation");
  const router = useRouter();
  const logout = useLogout();

  return (
    <Button
      variant="ghost"
      disabled={logout.isPending}
      onClick={() => logout.mutate(undefined, { onSettled: () => router.replace("/login") })}
    >
      <LogOutIcon aria-hidden="true" />
      {t("logout")}
    </Button>
  );
}
