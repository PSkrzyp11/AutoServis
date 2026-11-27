from enum import StrEnum
from typing import Protocol

from arq.connections import ArqRedis


class TaskName(StrEnum):
    SEND_PASSWORD_RESET_EMAIL = "send_password_reset_email"


class TaskQueue(Protocol):
    async def enqueue_password_reset_email(
        self,
        *,
        recipient: str,
        full_name: str,
        reset_url: str,
    ) -> None: ...


class ArqTaskQueue:
    def __init__(self, pool: ArqRedis) -> None:
        self._pool = pool

    async def enqueue_password_reset_email(
        self,
        *,
        recipient: str,
        full_name: str,
        reset_url: str,
    ) -> None:
        await self._pool.enqueue_job(
            TaskName.SEND_PASSWORD_RESET_EMAIL.value,
            recipient=recipient,
            full_name=full_name,
            reset_url=reset_url,
        )
