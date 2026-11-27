import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { VehiclePayload } from "@/features/vehicles/schemas";
import { callApi, callApiWithoutContent } from "@/lib/api/call";
import { apiClient } from "@/lib/api/client";
import type { Vehicle, VehiclePage } from "@/lib/api/types";

const VEHICLES_PAGE_SIZE = 100;
const vehiclesQueryKey = ["vehicles"] as const;

export function useVehicles() {
  return useQuery({
    queryKey: vehiclesQueryKey,
    queryFn: (): Promise<VehiclePage> =>
      callApi(() =>
        apiClient.GET("/api/v1/vehicles", {
          params: { query: { limit: VEHICLES_PAGE_SIZE, offset: 0 } },
        }),
      ),
  });
}

export function useCreateVehicle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: VehiclePayload): Promise<Vehicle> =>
      callApi(() => apiClient.POST("/api/v1/vehicles", { body: payload })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: vehiclesQueryKey }),
  });
}

export function useUpdateVehicle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ vehicleId, payload }: { vehicleId: string; payload: VehiclePayload }) =>
      callApi(() =>
        apiClient.PATCH("/api/v1/vehicles/{vehicle_id}", {
          params: { path: { vehicle_id: vehicleId } },
          body: payload,
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: vehiclesQueryKey }),
  });
}

export function useDeleteVehicle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vehicleId: string) =>
      callApiWithoutContent(() =>
        apiClient.DELETE("/api/v1/vehicles/{vehicle_id}", {
          params: { path: { vehicle_id: vehicleId } },
          parseAs: "text",
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: vehiclesQueryKey }),
  });
}
