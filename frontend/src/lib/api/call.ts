import { ApiError, toApiError, toNetworkError } from "@/lib/api/errors";

type ApiResult<T> = {
  data?: T;
  error?: unknown;
  response: Response;
};

async function settle<T>(operation: () => Promise<ApiResult<T>>): Promise<ApiResult<T>> {
  try {
    return await operation();
  } catch (cause) {
    throw cause instanceof ApiError ? cause : toNetworkError(cause);
  }
}

export async function callApi<T>(operation: () => Promise<ApiResult<T>>): Promise<T> {
  const result = await settle(operation);
  if (!result.response.ok || result.data === undefined) {
    throw toApiError(result.error, result.response.status);
  }
  return result.data;
}

export async function callApiWithoutContent(
  operation: () => Promise<ApiResult<unknown>>,
): Promise<void> {
  const result = await settle(operation);
  if (!result.response.ok) {
    throw toApiError(result.error, result.response.status);
  }
}
