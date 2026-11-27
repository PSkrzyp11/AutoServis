import re
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

REQUEST_ID_HEADER = "X-Request-ID"
VALID_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")
MILLISECONDS_IN_SECOND = 1000

logger = get_logger()


def resolve_request_id(request: Request) -> str:
    incoming_request_id = request.headers.get(REQUEST_ID_HEADER, "")
    if VALID_REQUEST_ID_PATTERN.fullmatch(incoming_request_id):
        return incoming_request_id
    return uuid.uuid4().hex


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = resolve_request_id(request)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started_at = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - started_at) * MILLISECONDS_IN_SECOND, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
