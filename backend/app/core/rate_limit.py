import math
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.errors import RateLimitedError

MILLISECONDS_PER_SECOND = 1000
MINIMUM_RETRY_AFTER_SECONDS = 1


@dataclass(frozen=True)
class RateLimitRule:
    scope: str
    limit: int
    window_seconds: int


class RateLimiter:
    def __init__(self, redis: Redis, clock: Callable[[], float] = time.time) -> None:
        self._redis = redis
        self._clock = clock

    async def hit(self, rule: RateLimitRule, identifier: str) -> None:
        now_ms = int(self._clock() * MILLISECONDS_PER_SECOND)
        window_ms = rule.window_seconds * MILLISECONDS_PER_SECOND
        key = f"rate_limit:{rule.scope}:{identifier}"
        attempt = f"{now_ms}:{secrets.token_hex(8)}"

        async with self._redis.pipeline(transaction=True) as pipeline:
            pipeline.zremrangebyscore(key, "-inf", now_ms - window_ms)
            pipeline.zadd(key, {attempt: now_ms})
            pipeline.zcard(key)
            pipeline.zrange(key, 0, 0, withscores=True)
            pipeline.expire(key, rule.window_seconds)
            _, _, hits, oldest, _ = await pipeline.execute()

        if int(hits) <= rule.limit:
            return

        await self._redis.zrem(key, attempt)
        oldest_attempt_ms = int(oldest[0][1])
        retry_after_ms = oldest_attempt_ms + window_ms - now_ms
        retry_after_seconds = max(
            MINIMUM_RETRY_AFTER_SECONDS, math.ceil(retry_after_ms / MILLISECONDS_PER_SECOND)
        )
        raise RateLimitedError(retry_after_seconds)
