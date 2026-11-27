"use client";

import { useTranslations } from "next-intl";
import { type FormEvent, useState } from "react";

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
import { useCurrentUser } from "@/features/auth/api";
import {
  ADMIN_USERS_PAGE_SIZE,
  type AdminUsersFilters,
  useAdminUsers,
  useUpdateUserAsAdmin,
} from "@/features/users/api";
import { useApiErrorMessage } from "@/hooks/use-api-error-message";
import { USER_ROLES, type User, type UserRole } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

const NATIVE_SELECT_CLASS_NAME =
  "h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50";
const ALL_OPTION_VALUE = "";
const ACTIVE_STATUS_VALUE = "active";
const INACTIVE_STATUS_VALUE = "inactive";

const INITIAL_FILTERS: AdminUsersFilters = {
  search: "",
  role: null,
  isActive: null,
  offset: 0,
  sortBy: "created_at",
  sortOrder: "desc",
};

function isUserRole(value: string): value is UserRole {
  return USER_ROLES.some((role) => role === value);
}

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

type UserRowProps = {
  user: User;
  isCurrentUser: boolean;
  onUpdate: (update: { role?: UserRole; isActive?: boolean }) => void;
  isUpdating: boolean;
};

function UserRow({ user, isCurrentUser, onUpdate, isUpdating }: UserRowProps) {
  const t = useTranslations();
  const roleSelectId = `role-${user.id}`;
  const isLocked = isCurrentUser || isUpdating;

  return (
    <TableRow>
      <TableCell className="font-medium">
        {user.full_name}
        {isCurrentUser ? (
          <Badge variant="outline" className="ml-2">
            {t("adminUsers.currentUser")}
          </Badge>
        ) : null}
      </TableCell>
      <TableCell className="break-all">{user.email}</TableCell>
      <TableCell>
        <label htmlFor={roleSelectId} className="sr-only">
          {t("adminUsers.changeRoleLabel", { name: user.full_name })}
        </label>
        <select
          id={roleSelectId}
          className={NATIVE_SELECT_CLASS_NAME}
          value={user.role}
          disabled={isLocked}
          onChange={(event) => {
            if (isUserRole(event.target.value)) {
              onUpdate({ role: event.target.value });
            }
          }}
        >
          {USER_ROLES.map((role) => (
            <option key={role} value={role}>
              {t(`roles.${role}`)}
            </option>
          ))}
        </select>
      </TableCell>
      <TableCell>
        <Badge variant={user.is_active ? "secondary" : "destructive"}>
          {user.is_active ? t("adminUsers.active") : t("adminUsers.inactive")}
        </Badge>
      </TableCell>
      <TableCell>
        <time dateTime={user.created_at}>{formatDate(user.created_at)}</time>
      </TableCell>
      <TableCell>
        <Button
          variant="outline"
          size="sm"
          disabled={isLocked}
          onClick={() => onUpdate({ isActive: !user.is_active })}
        >
          {user.is_active ? t("adminUsers.deactivate") : t("adminUsers.activate")}
        </Button>
      </TableCell>
    </TableRow>
  );
}

