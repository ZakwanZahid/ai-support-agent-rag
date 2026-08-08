"""JSON logs, so that a log aggregator can query them.

Human-readable lines are better on a laptop and worse everywhere else: once
logs are shipped somewhere, `grep`-ing prose is how you end up unable to answer
"which organization saw errors last night". One JSON object per line is
queryable without parsing rules, and every hosted log service already
understands it.

The formatter is applied to the root handler rather than to loggers this code
owns, so libraries — uvicorn, SQLAlchemy — are formatted too. A pipeline with
two log formats in it is a pipeline with one format nobody parses.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.observability.context import get_actor, get_request_id


# Attributes LogRecord always carries. Anything else on a record was put there
# by a caller through `extra=`, and is worth including in the output.
_STANDARD_FIELDS = frozenset(
    {
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "module", "msecs",
        "message", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName", "taskName",
        # uvicorn attaches an ANSI-coloured copy of its own message. Useful in
        # a terminal, noise in a log store, and duplicated data either way.
        "color_message",
    }
)

# Never log these, whatever a caller passes. A bearer token or an API key in a
# log line is a credential in every system the logs are shipped to, and log
# retention is usually longer than the credential's life.
_REDACTED_KEYS = frozenset(
    {
        "password", "token", "access_token", "refresh_token", "authorization",
        "api_key", "openai_api_key", "secret", "jwt_secret_key", "cookie",
    }
)
REDACTED = "[redacted]"


def _scrub(key: str, value: Any) -> Any:
    if key.lower() in _REDACTED_KEYS:
        return REDACTED
    if isinstance(value, dict):
        return {inner: _scrub(inner, item) for inner, item in value.items()}
    return value


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = get_request_id()
        if request_id:
            payload["request_id"] = request_id
        payload.update(get_actor())

        for key, value in record.__dict__.items():
            if key not in _STANDARD_FIELDS and not key.startswith("_"):
                payload[key] = _scrub(key, value)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # `default=str` so a UUID or a datetime in `extra=` logs as itself
        # rather than failing to serialise and losing the whole line.
        return json.dumps(payload, default=str)


def configure_logging(*, level: str = "INFO", as_json: bool = True) -> None:
    """Install one handler on the root logger, replacing any already there.

    Replacing rather than adding: uvicorn installs its own handlers, and
    leaving them in place produces every line twice, once in each format.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(
        JSONFormatter()
        if as_json
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    for name in ("uvicorn", "uvicorn.error"):
        library = logging.getLogger(name)
        library.handlers = []
        library.propagate = True

    # Silenced, not reformatted. `RequestLoggingMiddleware` already logs one
    # line per request with the method, path, status, duration and request id;
    # uvicorn's access log is the same event with less in it, and leaving both
    # on means every request appears twice.
    access = logging.getLogger("uvicorn.access")
    access.handlers = []
    access.propagate = False
