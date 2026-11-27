import asyncio
from collections.abc import Mapping
from pathlib import Path

from alembic import context
from alembic.script import write_hooks
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.models import Base

DATABASE_URL_ATTRIBUTE = "database_url"
COMMENT_PREFIX = "#"

config = context.config
target_metadata = Base.metadata


@write_hooks.register("strip_comment_lines")
def strip_comment_lines(filename: str, _options: Mapping[str, str]) -> None:
    path = Path(filename)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    kept_lines = [line for line in lines if not line.lstrip().startswith(COMMENT_PREFIX)]
    path.write_text("".join(kept_lines), encoding="utf-8")


def resolve_database_url() -> str:
    configured_url = config.attributes.get(DATABASE_URL_ATTRIBUTE)
    if isinstance(configured_url, str):
        return configured_url
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=resolve_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_with_connection(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(resolve_database_url(), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(run_migrations_with_connection)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
