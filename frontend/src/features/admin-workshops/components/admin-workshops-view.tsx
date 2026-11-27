"use client";

import { PlusIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { type FormEvent, Fragment, useState } from "react";

import { SelectField } from "@/components/native-select";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusMessage } from "@/components/status-message";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ADMIN_WORKSHOPS_PAGE_SIZE,
  type AdminWorkshopsFilters,
  useAdminWorkshops,
  useCreateWorkshop,
  useSetWorkshopActive,
} from "@/features/admin-workshops/api";
import { WorkshopMembersManager } from "@/features/admin-workshops/components/workshop-members-manager";
import { WorkshopForm } from "@/features/workshops/components/workshop-form";
import { EMPTY_WORKSHOP_FORM } from "@/features/workshops/workshop-form-schema";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import type { WorkshopRead } from "@/lib/api/types";

const ALL_OPTION_VALUE = "";
const ACTIVE_STATUS_VALUE = "active";
const INACTIVE_STATUS_VALUE = "inactive";
const TABLE_COLUMNS = 5;

const INITIAL_FILTERS: AdminWorkshopsFilters = { search: "", isActive: null, offset: 0 };

type Notice = { key: "created" | "updated"; name: string } | null;

function parseStatus(value: string): boolean | null {
  if (value === ACTIVE_STATUS_VALUE) {
    return true;
  }
  return value === INACTIVE_STATUS_VALUE ? false : null;
}

function statusValue(isActive: boolean | null): string {
  if (isActive === null) {
    return ALL_OPTION_VALUE;
  }
  return isActive ? ACTIVE_STATUS_VALUE : INACTIVE_STATUS_VALUE;
}

