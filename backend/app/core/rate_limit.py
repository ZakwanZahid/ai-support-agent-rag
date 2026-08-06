"""Fixed-window rate limiting, backed by Redis.

Two endpoints groups are protected, for two different reasons. Auth endpoints
are limited per client address, because the risk there is credential stuffing
against an account this server has never seen before. Chat is limited per
organization, because the risk there is spend: every message is an embedding
call plus a completion, and the bill lands on whoever owns the API key, not on
whoever sent the request.

The window is fixed rather than sliding. A fixed window lets a caller send up
to twice the limit across a window boundary, which is the known cost of the
simplest correct implementation: one INCR and one EXPIRE per request, no
stored request log to trim. At these limits the burst is not worth a sorted
set per caller.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitRule:
    """How many requests a single caller may make in one window."""

    name: str
    max_requests: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after: int


class RateLimitBackend(Protocol):
    def hit(self, key: str, rule: RateLimitRule) -> RateLimitDecision:
        """Count one request against `key` and say whether it may proceed."""


class RedisRateLimitBackend:
    """Counts requests in Redis so every API process shares one budget.

    Fails open. If Redis is unreachable the request is allowed through and the
    outage is logged: a limiter that is unavailable should not also be an
    outage of login and chat. This is a deliberate choice about which failure
    is worse, and it means the limiter is a spend and abuse control, not a
    security boundary — the boundaries are authentication and RLS.
    """

    def __init__(self, redis_factory: Callable[[], object]) -> None:
        self._redis_factory = redis_factory

    def hit(self, key: str, rule: RateLimitRule) -> RateLimitDecision:
        try:
            redis = self._redis_factory()
            pipeline = redis.pipeline()
            pipeline.incr(key)
            pipeline.ttl(key)
            count, ttl = pipeline.execute()
        except Exception:
            logger.warning(
                "Rate limiter unavailable, allowing request",
                exc_info=True,
                extra={"rule": rule.name},
            )
            return RateLimitDecision(allowed=True, remaining=rule.max_requests, retry_after=0)

        if ttl is None or ttl < 0:
            # First request in this window, or a key that somehow lost its
            # expiry. Either way the window starts now.
            try:
                redis.expire(key, rule.window_seconds)
            except Exception:
                logger.warning("Could not set rate limit expiry", exc_info=True)
            ttl = rule.window_seconds

        if count > rule.max_requests:
            return RateLimitDecision(allowed=False, remaining=0, retry_after=max(ttl, 1))
        return RateLimitDecision(
            allowed=True,
            remaining=rule.max_requests - count,
            retry_after=0,
        )


class InMemoryRateLimitBackend:
    """Process-local counter, for tests and single-process local runs.

    Not correct across processes — two API workers would each grant the full
    budget — which is exactly why the real backend is Redis.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._windows: dict[str, tuple[float, int]] = {}

    def reset(self) -> None:
        self._windows.clear()

    def hit(self, key: str, rule: RateLimitRule) -> RateLimitDecision:
        now = self._clock()
        expires_at, count = self._windows.get(key, (0.0, 0))
        if now >= expires_at:
            expires_at, count = now + rule.window_seconds, 0

        count += 1
        self._windows[key] = (expires_at, count)

        if count > rule.max_requests:
            return RateLimitDecision(
                allowed=False,
                remaining=0,
                retry_after=max(int(expires_at - now), 1),
            )
        return RateLimitDecision(
            allowed=True,
            remaining=rule.max_requests - count,
            retry_after=0,
        )


def build_key(rule: RateLimitRule, identity: str, window_seconds: int | None = None) -> str:
    """Namespaced key for one caller in one window.

    The window number is part of the key so an expired window can never be
    read as a partially-used one, even if EXPIRE was lost.
    """
    window = window_seconds or rule.window_seconds
    bucket = int(time.time() // window)
    return f"ratelimit:{rule.name}:{identity}:{bucket}"
