from fastapi import APIRouter

from app.core.config import settings
from app.jobs.queue import redis_is_available
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    queue_available = redis_is_available()
    return HealthResponse(
        # Still "ok" without the queue: the API serves reads and chat fine,
        # only preparation is affected. Reporting a hard failure would be
        # misleading, and reporting nothing would hide a real outage.
        status="ok" if queue_available else "degraded",
        service=settings.app_name,
        environment=settings.app_env,
        queue="available" if queue_available else "unavailable",
    )

@router.get("/")
def root():
    return {"message": "Welcome to the API. Please use the /health endpoint to check the health of the service."}
