"""Structured logging, request correlation, and what must never be logged.

The redaction tests are the ones that earn their place. A credential in a log
line is a credential in every system the logs are shipped to, and log
retention outlives most tokens.
"""

import json
import logging

from fastapi.testclient import TestClient

from app.observability.context import (
    get_actor,
    get_request_id,
    request_context,
    set_actor,
)
from app.observability.errors import _before_send
from app.observability.logging import REDACTED, JSONFormatter, configure_logging


def record(**extra) -> logging.LogRecord:
    logger = logging.getLogger("test.logger")
    return logger.makeRecord(
        "test.logger",
        logging.INFO,
        "file.py",
        10,
        "Something happened",
        (),
        None,
        extra=extra or None,
    )


def formatted(**extra) -> dict:
    return json.loads(JSONFormatter().format(record(**extra)))


def test_a_log_line_is_one_json_object():
    payload = formatted()

    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert payload["message"] == "Something happened"
    assert payload["timestamp"].endswith("+00:00")


def test_extra_fields_become_top_level_keys():
    """`extra=` is how the rest of the code attaches structure.

    Nesting them under a "details" key would mean every query in a log tool
    has to know about the nesting.
    """
    payload = formatted(document_id="abc", duration_ms=12.5)

    assert payload["document_id"] == "abc"
    assert payload["duration_ms"] == 12.5


def test_credentials_are_never_logged_even_when_passed_deliberately():
    payload = formatted(password="hunter2", api_key="sk-live-123", token="abc")

    assert payload["password"] == REDACTED
    assert payload["api_key"] == REDACTED
    assert payload["token"] == REDACTED
    assert "hunter2" not in json.dumps(payload)
    assert "sk-live-123" not in json.dumps(payload)


def test_redaction_reaches_into_nested_values():
    payload = formatted(context={"user": "a@example.com", "access_token": "secret"})

    assert payload["context"]["access_token"] == REDACTED
    assert payload["context"]["user"] == "a@example.com"


def test_values_that_are_not_json_serialisable_do_not_lose_the_line():
    """A UUID in `extra=` should log as itself, not take the message with it."""
    import uuid as uuid_module

    identifier = uuid_module.uuid4()
    payload = formatted(document_id=identifier)

    assert payload["document_id"] == str(identifier)


def test_a_line_logged_inside_a_request_carries_its_id():
    with request_context("req-123"):
        payload = formatted()

    assert payload["request_id"] == "req-123"


def test_a_line_logged_outside_a_request_simply_omits_it():
    payload = formatted()

    assert "request_id" not in payload


def test_the_actor_is_merged_rather_than_replaced():
    """Middleware knows the organization; authentication adds the user later."""
    with request_context():
        set_actor(organization_id="org-1")
        set_actor(user_id="user-1")

        assert get_actor() == {"organization_id": "org-1", "user_id": "user-1"}


def test_actor_ignores_empty_values():
    with request_context():
        set_actor(organization_id=None, user_id="user-1")

        assert get_actor() == {"user_id": "user-1"}


def test_context_is_cleared_when_the_request_ends():
    """Otherwise the next request served by this worker inherits the last one's."""
    with request_context("first"):
        set_actor(user_id="user-1")

    assert get_request_id() is None
    assert get_actor() == {}


def test_an_exception_is_formatted_into_the_line():
    logger = logging.getLogger("test.logger")
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        payload = json.loads(
            JSONFormatter().format(
                logger.makeRecord(
                    "test.logger",
                    logging.ERROR,
                    "file.py",
                    10,
                    "It failed",
                    (),
                    sys.exc_info(),
                )
            )
        )

    assert "ValueError: boom" in payload["exception"]


def test_configure_logging_replaces_handlers_rather_than_adding():
    """Uvicorn installs its own; leaving them prints every line twice."""
    root = logging.getLogger()
    original = list(root.handlers)
    original_level = root.level
    try:
        configure_logging(level="INFO")
        configure_logging(level="INFO")

        assert len(root.handlers) == 1
    finally:
        root.handlers = original
        root.setLevel(original_level)


def test_error_reports_carry_the_request_context():
    with request_context("req-9"):
        set_actor(organization_id="org-1")
        event = _before_send({}, {})

    assert event["tags"]["request_id"] == "req-9"
    assert event["tags"]["organization_id"] == "org-1"


def test_error_reports_drop_credentials_from_the_request():
    event = _before_send(
        {
            "request": {
                "headers": {"Authorization": "Bearer abc", "Accept": "application/json"},
                "cookies": {"session": "xyz"},
            }
        },
        {},
    )

    assert "Authorization" not in event["request"]["headers"]
    assert "cookies" not in event["request"]
    assert event["request"]["headers"]["Accept"] == "application/json"


def test_a_response_carries_the_request_id_back(client: TestClient):
    """So a user can quote the id from a failure and it can be found."""
    response = client.get("/api/v1/health")

    assert response.headers["X-Request-Id"]


def test_an_inbound_request_id_is_reused_rather_than_replaced(client: TestClient):
    """A trace started by a load balancer should survive the hop."""
    response = client.get("/api/v1/health", headers={"X-Request-Id": "from-upstream"})

    assert response.headers["X-Request-Id"] == "from-upstream"


def test_an_absurd_inbound_request_id_is_truncated(client: TestClient):
    response = client.get("/api/v1/health", headers={"X-Request-Id": "x" * 500})

    assert len(response.headers["X-Request-Id"]) == 64
