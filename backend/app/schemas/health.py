from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    # Preparation depends on Redis. Surfacing it here means a broken queue
    # shows up as a degraded service rather than as documents that
    # mysteriously never become ready.
    queue: str
