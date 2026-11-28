"use client";

import { WrenchIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { buttonVariants } from "@/components/ui/button";
import { useCurrentUser } from "@/features/auth/api";
import { LogoutButton } from "@/features/auth/components/logout-button";
import { Link, usePathname } from "@/i18n/navigation";
import type { StaticAppPathname } from "@/i18n/routing";
import type { UserRole } from "@/lib/api/types";

type NavigationItem = {
  href: StaticAppPathname;
  labelKey: "account" | "vehicles" | "appointments" | "workshopPanel" | "users" | "adminWorkshops";
  roles: readonly UserRole[] | null;
  activePrefix: string;
};

const NAVIGATION_ITEMS: readonly NavigationItem[] = [
  {
    href: "/appointments",
    labelKey: "appointments",
    roles: null,
    activePrefix: "/appointments",
  },
  { href: "/vehicles", labelKey: "vehicles", roles: null, activePrefix: "/vehicles" },
  {
    href: "/panel/calendar",
    labelKey: "workshopPanel",
    roles: ["MANAGER", "MECHANIC"],
    activePrefix: "/panel",
  },
  {
    href: "/admin/workshops",
    labelKey: "adminWorkshops",
    roles: ["ADMIN"],
    activePrefix: "/admin/workshops",
  },
  { href: "/admin/users", labelKey: "users", roles: ["ADMIN"], activePrefix: "/admin/users" },
  { href: "/account", labelKey: "account", roles: null, activePrefix: "/account" },
];

export function AppHeader() {
  const t = useTranslations();
  const pathname = usePathname();
  const { data: user } = useCurrentUser();
  const visibleItems = NAVIGATION_ITEMS.filter(
    (item) => item.roles === null || (user !== undefined && item.roles.includes(user.role)),
  );

  return (
    <header className="border-b">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <WrenchIcon aria-hidden="true" className="size-5" />
          {t("common.appName")}
        </Link>
        <nav aria-label={t("navigation.label")} className="flex flex-wrap items-center gap-1">
          {visibleItems.map((item) => {
            const isCurrent = pathname.startsWith(item.activePrefix);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isCurrent ? "page" : undefined}
                className={buttonVariants({ variant: isCurrent ? "secondary" : "ghost" })}
              >
                {t(`navigation.${item.labelKey}`)}
              </Link>
            );
          })}
          <LogoutButton />
        </nav>
      </div>
    </header>
  );
}
