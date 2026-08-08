from fastapi import APIRouter

from app.api.v1.conversations import router as conversations_router
from app.api.v1.documents import router as documents_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.indexing import router as indexing_router
from app.api.v1.knowledge_bases import router as knowledge_bases_router
from app.api.v1.preparation import router as preparation_router
from app.api.v1.search import router as search_router
from app.api.v1.usage import router as usage_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.organizations import router as organizations_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(auth_router)
api_v1_router.include_router(organizations_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(knowledge_bases_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(ingestion_router)
api_v1_router.include_router(indexing_router)
api_v1_router.include_router(preparation_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(usage_router)

