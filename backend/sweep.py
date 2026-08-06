"""Recover documents abandoned by a worker that died mid-preparation.

Run periodically — a cron entry, a scheduled platform task, or RQ's own
scheduler:

    python sweep.py

Without this, a worker killed between claiming a document and finishing it
leaves that document in `processing` forever: the queue has no job for it, and
the API will not start another because the status looks busy.
"""

import logging
import sys

from app.core.config import settings
from app.jobs.enqueue import enqueue_preparation
from app.jobs.sweep import sweep_stale_preparations


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("sweep")


def main() -> int:
    logger.info(
        "Sweeping preparations idle for more than %ds",
        settings.preparation_stale_after_seconds,
    )
    acted_on = sweep_stale_preparations(
        requeue=lambda document_id, organization_id, force: enqueue_preparation(
            document_id, organization_id, force
        )
    )
    if acted_on:
        logger.info("Recovered %d stale document(s): %s", len(acted_on), acted_on)
    else:
        logger.info("Nothing stale")
    return 0


if __name__ == "__main__":
    sys.exit(main())
