import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    get_request_embedding_provider,
    require_organization_member,
)
from app.embeddings.provider import EmbeddingProvider
from app.models.organization import OrganizationMember
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import (
    SearchKnowledgeBaseNotFoundError,
    SearchService,
)


router = APIRouter(
    prefix="/organizations/{organization_id}/knowledge-bases/{knowledge_base_id}",
    tags=["search"],
)


@router.post("/search", response_model=SearchResponse)
def semantic_search(
    organization_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    data: SearchRequest,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
    embedding_provider: Annotated[
        EmbeddingProvider,
        Depends(get_request_embedding_provider),
    ],
) -> SearchResponse:
    try:
        return SearchService(
            db=db,
            embedding_provider=embedding_provider,
        ).search(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            data=data,
        )
    except SearchKnowledgeBaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
