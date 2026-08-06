from functools import lru_cache

from redis import Redis
from rq import Queue

from app.core.config import settings


@lru_cache
def get_redis() -> Redis:
    """Shared Redis connection.

    Cached because RQ opens a connection per Queue, and the API enqueues on
    nearly every document action.
    """
    return Redis.from_url(settings.redis_url)


@lru_cache
def get_preparation_queue() -> Queue:
    return Queue(
        settings.preparation_queue_name,
        connection=get_redis(),
        default_timeout=settings.preparation_job_timeout_seconds,
    )


def redis_is_available() -> bool:
    """Whether Redis can currently be reached.

    Used by the health endpoint so a broken queue is visible as a degraded
    service rather than as documents that mysteriously never become ready.
    """
    try:
        return bool(get_redis().ping())
    except Exception:
        return False
