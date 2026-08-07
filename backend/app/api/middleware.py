"""Request-level middleware."""

import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.db.tenancy import reset_current_organization, set_current_organization


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
