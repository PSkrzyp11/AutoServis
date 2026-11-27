from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from app.core.dependencies import get_redis
from tests.conftest import TEST_BASE_URL

UNREACHABLE_REDIS_URL = "redis://127.0.0.1:1/0"
FAILING_ROUTE = "/test-only/failure"


@pytest.fixture
async def unreachable_redis() -> AsyncIterator[Redis]:
    client: Redis = Redis.from_url(UNREACHABLE_REDIS_URL, socket_connect_timeout=0.2)
    yield client
    await client.aclose()


async def test_liveness_probe_reports_ok(client: AsyncClient) -> None:
    response = await client.get("/health/live")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "ok"


async def test_readiness_probe_checks_dependencies(client: AsyncClient) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok", "components": {"database": "ok", "redis": "ok"}}


async def test_readiness_probe_reports_unavailable_redis(
    app: FastAPI,
    client: AsyncClient,
    unreachable_redis: Redis,
) -> None:
    app.dependency_overrides[get_redis] = lambda: unreachable_redis

    response = await client.get("/health/ready")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["components"]["redis"] == "unavailable"


async def test_unknown_route_uses_error_format(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_wrong_method_uses_error_format(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/login")

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


async def test_request_id_is_propagated_or_generated(client: AsyncClient) -> None:
    propagated = await client.get("/health/live", headers={"X-Request-ID": "abc-123"})
    generated = await client.get("/health/live", headers={"X-Request-ID": "bad id\n"})

    assert propagated.headers["X-Request-ID"] == "abc-123"
    assert generated.headers["X-Request-ID"] != "bad id\n"
    assert len(generated.headers["X-Request-ID"]) == 32


async def test_unexpected_exception_returns_internal_error(app: FastAPI) -> None:
    async def failing_endpoint() -> None:
        message = "unexpected failure"
        raise RuntimeError(message)

    app.add_api_route(FAILING_ROUTE, failing_endpoint)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url=TEST_BASE_URL) as http:
        response = await http.get(FAILING_ROUTE)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
