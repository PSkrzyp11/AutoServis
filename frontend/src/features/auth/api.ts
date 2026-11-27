import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuthStore } from "@/features/auth/auth-store";
import { apiClient, callApi, callApiWithoutContent } from "@/lib/api/client";
import type { User } from "@/lib/api/types";

export const currentUserQueryKey = ["current-user"] as const;

type Credentials = {
  email: string;
  password: string;
};

type Registration = Credentials & {
  fullName: string;
  phone: string;
};

type PasswordResetConfirmation = {
  token: string;
  newPassword: string;
};

async function signIn(credentials: Credentials): Promise<void> {
  const tokens = await callApi(() => apiClient.POST("/api/v1/auth/login", { body: credentials }));
  useAuthStore.getState().setAccessToken(tokens.access_token);
}

export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserQueryKey,
    queryFn: (): Promise<User> => callApi(() => apiClient.GET("/api/v1/users/me")),
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: signIn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: currentUserQueryKey }),
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ email, password, fullName, phone }: Registration) => {
      await callApi(() =>
        apiClient.POST("/api/v1/auth/register", {
          body: { email, password, full_name: fullName, phone: phone === "" ? null : phone },
        }),
      );
      await signIn({ email, password });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: currentUserQueryKey }),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      callApiWithoutContent(() => apiClient.POST("/api/v1/auth/logout", { parseAs: "text" })),
    onSettled: () => {
      useAuthStore.getState().clearAccessToken();
      queryClient.clear();
    },
  });
}

export function useRequestPasswordReset() {
  return useMutation({
    mutationFn: (email: string) =>
      callApiWithoutContent(() =>
        apiClient.POST("/api/v1/auth/password-reset/request", {
          body: { email },
          parseAs: "text",
        }),
      ),
  });
}

export function useConfirmPasswordReset() {
  return useMutation({
    mutationFn: ({ token, newPassword }: PasswordResetConfirmation) =>
      callApiWithoutContent(() =>
        apiClient.POST("/api/v1/auth/password-reset/confirm", {
          body: { token, new_password: newPassword },
          parseAs: "text",
        }),
      ),
  });
}
