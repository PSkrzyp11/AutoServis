from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import create_engine, create_session_factory
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.core.redis import create_redis
from app.core.sentry import configure_sentry
from app.ws.hub import RealtimeHub
from app.ws.manager import ConnectionManager

API_TITLE = "AutoServis API"
API_VERSION = "0.1.0"
API_DESCRIPTION = (
    "REST API of the AutoServis platform connecting car owners with car repair workshops."
)
OPENAPI_TAGS = [
    {"name": "auth", "description": "Registration, sign in, session refresh and password reset"},
    {"name": "users", "description": "Operations on the currently signed in user"},
    {
        "name": "workshops",
        "description": "Public workshop search and workshop management for staff",
    },
    {"name": "vehicles", "description": "Vehicles owned by the signed in user"},
    {
        "name": "appointments",
        "description": "Availability, bookings for clients and the workshop calendar for staff",
    },
    {
        "name": "orders",
        "description": "Service orders with their status workflow for staff and clients",
    },
    {"name": "notifications", "description": "In-app notifications of the signed in user"},
    {"name": "realtime", "description": "Tickets for the realtime WebSocket connection"},
    {"name": "admin", "description": "Platform administration, available to ADMIN only"},
    {"name": "health", "description": "Liveness and readiness probes"},
]

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = create_engine(settings)
    redis = create_redis(settings)
    arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))

    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.redis = redis
    app.state.arq_pool = arq_pool
    realtime_hub = RealtimeHub(redis, app.state.realtime_manager)
    await realtime_hub.start()
    logger.info("application_started", environment=settings.app_env.value)
    try:
        yield
    finally:
        await realtime_hub.stop()
        await arq_pool.aclose()
        await redis.aclose()
        await engine.dispose()
        logger.info("application_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    configure_sentry(resolved_settings)

    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.realtime_manager = ConnectionManager()
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router)
    return app
