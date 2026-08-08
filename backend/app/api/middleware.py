"""Request-level middleware."""

import logging
import re
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.db.tenancy import reset_current_organization, set_current_organization
from app.observability.context import request_context, set_actor
from app.observability.errors import report_exception


logger = logging.getLogger("app.request")

# Health checks are polled continuously by a platform and say nothing when
# they succeed. Logging every one buries the requests that matter.
_QUIET_PATHS = frozenset({"/api/v1/health", "/health"})


# The organization is in the path for tenant routes and in a header for the
# few that take it as context instead. Both are client-supplied, which is
# fine: the scope narrows what a query can reach, it does not grant anything.
# Whether this user may use that organization is still decided by
# `require_organization_member`, and an unauthorized organization id simply
# scopes the request to rows the request is then refused access to anyway.
_ORGANIZATION_IN_PATH = re.compile(
    r"/organizations/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)


def organization_from_request(request: Request) -> str | None:
    match = _ORGANIZATION_IN_PATH.search(request.url.path)
    if match is not None:
        return match.group(1)
    return request.headers.get("X-Organization-Id")


class OrganizationScopeMiddleware(BaseHTTPMiddleware):
    """Puts the requested organization into scope for the whole request.

    Runs before dependency resolution, so the scope is already in place by the
    time anything opens a transaction. Always resets, so a worker thread that
    handles the next request does not inherit this one's tenant.
    """

    async def dispatch(self, request: Request, call_next):
        token = set_current_organization(organization_from_request(request))
        try:
            return await call_next(request)
        finally:
            reset_current_organization(token)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """One log line per request, and a request id that ties the rest together.

    The id is taken from an inbound `X-Request-Id` when there is one, so a
    trace started by a load balancer or another service survives the hop, and
    generated otherwise. It goes back out on the response, which is what makes
    it possible for a user to quote the id from a failure.
    """

    async def dispatch(self, request: Request, call_next):
        inbound = request.headers.get("X-Request-Id")
        # Bounded and stripped of anything unexpected: the value is client
        # supplied and ends up in every log line for this request.
        candidate = inbound[:64].strip() if inbound else None

        with request_context(candidate or None) as request_id:
            organization = organization_from_request(request)
            if organization:
                set_actor(organization_id=organization)

            started = time.perf_counter()
            try:
                response = await call_next(request)
            except Exception as exc:
                # Logged and reported here because further up the stack there
                # is no request context left to attach it to.
                report_exception(exc)
                logger.error(
                    "Request failed",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round(
                            (time.perf_counter() - started) * 1000, 2
                        ),
                    },
                )
                raise

            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            response.headers["X-Request-Id"] = request_id

            if request.url.path not in _QUIET_PATHS:
                logger.info(
                    "Request completed",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    },
                )
            return response
