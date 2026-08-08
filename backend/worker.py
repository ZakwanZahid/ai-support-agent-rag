"""RQ worker entry point.

Run alongside the API:

    python worker.py

The worker needs the same environment as the API — database URL, Redis URL,
and an OpenAI key — because it does the embedding work the API hands off.
"""

import logging
import os
import sys

from rq import SimpleWorker, Worker
from rq.timeouts import TimerDeathPenalty

from app.core.config import settings
from app.jobs.queue import get_preparation_queue, get_redis
from app.observability.errors import configure_error_reporting
from app.observability.logging import configure_logging


# The same JSON format as the API. A worker whose logs are shaped differently
# from the API's is a worker whose logs get parsed separately, or not at all.
configure_logging(level=settings.log_level, as_json=settings.log_json)
configure_error_reporting()
logger = logging.getLogger("worker")


class WindowsWorker(SimpleWorker):
    """SimpleWorker with a timeout mechanism Windows actually has.

    RQ enforces job timeouts with SIGALRM, which does not exist on Windows.
    TimerDeathPenalty raises the timeout from a background thread instead.
    """

    death_penalty_class = TimerDeathPenalty


def worker_class() -> type[Worker]:
    """Pick a worker implementation the platform can actually run.

    RQ's default worker forks a child process per job, which isolates the job:
    a crash or a runaway allocation takes the child down, and the timeout is
    enforced by killing it. Windows has neither `os.fork` nor SIGALRM, so it
    runs jobs in the worker process with a thread-based timeout.

    The tradeoff is real and worth knowing. Under the Windows worker a job that
    hard-crashes the interpreter takes the worker down with it, and a timeout
    raised from a thread can only interrupt Python code — it will not break
    into a blocking C call. Deployment targets Linux, where the forking worker
    is used; this exists so the queue can be developed and tested on Windows.
    """
    return Worker if hasattr(os, "fork") else WindowsWorker


def main() -> int:
    redis = get_redis()
    try:
        redis.ping()
    except Exception as exc:
        logger.error(
            "Cannot reach Redis at %s: %s. Start it with `docker compose up -d redis`.",
            settings.redis_url,
            exc,
        )
        return 1

    queue = get_preparation_queue()
    implementation = worker_class()
    logger.info(
        "Worker starting on queue '%s' using %s (max %d attempts, backoff %s)",
        queue.name,
        implementation.__name__,
        settings.preparation_max_attempts,
        settings.preparation_retry_intervals,
    )
    if implementation is not Worker:
        logger.warning(
            "This platform has no os.fork, so jobs run inside the worker "
            "process. A crashing job will stop the worker."
        )

    implementation([queue], connection=redis).work(with_scheduler=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
