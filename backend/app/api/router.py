from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(api_v1_router, prefix=settings.api_v1_prefix)
