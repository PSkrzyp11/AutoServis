import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { currentUserQueryKey } from "@/features/auth/api";
import { callApi } from "@/lib/api/call";
import { apiClient } from "@/lib/api/client";
import type { SortOrder, User, UserPage, UserRole, UserSortField } from "@/lib/api/types";

export const ADMIN_USERS_PAGE_SIZE = 20;

export type AdminUsersFilters = {
  search: string;
  role: UserRole | null;
  isActive: boolean | null;
  offset: number;
  sortBy: UserSortField;
  sortOrder: SortOrder;
};

type ProfileUpdate = {
  fullName: string;
  phone: string;
};

type AdminUserUpdate = {
  userId: string;
  role?: UserRole;
  isActive?: boolean;
};

const adminUsersQueryKey = ["admin-users"] as const;

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ fullName, phone }: ProfileUpdate): Promise<User> =>
      callApi(() =>
        apiClient.PATCH("/api/v1/users/me", {
          body: { full_name: fullName, phone: phone === "" ? null : phone },
        }),
      ),
    onSuccess: (user) => queryClient.setQueryData(currentUserQueryKey, user),
  });
}

export function useAdminUsers(filters: AdminUsersFilters) {
  return useQuery({
    queryKey: [...adminUsersQueryKey, filters],
    placeholderData: keepPreviousData,
    queryFn: (): Promise<UserPage> =>
      callApi(() =>
        apiClient.GET("/api/v1/admin/users", {
          params: {
            query: {
              limit: ADMIN_USERS_PAGE_SIZE,
              offset: filters.offset,
              search: filters.search || null,
              role: filters.role,
              is_active: filters.isActive,
              sort_by: filters.sortBy,
              sort_order: filters.sortOrder,
            },
          },
        }),
      ),
  });
}

export function useUpdateUserAsAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role, isActive }: AdminUserUpdate): Promise<User> =>
      callApi(() =>
        apiClient.PATCH("/api/v1/admin/users/{user_id}", {
          params: { path: { user_id: userId } },
          body: { role, is_active: isActive },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminUsersQueryKey }),
  });
}
