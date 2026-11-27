import type { BackendErrorCode, ErrorResponse } from "@/lib/api/types";

export type ClientErrorCode = "NETWORK_ERROR" | "UNKNOWN_ERROR";
export type ApiErrorCode = BackendErrorCode | ClientErrorCode;

export type FieldIssue = {
  field: string;
  code: string;
  message: string;
};

export const NETWORK_ERROR_STATUS = 0;

export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode;
  readonly fieldIssues: readonly FieldIssue[];

  constructor(status: number, code: ApiErrorCode, message: string, fieldIssues: FieldIssue[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fieldIssues = fieldIssues;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  return (
    isRecord(value) &&
    isRecord(value.error) &&
    typeof value.error.code === "string" &&
    typeof value.error.message === "string"
  );
}

function isFieldIssue(value: unknown): value is FieldIssue {
  return (
    isRecord(value) &&
    typeof value.field === "string" &&
    typeof value.code === "string" &&
    typeof value.message === "string"
  );
}

function extractFieldIssues(details: ErrorResponse["error"]["details"]): FieldIssue[] {
  const fields = details?.fields;
  return Array.isArray(fields) ? fields.filter(isFieldIssue) : [];
}

export function toApiError(body: unknown, status: number): ApiError {
  if (!isErrorResponse(body)) {
    return new ApiError(status, "UNKNOWN_ERROR", `Unexpected response with status ${status}`);
  }
  return new ApiError(
    status,
    body.error.code,
    body.error.message,
    extractFieldIssues(body.error.details),
  );
}

export function toNetworkError(cause: unknown): ApiError {
  const message = cause instanceof Error ? cause.message : "Network request failed";
  return new ApiError(NETWORK_ERROR_STATUS, "NETWORK_ERROR", message);
}

export function isApiErrorWithStatus(error: unknown, ...statuses: number[]): error is ApiError {
  return error instanceof ApiError && statuses.includes(error.status);
}
