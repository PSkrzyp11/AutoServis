import asyncio

from fastapi import APIRouter, Response, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import RedisDep, SessionDep
from app.core.logging import get_logger
from app.schemas.health import ComponentStatus, HealthResponse

DEPENDENCY_CHECK_TIMEOUT_SECONDS = 2

logger = get_logger()

router = APIRouter(prefix="/health", tags=["health"])


async def check_database(session: AsyncSession) -> ComponentStatus:
    try:
        async with asyncio.timeout(DEPENDENCY_CHECK_TIMEOUT_SECONDS):
            await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError, TimeoutError):
        logger.warning("database_health_check_failed")
        return ComponentStatus.UNAVAILABLE
    return ComponentStatus.OK


async def check_redis(redis: Redis) -> ComponentStatus:
    try:
        async with asyncio.timeout(DEPENDENCY_CHECK_TIMEOUT_SECONDS):
            await redis.ping()
    except (RedisError, OSError, TimeoutError):
        logger.warning("redis_health_check_failed")
        return ComponentStatus.UNAVAILABLE
    return ComponentStatus.OK


@router.get(
    "/live",
    summary="Liveness probe",
    description="Returns 200 as long as the process is able to serve requests.",
)
async def liveness() -> HealthResponse:
    return HealthResponse(status=ComponentStatus.OK)


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Checks connectivity with PostgreSQL and Redis. Returns 503 if any is down.",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse}},
)
async def readiness(session: SessionDep, redis: RedisDep, response: Response) -> HealthResponse:
    components = {
        "database": await check_database(session),
        "redis": await check_redis(redis),
    }
    is_ready = all(component is ComponentStatus.OK for component in components.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status=ComponentStatus.OK if is_ready else ComponentStatus.UNAVAILABLE,
        components=components,
    )