function WorkshopRow({
  workshop,
  isExpanded,
  onToggleStaff,
  onStatusChanged,
}: {
  workshop: WorkshopRead;
  isExpanded: boolean;
  onToggleStaff: () => void;
  onStatusChanged: (name: string) => void;
}) {
  const t = useTranslations();
  const setWorkshopActive = useSetWorkshopActive();

  return (
    <Fragment>
      <TableRow>
        <TableCell className="font-medium whitespace-normal">{workshop.name}</TableCell>
        <TableCell>{workshop.city}</TableCell>
        <TableCell className="font-mono">{workshop.tax_id}</TableCell>
        <TableCell>
          <Badge variant={workshop.is_active ? "secondary" : "destructive"}>
            {workshop.is_active ? t("common.active") : t("common.inactive")}
          </Badge>
        </TableCell>
        <TableCell>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" aria-expanded={isExpanded} onClick={onToggleStaff}>
              {isExpanded ? t("adminWorkshops.hideStaff") : t("adminWorkshops.showStaff")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={setWorkshopActive.isPending}
              onClick={() =>
                setWorkshopActive.mutate(
                  { workshopId: workshop.id, isActive: !workshop.is_active },
                  { onSuccess: () => onStatusChanged(workshop.name) },
                )
              }
            >
              {workshop.is_active ? t("common.deactivate") : t("common.activate")}
            </Button>
          </div>
        </TableCell>
      </TableRow>
      {isExpanded ? (
        <TableRow>
          <TableCell colSpan={TABLE_COLUMNS} className="whitespace-normal">
            <WorkshopMembersManager workshop={workshop} />
          </TableCell>
        </TableRow>
      ) : null}
    </Fragment>
  );
}

export function AdminWorkshopsView() {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const [filters, setFilters] = useState<AdminWorkshopsFilters>(INITIAL_FILTERS);
  const [searchDraft, setSearchDraft] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const workshops = useAdminWorkshops(filters);
  const createWorkshop = useCreateWorkshop();

  const updateFilters = (changes: Partial<AdminWorkshopsFilters>) =>
    setFilters((previous) => ({ ...previous, ...changes, offset: changes.offset ?? 0 }));

  const onSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    updateFilters({ search: searchDraft.trim() });
  };

  const page = workshops.data;
  const firstItem = page && page.total > 0 ? page.offset + 1 : 0;
  const lastItem = page ? page.offset + page.items.length : 0;

  return (
    <div className="grid gap-6">
      <PageHeader
        title={t("adminWorkshops.title")}
        description={t("adminWorkshops.description")}
        actions={
          isCreating ? null : (
            <Button onClick={() => setIsCreating(true)}>
              <PlusIcon aria-hidden="true" />
              {t("adminWorkshops.add")}
            </Button>
          )
        }
      />

      {notice ? (
        <StatusMessage
          tone="success"
          message={t(`adminWorkshops.${notice.key}`, { name: notice.name })}
        />
      ) : null}

      {isCreating ? (
        <SectionCard title={t("adminWorkshops.formTitle")}>
          <WorkshopForm
            idPrefix="new-workshop"
            defaultValues={EMPTY_WORKSHOP_FORM}
            submitLabel={t("adminWorkshops.add")}
            isPending={createWorkshop.isPending}
            error={createWorkshop.error}
            onCancel={() => setIsCreating(false)}
            onSubmit={(payload) =>
              createWorkshop.mutate(payload, {
                onSuccess: (workshop) => {
                  setIsCreating(false);
                  setNotice({ key: "created", name: workshop.name });
                },
              })
            }
          />
        </SectionCard>
      ) : null}

      <div className="flex flex-col gap-4 md:flex-row md:items-end">
        <form className="flex flex-1 items-end gap-2" onSubmit={onSearch} role="search">
          <div className="grid flex-1 gap-2">
            <Label htmlFor="workshop-search">{t("adminWorkshops.searchLabel")}</Label>
            <Input
              id="workshop-search"
              type="search"
              value={searchDraft}
              placeholder={t("adminWorkshops.searchPlaceholder")}
              onChange={(event) => setSearchDraft(event.target.value)}
            />
          </div>
          <Button type="submit" variant="secondary">
            {t("adminWorkshops.searchSubmit")}
          </Button>
        </form>
        <SelectField
          id="workshop-status-filter"
          label={t("adminWorkshops.statusFilter")}
          value={statusValue(filters.isActive)}
          onChange={(event) => updateFilters({ isActive: parseStatus(event.target.value) })}
        >
          <option value={ALL_OPTION_VALUE}>{t("adminWorkshops.allStatuses")}</option>
          <option value={ACTIVE_STATUS_VALUE}>{t("common.active")}</option>
          <option value={INACTIVE_STATUS_VALUE}>{t("common.inactive")}</option>
        </SelectField>
      </div>

      {workshops.isError ? (
        <StatusMessage tone="error" message={errorMessage(workshops.error)} />
      ) : null}

      {page ? (
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableCaption className="sr-only">{t("adminWorkshops.tableCaption")}</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">{t("adminWorkshops.columns.name")}</TableHead>
                <TableHead scope="col">{t("adminWorkshops.columns.city")}</TableHead>
                <TableHead scope="col">{t("adminWorkshops.columns.taxId")}</TableHead>
                <TableHead scope="col">{t("adminWorkshops.columns.status")}</TableHead>
                <TableHead scope="col">{t("adminWorkshops.columns.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {page.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={TABLE_COLUMNS} className="text-center text-muted-foreground">
                    {t("adminWorkshops.empty")}
                  </TableCell>
                </TableRow>
              ) : (
                page.items.map((workshop) => (
                  <WorkshopRow
                    key={workshop.id}
                    workshop={workshop}
                    isExpanded={expandedId === workshop.id}
                    onToggleStaff={() =>
                      setExpandedId((current) => (current === workshop.id ? null : workshop.id))
                    }
                    onStatusChanged={(name) => setNotice({ key: "updated", name })}
                  />
                ))
              )}
            </TableBody>
          </Table>
        </div>
      ) : (
        <p role="status" className="text-sm text-muted-foreground">
          {t("common.loading")}
        </p>
      )}

      {page ? (
        <nav
          className="flex items-center justify-between gap-4"
          aria-label={t("common.pagination")}
        >
          <p className="text-sm text-muted-foreground" aria-live="polite">
            {t("common.summary", { from: firstItem, to: lastItem, total: page.total })}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={filters.offset === 0}
              onClick={() =>
                updateFilters({ offset: Math.max(filters.offset - ADMIN_WORKSHOPS_PAGE_SIZE, 0) })
              }
            >
              {t("common.previousPage")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={lastItem >= page.total}
              onClick={() => updateFilters({ offset: filters.offset + ADMIN_WORKSHOPS_PAGE_SIZE })}
            >
              {t("common.nextPage")}
            </Button>
          </div>
        </nav>
      ) : null}
    </div>
  );
}
