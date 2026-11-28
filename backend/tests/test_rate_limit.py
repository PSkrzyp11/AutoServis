import pytest
from redis.asyncio import Redis

from app.core.errors import RateLimitedError
from app.core.rate_limit import RateLimiter, RateLimitRule

RULE = RateLimitRule(scope="test", limit=3, window_seconds=60)
IDENTIFIER = "203.0.113.7"
SECONDS_BEFORE_FULL_MINUTE = 1_700_000_039.9


class ManualClock:
    def __init__(self, start: float) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


async def exhaust_limit(limiter: RateLimiter, clock: ManualClock) -> None:
    for _ in range(RULE.limit):
        await limiter.hit(RULE, IDENTIFIER)
        clock.advance(0.1)


async def test_limit_holds_across_full_minute_boundary(redis: Redis) -> None:
    clock = ManualClock(SECONDS_BEFORE_FULL_MINUTE)
    limiter = RateLimiter(redis, clock)

    await exhaust_limit(limiter, clock)

    with pytest.raises(RateLimitedError):
        await limiter.hit(RULE, IDENTIFIER)


async def test_retry_after_counts_from_oldest_attempt(redis: Redis) -> None:
    clock = ManualClock(SECONDS_BEFORE_FULL_MINUTE)
    limiter = RateLimiter(redis, clock)
    await exhaust_limit(limiter, clock)
    clock.advance(20)

    with pytest.raises(RateLimitedError) as error:
        await limiter.hit(RULE, IDENTIFIER)

    assert error.value.details == {"retry_after_seconds": 40}


async def test_rejected_attempts_do_not_extend_the_block(redis: Redis) -> None:
    clock = ManualClock(SECONDS_BEFORE_FULL_MINUTE)
    limiter = RateLimiter(redis, clock)
    await exhaust_limit(limiter, clock)

    for _ in range(5):
        with pytest.raises(RateLimitedError):
            await limiter.hit(RULE, IDENTIFIER)
        clock.advance(10)

    clock.advance(RULE.window_seconds - 50)

    await limiter.hit(RULE, IDENTIFIER)


async def test_identifiers_are_limited_separately(redis: Redis) -> None:
    clock = ManualClock(SECONDS_BEFORE_FULL_MINUTE)
    limiter = RateLimiter(redis, clock)
    await exhaust_limit(limiter, clock)

    await limiter.hit(RULE, "198.51.100.2")
