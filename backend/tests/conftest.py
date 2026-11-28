import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Environment, Settings, get_settings
from app.core.dependencies import get_event_publisher, get_redis, get_session, get_task_queue
from app.main import create_app
from tests.fakes import FakeEventPublisher, FakeTaskQueue

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TEST_DATABASE_URL = (
    "postgresql+asyncpg://autoservis:autoservis@localhost:5432/autoservis_test"
)
DEFAULT_TEST_REDIS_URL = "redis://localhost:6379/15"
TEST_JWT_SECRET = "test-jwt-secret-key-that-is-longer-than-32-characters"
TEST_PASSWORD_RESET_URL = "http://localhost:3000/nowe-haslo"
TEST_BASE_URL = "http://testserver"


async def recreate_public_schema(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(
        app_env=Environment.TEST,
        database_url=os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL),
        redis_url=os.environ.get("TEST_REDIS_URL", DEFAULT_TEST_REDIS_URL),
        jwt_secret_key=SecretStr(TEST_JWT_SECRET),
        frontend_password_reset_url=TEST_PASSWORD_RESET_URL,
        cookie_secure=False,
        sentry_dsn=None,
    )


@pytest.fixture(scope="session")
def migrated_database(settings: Settings) -> str:
    asyncio.run(recreate_public_schema(settings.database_url))
    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.attributes["database_url"] = settings.database_url
    command.upgrade(alembic_config, "head")
    return settings.database_url


@pytest.fixture
async def engine(migrated_database: str) -> AsyncIterator[AsyncEngine]:
    test_engine = create_async_engine(migrated_database, poolclass=NullPool)
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture
async def redis(settings: Settings) -> AsyncIterator[Redis]:
    client: Redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await client.flushdb()
    yield client
    await client.aclose()


@pytest.fixture
def task_queue() -> FakeTaskQueue:
    return FakeTaskQueue()


@pytest.fixture
def event_publisher() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def app(
    settings: Settings,
    db_session: AsyncSession,
    redis: Redis,
    task_queue: FakeTaskQueue,
    event_publisher: FakeEventPublisher,
) -> FastAPI:
    application = create_app(settings)
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[get_session] = lambda: db_session
    application.dependency_overrides[get_redis] = lambda: redis
    application.dependency_overrides[get_task_queue] = lambda: task_queue
    application.dependency_overrides[get_event_publisher] = lambda: event_publisher
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=TEST_BASE_URL) as http:
        yield http
