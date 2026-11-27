import createClient from "openapi-fetch";

import { getAccessToken, useAuthStore } from "@/features/auth/auth-store";
import type { paths } from "@/lib/api/schema";
import type { AccessTokenResponse } from "@/lib/api/types";

const REFRESH_PATH = "/api/v1/auth/refresh";
const AUTH_PATH_PREFIX = "/api/v1/auth/";
const UNAUTHORIZED_STATUS = 401;

let pendingRefresh: Promise<string | null> | null = null;

function apiBaseUrl(): string {
  return typeof window === "undefined" ? "" : window.location.origin;
}

async function performRefresh(): Promise<string | null> {
  const response = await fetch(`${apiBaseUrl()}${REFRESH_PATH}`, {
    method: "POST",
    credentials: "same-origin",
  });
  if (!response.ok) {
    useAuthStore.getState().clearAccessToken();
    return null;
  }
  const body = (await response.json()) as AccessTokenResponse;
  useAuthStore.getState().setAccessToken(body.access_token);
  return body.access_token;
}

export function refreshAccessToken(): Promise<string | null> {
  pendingRefresh ??= performRefresh().finally(() => {
    pendingRefresh = null;
  });
  return pendingRefresh;
}

function isAuthEndpoint(url: string): boolean {
  return new URL(url, "http://localhost").pathname.startsWith(AUTH_PATH_PREFIX);
}

function withAuthorization(request: Request, accessToken: string | null): Request {
  if (!accessToken) {
    return request;
  }
  const headers = new Headers(request.headers);
  headers.set("Authorization", `Bearer ${accessToken}`);
  return new Request(request, { headers });
}

async function authorizedFetch(request: Request): Promise<Response> {
  const retryableRequest = request.clone();
  const response = await fetch(withAuthorization(request, getAccessToken()));
  if (response.status !== UNAUTHORIZED_STATUS || isAuthEndpoint(request.url)) {
    return response;
  }
  const refreshedToken = await refreshAccessToken();
  if (!refreshedToken) {
    return response;
  }
  return fetch(withAuthorization(retryableRequest, refreshedToken));
}

export const apiClient = createClient<paths>({
  baseUrl: apiBaseUrl(),
  fetch: authorizedFetch,
  credentials: "same-origin",
});
