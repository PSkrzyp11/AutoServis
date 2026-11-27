"use client";

import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { ConfirmButton } from "@/components/confirm-button";
import { SelectField } from "@/components/native-select";
import { StatusMessage } from "@/components/status-message";
import { Button } from "@/components/ui/button";
import {
  useAssignMember,
  useRemoveMember,
  useStaffCandidates,
} from "@/features/admin-workshops/api";
import { RoleBadge } from "@/features/users/components/role-badge";
import { useWorkshopMembers } from "@/features/workshop-panel/api";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import type { WorkshopRead } from "@/lib/api/types";

export function WorkshopMembersManager({ workshop }: { workshop: WorkshopRead }) {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const members = useWorkshopMembers(workshop.id);
  const candidates = useStaffCandidates();
  const assignMember = useAssignMember(workshop.id);
  const removeMember = useRemoveMember(workshop.id);
  const [selectedUserId, setSelectedUserId] = useState("");

  const memberIds = new Set(members.data?.map((member) => member.user_id));
  const availableCandidates = (candidates.data ?? []).filter((user) => !memberIds.has(user.id));
  const selectId = `member-candidate-${workshop.id}`;
  const mutationError = assignMember.error ?? removeMember.error;

  const onAssign = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedUserId !== "") {
      assignMember.mutate(selectedUserId, { onSuccess: () => setSelectedUserId("") });
    }
  };

  return (
    <section
      className="grid gap-4 rounded-lg bg-muted/40 p-4"
      aria-labelledby={`${selectId}-title`}
    >
      <h3 id={`${selectId}-title`} className="font-medium">
        {t("adminWorkshops.members.title", { name: workshop.name })}
      </h3>
      {mutationError ? <StatusMessage tone="error" message={errorMessage(mutationError)} /> : null}
      {members.isError ? (
        <StatusMessage tone="error" message={errorMessage(members.error)} />
      ) : null}
      {members.data?.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("adminWorkshops.members.empty")}</p>
      ) : null}
      {members.data && members.data.length > 0 ? (
        <ul className="grid gap-2">
          {members.data.map((member) => (
            <li
              key={member.user_id}
              className="flex flex-wrap items-center justify-between gap-2 text-sm"
            >
              <span className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{member.full_name}</span>
                <RoleBadge role={member.role} />
                <span className="text-muted-foreground">{member.email}</span>
              </span>
              <ConfirmButton
                label={t("adminWorkshops.members.remove")}
                accessibleLabel={t("adminWorkshops.members.removeLabel", {
                  name: member.full_name,
                })}
                question={t("adminWorkshops.members.removeLabel", { name: member.full_name })}
                disabled={removeMember.isPending}
                onConfirm={() => removeMember.mutate(member.user_id)}
              />
            </li>
          ))}
        </ul>
      ) : null}
      {candidates.isSuccess && availableCandidates.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("adminWorkshops.members.noCandidates")}</p>
      ) : null}
      {availableCandidates.length > 0 ? (
        <form
          className="flex flex-wrap items-end gap-2"
          method="post"
          noValidate
          onSubmit={onAssign}
        >
          <SelectField
            id={selectId}
            label={t("adminWorkshops.members.candidateLabel")}
            value={selectedUserId}
            onChange={(event) => setSelectedUserId(event.target.value)}
          >
            <option value="">{t("adminWorkshops.members.choose")}</option>
            {availableCandidates.map((user) => (
              <option key={user.id} value={user.id}>
                {t("adminWorkshops.members.candidateOption", {
                  name: user.full_name,
                  role: t(`roles.${user.role}`),
                })}
              </option>
            ))}
          </SelectField>
          <Button type="submit" disabled={selectedUserId === "" || assignMember.isPending}>
            {t("adminWorkshops.members.assign")}
          </Button>
        </form>
      ) : null}
    </section>
  );
}
