import time
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.errors import RateLimitedError


@dataclass(frozen=True)
class RateLimitRule:
    scope: str
    limit: int
    window_seconds: int


class RateLimiter:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def hit(self, rule: RateLimitRule, identifier: str) -> None:
        now = int(time.time())
        window_index = now // rule.window_seconds
        key = f"rate_limit:{rule.scope}:{identifier}:{window_index}"

        async with self._redis.pipeline(transaction=True) as pipeline:
            pipeline.incr(key)
            pipeline.expire(key, rule.window_seconds)
            hits, _ = await pipeline.execute()

        if int(hits) > rule.limit:
            retry_after_seconds = rule.window_seconds - now % rule.window_seconds
            raise RateLimitedError(retry_after_seconds)
