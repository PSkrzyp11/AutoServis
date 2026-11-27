from collections.abc import Mapping

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import JsonValue
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.schemas.errors import ErrorBody, ErrorResponse

logger = get_logger()

HTTP_STATUS_ERROR_CODES: dict[int, ErrorCode] = {
    status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
    status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
    status.HTTP_405_METHOD_NOT_ALLOWED: ErrorCode.METHOD_NOT_ALLOWED,
}
REQUEST_LOCATION_PREFIXES = {"body", "query", "path", "header", "cookie"}


def build_error_response(
    *,
    status_code: int,
    code: ErrorCode,
    message: str,
    details: dict[str, JsonValue] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details or {}))
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
        headers=headers,
    )


def error_response_from(error: AppError) -> JSONResponse:
    return build_error_response(
        status_code=error.status_code,
        code=error.code,
        message=error.message,
        details=error.details,
        headers=error.headers,
    )


def format_field_location(location: tuple[int | str, ...]) -> str:
    parts = [str(part) for part in location]
    if parts and parts[0] in REQUEST_LOCATION_PREFIXES:
        parts = parts[1:]
    return ".".join(parts)


async def handle_app_error(_request: Request, error: AppError) -> JSONResponse:
    return error_response_from(error)


async def handle_validation_error(
    _request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    fields: list[JsonValue] = [
        {
            "field": format_field_location(tuple(item["loc"])),
            "code": str(item["type"]),
            "message": str(item["msg"]),
        }
        for item in error.errors()
    ]
    return build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        details={"fields": fields},
    )


async def handle_http_exception(
    _request: Request,
    error: StarletteHTTPException,
) -> JSONResponse:
    code = HTTP_STATUS_ERROR_CODES.get(error.status_code, ErrorCode.HTTP_ERROR)
    message = error.detail if isinstance(error.detail, str) else "HTTP error"
    return build_error_response(
        status_code=error.status_code,
        code=code,
        message=message,
        headers=error.headers,
    )


async def handle_unexpected_error(_request: Request, error: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", error_type=type(error).__name__)
    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.exception_handler(AppError)(handle_app_error)
    app.exception_handler(RequestValidationError)(handle_validation_error)
    app.exception_handler(StarletteHTTPException)(handle_http_exception)
    app.exception_handler(Exception)(handle_unexpected_error)
