import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { WorkshopPayload } from "@/features/workshops/workshop-form-schema";
import { callApi, callApiWithoutContent } from "@/lib/api/call";
import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import type {
  Bay,
  Closure,
  OpeningHoursEntry,
  ServiceType,
  WorkshopMember,
  WorkshopRead,
  WorkshopStaffDetail,
  WorkshopSummary,
} from "@/lib/api/types";

type Schemas = components["schemas"];
export type BayCreatePayload = Schemas["BayCreate"];
export type BayUpdatePayload = Schemas["BayUpdate"];
export type ServiceTypeCreatePayload = Schemas["ServiceTypeCreate"];
export type ServiceTypeUpdatePayload = Schemas["ServiceTypeUpdate"];
export type ClosureCreatePayload = Schemas["ClosureCreate"];
export type OpeningHoursPayload = Schemas["OpeningHoursUpdate"];

export const workshopKeys = {
  mine: ["my-workshops"] as const,
  detail: (workshopId: string) => ["workshop", workshopId] as const,
  closures: (workshopId: string) => ["workshop", workshopId, "closures"] as const,
  bays: (workshopId: string) => ["workshop", workshopId, "bays"] as const,
  serviceTypes: (workshopId: string) => ["workshop", workshopId, "service-types"] as const,
  members: (workshopId: string) => ["workshop", workshopId, "members"] as const,
};

function workshopPath(workshopId: string) {
  return { params: { path: { workshop_id: workshopId } } };
}

export function useMyWorkshops() {
  return useQuery({
    queryKey: workshopKeys.mine,
    queryFn: (): Promise<WorkshopSummary[]> =>
      callApi(() => apiClient.GET("/api/v1/users/me/workshops")),
  });
}

export function useStaffWorkshop(workshopId: string) {
  return useQuery({
    queryKey: workshopKeys.detail(workshopId),
    queryFn: (): Promise<WorkshopStaffDetail> =>
      callApi(() => apiClient.GET("/api/v1/workshops/{workshop_id}", workshopPath(workshopId))),
  });
}

export function useUpdateWorkshop(workshopId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: WorkshopPayload): Promise<WorkshopRead> =>
      callApi(() =>
        apiClient.PATCH("/api/v1/workshops/{workshop_id}", {
          ...workshopPath(workshopId),
          body: payload,
        }),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: workshopKeys.detail(workshopId) });
      await queryClient.invalidateQueries({ queryKey: workshopKeys.mine });
    },
  });
}

export function useReplaceOpeningHours(workshopId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OpeningHoursPayload): Promise<OpeningHoursEntry[]> =>
      callApi(() =>
        apiClient.PUT("/api/v1/workshops/{workshop_id}/opening-hours", {
          ...workshopPath(workshopId),
          body: payload,
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workshopKeys.detail(workshopId) }),
  });
}

export function useClosures(workshopId: string) {
  return useQuery({
    queryKey: workshopKeys.closures(workshopId),
    queryFn: (): Promise<Closure[]> =>
      callApi(() =>
        apiClient.GET("/api/v1/workshops/{workshop_id}/closures", workshopPath(workshopId)),
      ),
  });
}

export function useAddClosure(workshopId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ClosureCreatePayload): Promise<Closure> =>
      callApi(() =>
        apiClient.POST("/api/v1/workshops/{workshop_id}/closures", {
          ...workshopPath(workshopId),
          body: payload,
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workshopKeys.closures(workshopId) }),
  });
}

export function useDeleteClosure(workshopId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (closureId: string) =>
      callApiWithoutContent(() =>
        apiClient.DELETE("/api/v1/workshops/{workshop_id}/closures/{closure_id}", {
          params: { path: { workshop_id: workshopId, closure_id: closureId } },
          parseAs: "text",
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workshopKeys.closures(workshopId) }),
  });
}

export function useBays(workshopId: string) {
  return useQuery({
    queryKey: workshopKeys.bays(workshopId),
    queryFn: (): Promise<Bay[]> =>
      callApi(() =>
        apiClient.GET("/api/v1/workshops/{workshop_id}/bays", {
          params: { path: { workshop_id: workshopId }, query: { include_inactive: true } },
        }),
      ),
  });
}

export function useCreateBay(workshopId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BayCreatePayload): Promise<Bay> =>
      callApi(() =>
        apiClient.POST("/api/v1/workshops/{workshop_id}/bays", {
          ...workshopPath(workshopId),
          body: payload,
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workshopKeys.bays(workshopId) }),
  });
}

export function useUpdateBay(workshopId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ bayId, payload }: { bayId: string; payload: BayUpdatePayload }): Promise<Bay> =>
      callApi(() =>
        apiClient.PATCH("/api/v1/workshops/{workshop_id}/bays/{bay_id}", {
          params: { path: { workshop_id: workshopId, bay_id: bayId } },
          body: payload,
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workshopKeys.bays(workshopId) }),
  });
}

export function useServiceTypes(workshopId: string) {
  return useQuery({
    queryKey: workshopKeys.serviceTypes(workshopId),
    queryFn: (): Promise<ServiceType[]> =>
      callApi(() =>
        apiClient.GET("/api/v1/workshops/{workshop_id}/service-types", {
          params: { path: { workshop_id: workshopId }, query: { include_inactive: true } },
        }),
      ),
  });
}

export function useCreateServiceType(workshopId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ServiceTypeCreatePayload): Promise<ServiceType> =>
      callApi(() =>
        apiClient.POST("/api/v1/workshops/{workshop_id}/service-types", {
          ...workshopPath(workshopId),
          body: payload,
        }),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: workshopKeys.serviceTypes(workshopId) }),
  });
}

export function useUpdateServiceType(workshopId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      serviceTypeId,
      payload,
    }: {
      serviceTypeId: string;
      payload: ServiceTypeUpdatePayload;
    }): Promise<ServiceType> =>
      callApi(() =>
        apiClient.PATCH("/api/v1/workshops/{workshop_id}/service-types/{service_type_id}", {
          params: { path: { workshop_id: workshopId, service_type_id: serviceTypeId } },
          body: payload,
        }),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: workshopKeys.serviceTypes(workshopId) }),
  });
}

export function useWorkshopMembers(workshopId: string) {
  return useQuery({
    queryKey: workshopKeys.members(workshopId),
    queryFn: (): Promise<WorkshopMember[]> =>
      callApi(() =>
        apiClient.GET("/api/v1/workshops/{workshop_id}/members", workshopPath(workshopId)),
      ),
  });
}
