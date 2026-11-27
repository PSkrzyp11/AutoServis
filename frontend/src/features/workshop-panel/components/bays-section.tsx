"use client";

import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

import { FormField } from "@/components/form-field";
import { SelectField } from "@/components/native-select";
import { SectionCard } from "@/components/section-card";
import { StatusMessage } from "@/components/status-message";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useBays, useCreateBay, useUpdateBay } from "@/features/workshop-panel/api";
import { usePanelWorkshop } from "@/features/workshop-panel/components/panel-shell";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import { type Bay, BAY_TYPES, type BayType } from "@/lib/api/types";

type BayDraft = {
  name: string;
  type: BayType;
};

const EMPTY_BAY_DRAFT: BayDraft = { name: "", type: "GENERAL" };

function isBayType(value: string): value is BayType {
  return BAY_TYPES.some((type) => type === value);
}

function BayFields({
  idPrefix,
  draft,
  nameError,
  onChange,
}: {
  idPrefix: string;
  draft: BayDraft;
  nameError?: string;
  onChange: (draft: BayDraft) => void;
}) {
  const t = useTranslations();
  return (
    <>
      <FormField
        id={`${idPrefix}-name`}
        label={t("panel.bays.name")}
        value={draft.name}
        maxLength={100}
        error={nameError}
        onChange={(event) => onChange({ ...draft, name: event.target.value })}
      />
      <SelectField
        id={`${idPrefix}-type`}
        label={t("panel.bays.type")}
        value={draft.type}
        onChange={(event) => {
          const { value } = event.target;
          if (isBayType(value)) {
            onChange({ ...draft, type: value });
          }
        }}
      >
        {BAY_TYPES.map((type) => (
          <option key={type} value={type}>
            {t(`bayTypes.${type}`)}
          </option>
        ))}
      </SelectField>
    </>
  );
}

function BayRow({ bay }: { bay: Bay }) {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const { workshop, canManage } = usePanelWorkshop();
  const updateBay = useUpdateBay(workshop.id);
  const [draft, setDraft] = useState<BayDraft | null>(null);

  if (draft !== null) {
    return (
      <TableRow>
        <TableCell colSpan={4}>
          <form
            className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_12rem_auto] sm:items-end"
            method="post"
            noValidate
            onSubmit={(event: FormEvent<HTMLFormElement>) => {
              event.preventDefault();
              updateBay.mutate(
                { bayId: bay.id, payload: { name: draft.name.trim(), type: draft.type } },
                { onSuccess: () => setDraft(null) },
              );
            }}
          >
            <BayFields
              idPrefix={`bay-${bay.id}`}
              draft={draft}
              nameError={draft.name.trim() === "" ? t("validation.required") : undefined}
              onChange={setDraft}
            />
            <div className="flex gap-2">
              <Button
                type="submit"
                size="sm"
                disabled={updateBay.isPending || draft.name.trim() === ""}
              >
                {t("common.save")}
              </Button>
              <Button type="button" variant="ghost" size="sm" onClick={() => setDraft(null)}>
                {t("common.cancel")}
              </Button>
            </div>
            {updateBay.isError ? (
              <div className="sm:col-span-3">
                <StatusMessage tone="error" message={errorMessage(updateBay.error)} />
              </div>
            ) : null}
          </form>
        </TableCell>
      </TableRow>
    );
  }

  return (
    <TableRow>
      <TableCell className="font-medium">{bay.name}</TableCell>
      <TableCell>{t(`bayTypes.${bay.type}`)}</TableCell>
      <TableCell>
        <Badge variant={bay.is_active ? "secondary" : "outline"}>
          {bay.is_active ? t("common.active") : t("common.inactive")}
        </Badge>
      </TableCell>
      <TableCell>
        {canManage ? (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDraft({ name: bay.name, type: bay.type })}
            >
              {t("common.edit")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={updateBay.isPending}
              onClick={() =>
                updateBay.mutate({ bayId: bay.id, payload: { is_active: !bay.is_active } })
              }
            >
              {bay.is_active ? t("common.deactivate") : t("common.activate")}
            </Button>
          </div>
        ) : null}
      </TableCell>
    </TableRow>
  );
}

function AddBayForm() {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const { workshop } = usePanelWorkshop();
  const createBay = useCreateBay(workshop.id);
  const [draft, setDraft] = useState<BayDraft>(EMPTY_BAY_DRAFT);
  const [nameError, setNameError] = useState<string | undefined>(undefined);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (draft.name.trim() === "") {
      setNameError(t("validation.required"));
      return;
    }
    setNameError(undefined);
    createBay.mutate(
      { name: draft.name.trim(), type: draft.type },
      { onSuccess: () => setDraft(EMPTY_BAY_DRAFT) },
    );
  };

  return (
    <form
      className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_12rem_auto] sm:items-end"
      method="post"
      noValidate
      onSubmit={onSubmit}
    >
      <BayFields idPrefix="new-bay" draft={draft} nameError={nameError} onChange={setDraft} />
      <Button type="submit" disabled={createBay.isPending}>
        {t("panel.bays.add")}
      </Button>
      {createBay.isError ? (
        <div className="sm:col-span-3">
          <StatusMessage tone="error" message={errorMessage(createBay.error)} />
        </div>
      ) : null}
    </form>
  );
}

export function BaysSection() {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const { workshop, canManage } = usePanelWorkshop();
  const bays = useBays(workshop.id);

  return (
    <SectionCard title={t("panel.bays.title")} description={t("panel.bays.description")}>
      {bays.isError ? <StatusMessage tone="error" message={errorMessage(bays.error)} /> : null}
      {bays.isPending ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("common.loading")}
        </p>
      ) : null}
      {bays.data?.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("panel.bays.empty")}</p>
      ) : null}
      {bays.data && bays.data.length > 0 ? (
        <div className="overflow-x-auto">
          <Table>
            <TableCaption className="sr-only">{t("panel.bays.title")}</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">{t("panel.bays.name")}</TableHead>
                <TableHead scope="col">{t("panel.bays.type")}</TableHead>
                <TableHead scope="col">{t("panel.bays.status")}</TableHead>
                <TableHead scope="col">{canManage ? t("panel.bays.actions") : null}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {bays.data.map((bay) => (
                <BayRow key={bay.id} bay={bay} />
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}
      {canManage ? <AddBayForm /> : null}
    </SectionCard>
  );
}
