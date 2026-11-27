from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.pagination import PageParams

LIKE_ESCAPE_CHARACTER = "\\"


def escape_like_pattern(value: str) -> str:
    return (
        value.replace(LIKE_ESCAPE_CHARACTER, LIKE_ESCAPE_CHARACTER * 2)
        .replace("%", f"{LIKE_ESCAPE_CHARACTER}%")
        .replace("_", f"{LIKE_ESCAPE_CHARACTER}_")
    )


def contains_pattern(value: str) -> str:
    return f"%{escape_like_pattern(value.strip())}%"


async def fetch_page[ModelT](
    session: AsyncSession,
    query: Select[ModelT],
    conditions: Sequence[ColumnElement[bool]],
    order_by: Sequence[ColumnElement[Any]],
    page: PageParams,
) -> tuple[Sequence[ModelT], int]:
    filtered = query.where(*conditions)
    total = await session.scalar(select(func.count()).select_from(filtered.subquery()))
    result = await session.execute(
        filtered.order_by(*order_by).limit(page.limit).offset(page.offset)
    )
    return result.scalars().all(), total or 0
