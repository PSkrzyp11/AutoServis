"use client";

import { MailIcon, PhoneIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { SectionCard } from "@/components/section-card";
import { StatusMessage } from "@/components/status-message";
import { useWorkshopMembers } from "@/features/workshop-panel/api";
import { usePanelWorkshop } from "@/features/workshop-panel/components/panel-shell";
import { RoleBadge } from "@/features/users/components/role-badge";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";

export function TeamSection() {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const { workshop } = usePanelWorkshop();
  const members = useWorkshopMembers(workshop.id);

  return (
    <SectionCard title={t("panel.team.title")} description={t("panel.team.description")}>
      {members.isError ? (
        <StatusMessage tone="error" message={errorMessage(members.error)} />
      ) : null}
      {members.isPending ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("common.loading")}
        </p>
      ) : null}
      {members.data?.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("panel.team.empty")}</p>
      ) : null}
      {members.data && members.data.length > 0 ? (
        <ul className="grid gap-4 sm:grid-cols-2">
          {members.data.map((member) => (
            <li key={member.user_id} className="grid gap-2 rounded-lg border p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium">{member.full_name}</span>
                <RoleBadge role={member.role} />
              </div>
              <a
                href={`mailto:${member.email}`}
                className="flex items-center gap-2 text-sm break-all underline-offset-4 hover:underline"
              >
                <MailIcon aria-hidden="true" className="size-4 shrink-0" />
                {member.email}
              </a>
              {member.phone ? (
                <a
                  href={`tel:${member.phone.replaceAll(" ", "")}`}
                  className="flex items-center gap-2 text-sm underline-offset-4 hover:underline"
                >
                  <PhoneIcon aria-hidden="true" className="size-4 shrink-0" />
                  {member.phone}
                </a>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </SectionCard>
  );
}
