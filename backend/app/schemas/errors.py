from typing import Any

from fastapi import status
from pydantic import BaseModel, Field, JsonValue

from app.core.errors import ErrorCode

ERROR_DESCRIPTIONS: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "The request cannot be processed in the current state",
    status.HTTP_401_UNAUTHORIZED: "Authentication is missing, invalid or expired",
    status.HTTP_403_FORBIDDEN: "The authenticated user is not allowed to perform this action",
    status.HTTP_404_NOT_FOUND: "The requested resource does not exist",
    status.HTTP_409_CONFLICT: "The request conflicts with the current state of the resource",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "The request payload or parameters are invalid",
    status.HTTP_429_TOO_MANY_REQUESTS: "Too many requests were sent in a short period of time",
}


class ErrorBody(BaseModel):
    code: ErrorCode = Field(description="Stable, machine readable error code")
    message: str = Field(description="Human readable error description in English")
    details: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Additional structured information about the error",
    )


class ErrorResponse(BaseModel):
    error: ErrorBody


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    codes = {*status_codes, status.HTTP_422_UNPROCESSABLE_CONTENT}
    return {
        code: {"model": ErrorResponse, "description": ERROR_DESCRIPTIONS[code]}
        for code in sorted(codes)
    }