export function AdminUsersView() {
  const t = useTranslations();
  const errorMessage = useApiErrorMessage();
  const { data: currentUser } = useCurrentUser();
  const [filters, setFilters] = useState<AdminUsersFilters>(INITIAL_FILTERS);
  const [searchDraft, setSearchDraft] = useState("");
  const [lastUpdatedName, setLastUpdatedName] = useState<string | null>(null);
  const users = useAdminUsers(filters);
  const updateUser = useUpdateUserAsAdmin();

  const updateFilters = (changes: Partial<AdminUsersFilters>) =>
    setFilters((previous) => ({ ...previous, ...changes, offset: changes.offset ?? 0 }));

  const onSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    updateFilters({ search: searchDraft.trim() });
  };

  const onUpdate = (user: User, update: { role?: UserRole; isActive?: boolean }) => {
    setLastUpdatedName(null);
    updateUser.mutate(
      { userId: user.id, ...update },
      { onSuccess: () => setLastUpdatedName(user.full_name) },
    );
  };

  const page = users.data;
  const firstItem = page && page.total > 0 ? page.offset + 1 : 0;
  const lastItem = page ? page.offset + page.items.length : 0;
  const hasPreviousPage = filters.offset > 0;
  const hasNextPage = page ? lastItem < page.total : false;

  return (
    <div className="grid gap-6">
      <header className="grid gap-1">
        <h1 className="text-2xl font-semibold">{t("adminUsers.title")}</h1>
        <p className="text-muted-foreground">{t("adminUsers.description")}</p>
      </header>

      <div className="flex flex-col gap-4 md:flex-row md:items-end">
        <form className="flex flex-1 items-end gap-2" onSubmit={onSearch} role="search">
          <div className="grid flex-1 gap-2">
            <Label htmlFor="user-search">{t("adminUsers.searchLabel")}</Label>
            <Input
              id="user-search"
              type="search"
              value={searchDraft}
              placeholder={t("adminUsers.searchPlaceholder")}
              onChange={(event) => setSearchDraft(event.target.value)}
            />
          </div>
          <Button type="submit" variant="secondary">
            {t("adminUsers.searchSubmit")}
          </Button>
        </form>
        <div className="grid gap-2">
          <Label htmlFor="role-filter">{t("adminUsers.roleFilter")}</Label>
          <select
            id="role-filter"
            className={NATIVE_SELECT_CLASS_NAME}
            value={filters.role ?? ALL_OPTION_VALUE}
            onChange={(event) => {
              const { value } = event.target;
              updateFilters({ role: isUserRole(value) ? value : null });
            }}
          >
            <option value={ALL_OPTION_VALUE}>{t("adminUsers.allRoles")}</option>
            {USER_ROLES.map((role) => (
              <option key={role} value={role}>
                {t(`roles.${role}`)}
              </option>
            ))}
          </select>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="status-filter">{t("adminUsers.statusFilter")}</Label>
          <select
            id="status-filter"
            className={NATIVE_SELECT_CLASS_NAME}
            value={statusValue(filters.isActive)}
            onChange={(event) => updateFilters({ isActive: parseStatus(event.target.value) })}
          >
            <option value={ALL_OPTION_VALUE}>{t("adminUsers.allStatuses")}</option>
            <option value={ACTIVE_STATUS_VALUE}>{t("adminUsers.active")}</option>
            <option value={INACTIVE_STATUS_VALUE}>{t("adminUsers.inactive")}</option>
          </select>
        </div>
      </div>

      {updateUser.isError ? (
        <StatusMessage tone="error" message={errorMessage(updateUser.error)} />
      ) : null}
      {lastUpdatedName ? (
        <StatusMessage
          tone="success"
          message={t("adminUsers.updated", { name: lastUpdatedName })}
        />
      ) : null}
      {users.isError ? <StatusMessage tone="error" message={errorMessage(users.error)} /> : null}

      {page ? (
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableCaption className="sr-only">{t("adminUsers.tableCaption")}</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">{t("adminUsers.columns.fullName")}</TableHead>
                <TableHead scope="col">{t("adminUsers.columns.email")}</TableHead>
                <TableHead scope="col">{t("adminUsers.columns.role")}</TableHead>
                <TableHead scope="col">{t("adminUsers.columns.status")}</TableHead>
                <TableHead scope="col">{t("adminUsers.columns.createdAt")}</TableHead>
                <TableHead scope="col">{t("adminUsers.columns.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {page.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    {t("adminUsers.empty")}
                  </TableCell>
                </TableRow>
              ) : (
                page.items.map((user) => (
                  <UserRow
                    key={user.id}
                    user={user}
                    isCurrentUser={user.id === currentUser?.id}
                    isUpdating={updateUser.isPending}
                    onUpdate={(update) => onUpdate(user, update)}
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
          aria-label={t("adminUsers.tableCaption")}
        >
          <p className="text-sm text-muted-foreground" aria-live="polite">
            {t("adminUsers.summary", { from: firstItem, to: lastItem, total: page.total })}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!hasPreviousPage}
              onClick={() =>
                updateFilters({ offset: Math.max(filters.offset - ADMIN_USERS_PAGE_SIZE, 0) })
              }
            >
              {t("common.previousPage")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!hasNextPage}
              onClick={() => updateFilters({ offset: filters.offset + ADMIN_USERS_PAGE_SIZE })}
            >
              {t("common.nextPage")}
            </Button>
          </div>
        </nav>
      ) : null}
    </div>
  );
}
