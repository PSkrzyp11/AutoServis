import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { callApi } from "@/lib/api/call";
import { apiClient } from "@/lib/api/client";
import type {
  Appointment,
  AppointmentPage,
  AppointmentScope,
  DayAvailability,
  WorkshopPublicDetail,
} from "@/lib/api/types";
import type { DayKey } from "@/lib/day-keys";

const MY_APPOINTMENTS_PAGE_SIZE = 50;

export const bookingKeys = {
  workshop: (slug: string) => ["public-workshop", slug] as const,
  availability: (workshopId: string, serviceTypeId: string, day: DayKey) =>
    ["availability", workshopId, serviceTypeId, day] as const,
  availabilityRoot: ["availability"] as const,
  myAppointments: ["my-appointments"] as const,
};

export type BookingRequest = {
  workshop_id: string;
  service_type_id: string;
  vehicle_id: string;
  start_at: string;
  problem_description: string | null;
};

export function usePublicWorkshop(slug: string) {
  return useQuery({
    queryKey: bookingKeys.workshop(slug),
    queryFn: (): Promise<WorkshopPublicDetail> =>
      callApi(() => apiClient.GET("/api/v1/workshops/slug/{slug}", { params: { path: { slug } } })),
  });
}

export function useAvailability(
  workshopId: string | undefined,
  serviceTypeId: string | null,
  day: DayKey | null,
) {
  return useQuery({
    queryKey: bookingKeys.availability(workshopId ?? "", serviceTypeId ?? "", day ?? ""),
    enabled: Boolean(workshopId && serviceTypeId && day),
    queryFn: (): Promise<DayAvailability> =>
      callApi(() =>
        apiClient.GET("/api/v1/workshops/{workshop_id}/availability", {
          params: {
            path: { workshop_id: workshopId ?? "" },
            query: { service_type_id: serviceTypeId ?? "", date: day ?? "" },
          },
        }),
      ),
  });
}

export function useBookAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BookingRequest): Promise<Appointment> =>
      callApi(() => apiClient.POST("/api/v1/appointments", { body: payload })),
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: bookingKeys.availabilityRoot });
      await queryClient.invalidateQueries({ queryKey: bookingKeys.myAppointments });
    },
  });
}

export function useMyAppointments(scope: AppointmentScope) {
  return useQuery({
    queryKey: [...bookingKeys.myAppointments, scope],
    queryFn: (): Promise<AppointmentPage> =>
      callApi(() =>
        apiClient.GET("/api/v1/appointments/mine", {
          params: { query: { scope, limit: MY_APPOINTMENTS_PAGE_SIZE, offset: 0 } },
        }),
      ),
  });
}

export function useCancelMyAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (appointmentId: string): Promise<Appointment> =>
      callApi(() =>
        apiClient.POST("/api/v1/appointments/{appointment_id}/cancel", {
          params: { path: { appointment_id: appointmentId } },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: bookingKeys.myAppointments }),
  });
}
