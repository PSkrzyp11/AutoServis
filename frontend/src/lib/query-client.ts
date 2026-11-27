import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "@/lib/api/errors";

const MAX_RETRIES = 2;
const DEFAULT_STALE_TIME_MS = 30_000;
const FIRST_SERVER_ERROR_STATUS = 500;

function shouldRetry(failureCount: number, error: unknown): boolean {
  const isClientError =
    error instanceof ApiError && error.status > 0 && error.status < FIRST_SERVER_ERROR_STATUS;
  return !isClientError && failureCount < MAX_RETRIES;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetry, staleTime: DEFAULT_STALE_TIME_MS },
      mutations: { retry: false },
    },
  });
}
