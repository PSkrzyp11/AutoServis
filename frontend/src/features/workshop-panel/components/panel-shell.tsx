"use client";

import { useTranslations } from "next-intl";
import { createContext, type ReactNode, useContext, useState } from "react";

import { SelectField } from "@/components/native-select";
import { StatusMessage } from "@/components/status-message";
import { buttonVariants } from "@/components/ui/button";
import { useCurrentUser } from "@/features/auth/api";
import { useMyWorkshops } from "@/features/workshop-panel/api";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import { Link, usePathname } from "@/i18n/navigation";
import type { StaticAppPathname } from "@/i18n/routing";
import type { WorkshopSummary } from "@/lib/api/types";

type PanelContextValue = {
  workshop: WorkshopSummary;
  canManage: boolean;
};

const PanelContext = createContext<PanelContextValue | null>(null);

export function usePanelWorkshop(): PanelContextValue {
  const value = useContext(PanelContext);
  if (value === null) {
    throw new Error("usePanelWorkshop must be used inside PanelShell");
  }
  return value;
}

type PanelTab = {
  href: StaticAppPathname;
  labelKey: "workshop" | "bays" | "services" | "team";
};

const PANEL_TABS: readonly PanelTab[] = [
  { href: "/panel/workshop", labelKey: "workshop" },
  { href: "/panel/bays", labelKey: "bays" },
  { href: "/panel/services", labelKey: "services" },
  { href: "/panel/team", labelKey: "team" },
];

function PanelTabs() {
  const t = useTranslations("panel");
  const pathname = usePathname();
  return (
    <nav aria-label={t("sectionsLabel")} className="flex flex-wrap gap-1 border-b pb-2">
      {PANEL_TABS.map((tab) => {
        const isCurrent = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={isCurrent ? "page" : undefined}
            className={buttonVariants({ variant: isCurrent ? "secondary" : "ghost", size: "sm" })}
          >
            {t(`tabs.${tab.labelKey}`)}
          </Link>
        );
      })}
    </nav>
  );
}

export function PanelShell({ children }: { children: ReactNode }) {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const { data: user } = useCurrentUser();
  const workshops = useMyWorkshops();
  const [selectedWorkshopId, setSelectedWorkshopId] = useState<string | null>(null);

  if (workshops.isPending) {
    return (
      <p role="status" className="text-sm text-muted-foreground">
        {t("common.loading")}
      </p>
    );
  }
  if (workshops.isError) {
    return <StatusMessage tone="error" message={errorMessage(workshops.error)} />;
  }

  const workshop =
    workshops.data.find((item) => item.id === selectedWorkshopId) ?? workshops.data[0];
  if (workshop === undefined) {
    return <StatusMessage tone="info" message={t("panel.noWorkshops")} />;
  }
  const canManage = user?.role === "MANAGER";

  return (
    <div className="grid gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid gap-1">
          <h1 className="text-2xl font-semibold">{t("panel.title")}</h1>
          <p className="text-muted-foreground">
            {workshop.name}, {workshop.city}
          </p>
        </div>
        {workshops.data.length > 1 ? (
          <SelectField
            id="workshop-switcher"
            label={t("panel.workshopSwitcher")}
            value={workshop.id}
            onChange={(event) => setSelectedWorkshopId(event.target.value)}
          >
            {workshops.data.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </SelectField>
        ) : null}
      </header>
      {canManage ? null : <StatusMessage tone="info" message={t("panel.readOnly")} />}
      <PanelTabs />
      <PanelContext.Provider value={{ workshop, canManage }}>{children}</PanelContext.Provider>
    </div>
  );
}
