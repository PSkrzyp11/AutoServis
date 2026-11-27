import { describe, expect, it } from "vitest";

import { ApiError, isApiErrorWithStatus, toApiError, toNetworkError } from "@/lib/api/errors";

describe("toApiError", () => {
  it("reads the error code and field issues from the API error format", () => {
    const error = toApiError(
      {
        error: {
          code: "VALIDATION_ERROR",
          message: "Request validation failed",
          details: {
            fields: [
              { field: "email", code: "value_error", message: "invalid email" },
              { unexpected: true },
            ],
          },
        },
      },
      422,
    );

    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("VALIDATION_ERROR");
    expect(error.status).toBe(422);
    expect(error.fieldIssues).toEqual([
      { field: "email", code: "value_error", message: "invalid email" },
    ]);
  });

  it("falls back to UNKNOWN_ERROR for unexpected payloads", () => {
    const error = toApiError("<html>Bad gateway</html>", 502);

    expect(error.code).toBe("UNKNOWN_ERROR");
    expect(error.status).toBe(502);
  });
});

describe("toNetworkError", () => {
  it("creates a NETWORK_ERROR with status 0", () => {
    const error = toNetworkError(new TypeError("Failed to fetch"));

    expect(error.code).toBe("NETWORK_ERROR");
    expect(error.status).toBe(0);
    expect(isApiErrorWithStatus(error, 0)).toBe(true);
    expect(isApiErrorWithStatus(error, 401, 403)).toBe(false);
  });
});
