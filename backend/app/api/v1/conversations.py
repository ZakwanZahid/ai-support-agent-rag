import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    enforce_chat_rate_limit,
    enforce_daily_budget,
    get_current_user,
    get_db,
    get_request_chat_provider,
    get_request_embedding_provider,
    require_organization_member,
)
from app.embeddings.provider import EmbeddingProvider
from app.llm.provider import ChatProvider
from app.models.conversation import Conversation
from app.models.organization import OrganizationMember
from app.models.user import User
from app.schemas.conversation import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
)
from app.schemas.pagination import InvalidCursorError, Page
from app.services.conversation_service import (
    ConversationAccessDeniedError,
    ConversationKnowledgeBaseNotFoundError,
    ConversationNotFoundError,
    ConversationService,
)
from app.services.rag_service import (
    RAGConversationNotFoundError,
    RAGKnowledgeBaseMismatchError,
    RAGKnowledgeBaseNotFoundError,
    RAGProviderError,
    RAGService,
)


router = APIRouter(
    prefix="/organizations/{organization_id}/conversations",
    tags=["conversations"],
)


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    organization_id: uuid.UUID,
    data: ConversationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
) -> Conversation:
    try:
        return ConversationService(db).create(
            organization_id=organization_id,
            user=current_user,
            data=data,
        )
    except ConversationKnowledgeBaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    organization_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
) -> list[ConversationResponse]:
    return ConversationService(db).list_for_user(
        organization_id=organization_id,
        user=current_user,
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_conversation(
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
    message_limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ConversationDetailResponse:
    try:
        return ConversationService(db).get_detail(
            organization_id=organization_id,
            conversation_id=conversation_id,
            user=current_user,
            membership=membership,
            message_limit=message_limit,
        )
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    except ConversationAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access this conversation",
        )


@router.post(
    "/{conversation_id}/messages",
    response_model=ChatMessageResponse,
    # The one uncapped spend path in the API: every message is an embedding
    # call plus a completion. Two controls, not one: the rate limit bounds a
    # burst, the budget bounds a day.
    dependencies=[Depends(enforce_chat_rate_limit), Depends(enforce_daily_budget)],
)
def send_chat_message(
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    data: ChatMessageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
    embedding_provider: Annotated[
        EmbeddingProvider,
        Depends(get_request_embedding_provider),
    ],
    chat_provider: Annotated[
        ChatProvider,
        Depends(get_request_chat_provider),
    ],
) -> ChatMessageResponse:
    try:
        return RAGService(
            db=db,
            embedding_provider=embedding_provider,
            chat_provider=chat_provider,
        ).chat(
            organization_id=organization_id,
            conversation_id=conversation_id,
            user=current_user,
            membership=membership,
            data=data,
        )
    except RAGConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    except RAGKnowledgeBaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    except ConversationAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access this conversation",
        )
    except RAGKnowledgeBaseMismatchError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation is associated with a different knowledge base",
        )
    except RAGProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )


@router.get("/{conversation_id}/messages", response_model=Page[MessageResponse])
def list_conversation_messages(
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query()] = None,
) -> Page[MessageResponse]:
    """Older messages in a thread.

    The conversation detail endpoint already returns the newest page; this
    walks backwards from a cursor it hands out. Without a cursor it returns
    that same newest page, so a client can use one endpoint throughout.
    """
    try:
        return ConversationService(db).list_messages(
            organization_id=organization_id,
            conversation_id=conversation_id,
            user=current_user,
            membership=membership,
            limit=limit,
            cursor=cursor,
        )
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    except ConversationAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access this conversation",
        )
    except InvalidCursorError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid pagination cursor",
        )
