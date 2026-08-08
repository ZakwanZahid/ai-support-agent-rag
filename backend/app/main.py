import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware import (
    OrganizationScopeMiddleware,
    RequestLoggingMiddleware,
)
from app.api.router import api_router
from app.core.config import settings
from app.observability.errors import configure_error_reporting
from app.observability.logging import configure_logging


# Configured at import, before anything else has a chance to log. Doing it in
# the lifespan would leave startup lines in whatever format the default
# handler happens to have.
configure_logging(level=settings.log_level, as_json=settings.log_json)
reporting_enabled = configure_error_reporting()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Checked once at startup rather than per request. A role that bypasses
    # row-level security fails silently — everything works, nothing is
    # isolated — so the only way to notice is to look on purpose.
    from app.db.session import engine
    from app.db.tenancy import warn_if_row_level_security_is_bypassed

    enforced = warn_if_row_level_security_is_bypassed(engine)
    logging.getLogger("app.startup").info(
        "Application started",
        extra={
            "environment": settings.app_env,
            "row_level_security": "enforced" if enforced else "bypassed",
            "error_reporting": "on" if reporting_enabled else "off",
            "rate_limiting": "on" if settings.rate_limit_enabled else "off",
            "cors_origins": settings.frontend_origins,
        },
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # All middleware runs before routing, so the tenant scope is in place
    # before any dependency or handler opens a transaction. Added before CORS
    # so CORS stays the outermost layer and can still answer a preflight.
    app.add_middleware(OrganizationScopeMiddleware)
    # Added after, which makes it the outer of the two: the request id has to
    # exist before anything the scope middleware might log.
    app.add_middleware(RequestLoggingMiddleware)

    # Registered unconditionally now. It used to register only when APP_ENV
    # looked local, which meant a deployed frontend was blocked by the
    # browser with nothing in the server logs to explain why — the request
    # never reached FastAPI's routing, so nothing here ever ran to log it.
    # `Settings.validate_cors_is_configured_outside_local` is the other half
    # of the fix: it fails at startup if a non-local deployment forgot to set
    # FRONTEND_ORIGIN, rather than failing silently in the browser later.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(api_router)

    return app


app = create_app()

