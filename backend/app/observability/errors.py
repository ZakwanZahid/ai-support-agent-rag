"""Where an unhandled exception goes.

Wired, not enabled. `SENTRY_DSN` is unset by default and everything here
becomes a no-op, which keeps the dependency optional and means this repository
carries no account, no key, and no vendor lock-in that a reader has to
untangle.

The point of doing it now anyway: the decision about *what* gets reported and
what is scrubbed from it belongs with the code that knows which fields are
sensitive, not with whoever later pastes in a DSN and finds tokens in their
error tracker.
"""

import logging
from typing import Any

from app.core.config import settings
from app.observability.context import get_actor, get_request_id


logger = logging.getLogger(__name__)

_client: Any = None


def configure_error_reporting() -> bool:
    """Initialise the reporter if a DSN is configured. Returns whether it is on."""
    global _client

    dsn = (settings.sentry_dsn or "").strip()
    if not dsn:
        return False

    try:
        import sentry_sdk
    except ImportError:
        # A configured DSN with the package missing is a deployment mistake
        # worth saying out loud, not worth refusing to start over.
        logger.warning(
            "SENTRY_DSN is set but sentry-sdk is not installed; "
            "errors will only be logged"
        )
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.app_env,
        # Errors only. Performance tracing is a separate decision with its own
        # cost, and turning it on by default is how a free tier disappears.
        traces_sample_rate=0.0,
        send_default_pii=False,
        before_send=_before_send,
    )
    _client = sentry_sdk
    return True


def _before_send(event: dict, _hint: dict) -> dict:
    """Attach request context, and drop anything that should not leave here."""
    event.setdefault("tags", {}).update(get_actor())
    request_id = get_request_id()
    if request_id:
        event["tags"]["request_id"] = request_id

    request = event.get("request")
    if isinstance(request, dict):
        # The URL can carry a bearer token if somebody ever puts one there,
        # and headers certainly do.
        request.pop("cookies", None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            for header in ("authorization", "Authorization", "cookie", "Cookie"):
                headers.pop(header, None)
    return event


def report_exception(exc: BaseException) -> None:
    """Send an exception onward if reporting is configured; always log it."""
    logger.exception("Unhandled exception", exc_info=exc)
    if _client is not None:
        _client.capture_exception(exc)
