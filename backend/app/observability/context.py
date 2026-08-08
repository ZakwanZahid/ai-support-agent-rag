"""What every log line should say about the request it came from.

Log lines are only useful in production if you can gather the ones belonging
to a single request. Passing a request id down through every function that
might log is the explicit way to do that and an invasive one — it changes the
signature of code that has no other interest in logging. A context variable
keeps it out of the signatures, at the cost of being invisible at the call
site, which is the trade this makes knowingly.

Same mechanism as the tenant scope in `app/db/tenancy.py`, and the same
caveat: a context variable is set for the current context, so anything that
runs outside it — a thread pool, a background job — starts empty and has to
establish its own.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar


_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_actor: ContextVar[dict[str, str]] = ContextVar("actor", default={})


def new_request_id() -> str:
    return uuid.uuid4().hex


def get_request_id() -> str | None:
    return _request_id.get()


def get_actor() -> dict[str, str]:
    return _actor.get()


def set_actor(**fields: str | None) -> None:
    """Add who this request is on behalf of, once it is known.

    Called after authentication rather than at the start of the request,
    because at the start there is nothing to say. Merges rather than replaces,
    so the organization can be added by middleware and the user later.
    """
    current = dict(_actor.get())
    current.update({key: str(value) for key, value in fields.items() if value})
    _actor.set(current)


@contextmanager
def request_context(request_id: str | None = None) -> Iterator[str]:
    identifier = request_id or new_request_id()
    request_token = _request_id.set(identifier)
    actor_token = _actor.set({})
    try:
        yield identifier
    finally:
        _request_id.reset(request_token)
        _actor.reset(actor_token)
