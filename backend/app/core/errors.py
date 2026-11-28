from enum import StrEnum

from fastapi import status
from pydantic import JsonValue


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    FORBIDDEN = "FORBIDDEN"
    USER_INACTIVE = "USER_INACTIVE"
    EMAIL_ALREADY_REGISTERED = "EMAIL_ALREADY_REGISTERED"
    SELF_MODIFICATION_FORBIDDEN = "SELF_MODIFICATION_FORBIDDEN"
    WORKSHOP_ACCESS_DENIED = "WORKSHOP_ACCESS_DENIED"
    USER_NOT_STAFF = "USER_NOT_STAFF"
    MEMBER_ALREADY_EXISTS = "MEMBER_ALREADY_EXISTS"
    CLOSURE_ALREADY_EXISTS = "CLOSURE_ALREADY_EXISTS"
    BAY_NAME_TAKEN = "BAY_NAME_TAKEN"
    SERVICE_NAME_TAKEN = "SERVICE_NAME_TAKEN"
    VIN_ALREADY_REGISTERED = "VIN_ALREADY_REGISTERED"
    SERVICE_NOT_AVAILABLE = "SERVICE_NOT_AVAILABLE"
    SLOT_NOT_AVAILABLE = "SLOT_NOT_AVAILABLE"
    APPOINTMENT_SLOT_TAKEN = "APPOINTMENT_SLOT_TAKEN"
    VEHICLE_ALREADY_BOOKED = "VEHICLE_ALREADY_BOOKED"
    CANCELLATION_TOO_LATE = "CANCELLATION_TOO_LATE"
    INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"
    ORDER_STATUS_CONFLICT = "ORDER_STATUS_CONFLICT"
    DIAGNOSIS_REQUIRED = "DIAGNOSIS_REQUIRED"
    ORDER_CLOSED = "ORDER_CLOSED"
    ORDER_NOT_ASSIGNED_TO_YOU = "ORDER_NOT_ASSIGNED_TO_YOU"
    ORDER_ALREADY_ASSIGNED = "ORDER_ALREADY_ASSIGNED"
    ASSIGNEE_NOT_IN_WORKSHOP = "ASSIGNEE_NOT_IN_WORKSHOP"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    RATE_LIMITED = "RATE_LIMITED"
    HTTP_ERROR = "HTTP_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, JsonValue] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details: dict[str, JsonValue] = details or {}
        self.headers = headers


class UnauthorizedError(AppError):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(
            code,
            message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(AppError):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(code, message, status_code=status.HTTP_403_FORBIDDEN)


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.NOT_FOUND, message, status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppError):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(code, message, status_code=status.HTTP_409_CONFLICT)


class RateLimitedError(AppError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            ErrorCode.RATE_LIMITED,
            "Too many requests, try again later",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after_seconds": retry_after_seconds},
            headers={"Retry-After": str(retry_after_seconds)},
        )
