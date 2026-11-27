import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { workshopKeys } from "@/features/workshop-panel/api";
import type { WorkshopPayload } from "@/features/workshops/workshop-form-schema";
import { callApi, callApiWithoutContent } from "@/lib/api/call";
import { apiClient } from "@/lib/api/client";
import type { User, UserRole, WorkshopMember, WorkshopPage, WorkshopRead } from "@/lib/api/types";

export const ADMIN_WORKSHOPS_PAGE_SIZE = 20;
const CANDIDATES_PAGE_SIZE = 100;
const CANDIDATE_ROLES = ["MANAGER", "MECHANIC"] as const satisfies readonly UserRole[];

const adminWorkshopsQueryKey = ["admin-workshops"] as const;
const staffCandidatesQueryKey = ["staff-candidates"] as const;

export type AdminWorkshopsFilters = {
  search: string;
  isActive: boolean | null;
  offset: number;
};

export function useAdminWorkshops(filters: AdminWorkshopsFilters) {
  return useQuery({
    queryKey: [...adminWorkshopsQueryKey, filters],
    placeholderData: keepPreviousData,
    queryFn: (): Promise<WorkshopPage> =>
      callApi(() =>
        apiClient.GET("/api/v1/admin/workshops", {
          params: {
            query: {
              limit: ADMIN_WORKSHOPS_PAGE_SIZE,
              offset: filters.offset,
              search: filters.search || null,
              is_active: filters.isActive,
            },
          },
        }),
      ),
  });
}

export function useCreateWorkshop() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: WorkshopPayload): Promise<WorkshopRead> =>
      callApi(() => apiClient.POST("/api/v1/admin/workshops", { body: payload })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminWorkshopsQueryKey }),
  });
}

export function useSetWorkshopActive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workshopId, isActive }: { workshopId: string; isActive: boolean }) =>
      callApi(() =>
        apiClient.PATCH("/api/v1/admin/workshops/{workshop_id}", {
          params: { path: { workshop_id: workshopId } },
          body: { is_active: isActive },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminWorkshopsQueryKey }),
  });
}

async function fetchStaffCandidates(): Promise<User[]> {
  const pages = await Promise.all(
    CANDIDATE_ROLES.map((role) =>
      callApi(() =>
        apiClient.GET("/api/v1/admin/users", {
          params: {
            query: {
              role,
              is_active: true,
              limit: CANDIDATES_PAGE_SIZE,
              offset: 0,
              sort_by: "full_name",
              sort_order: "asc",
            },
          },
        }),
      ),
    ),
  );
  return pages.flatMap((page) => page.items);
}

export function useStaffCandidates() {
  return useQuery({ queryKey: staffCandidatesQueryKey, queryFn: fetchStaffCandidates });
}

export function useAssignMember(workshopId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string): Promise<WorkshopMember> =>
      callApi(() =>
        apiClient.POST("/api/v1/admin/workshops/{workshop_id}/members", {
          params: { path: { workshop_id: workshopId } },
          body: { user_id: userId },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workshopKeys.members(workshopId) }),
  });
}

export function useRemoveMember(workshopId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) =>
      callApiWithoutContent(() =>
        apiClient.DELETE("/api/v1/admin/workshops/{workshop_id}/members/{user_id}", {
          params: { path: { workshop_id: workshopId, user_id: userId } },
          parseAs: "text",
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workshopKeys.members(workshopId) }),
  });
}
