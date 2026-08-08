import uuid

from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.embeddings.provider import EmbeddingProvider
from app.llm.provider import ChatProvider, ChatProviderError
from app.models.organization import OrganizationMember
from app.models.user import User
from app.rag.citation_builder import CitationData, build_citations
from app.rag.context_builder import build_context
from app.rag.prompts import (
    GROUNDED_SUPPORT_SYSTEM_PROMPT,
    build_grounded_user_prompt,
)
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.repositories.message_citation_repository import MessageCitationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.conversation import (
    ChatMessageRequest,
    ChatMessageResponse,
    CitationResponse,
)
from app.observability.usage import track_usage
from app.services.conversation_service import (
    ConversationAccessDeniedError,
    ConversationService,
)
from app.services.usage_service import UsageService


NO_CONTEXT_ANSWER = (
    "I do not have enough information in the indexed knowledge base "
    "to answer that question."
)


class RAGConversationNotFoundError(Exception):
    pass


class RAGKnowledgeBaseNotFoundError(Exception):
    pass


class RAGKnowledgeBaseMismatchError(Exception):
    pass


class RAGProviderError(Exception):
    pass


class RAGService:
    def __init__(
        self,
        *,
        db: Session,
        embedding_provider: EmbeddingProvider,
        chat_provider: ChatProvider,
        app_settings: Settings = settings,
    ) -> None:
        self.db = db
        self.embedding_provider = embedding_provider
        self.chat_provider = chat_provider
        self.settings = app_settings
        self.conversations = ConversationRepository(db)
        self.knowledge_bases = KnowledgeBaseRepository(db)
        self.chunks = DocumentChunkRepository(db)
        self.messages = MessageRepository(db)
        self.message_citations = MessageCitationRepository(db)

    def chat(
        self,
        *,
        organization_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user: User,
        membership: OrganizationMember,
        data: ChatMessageRequest,
    ) -> ChatMessageResponse:
        conversation = self.conversations.get_by_id(
            organization_id=organization_id,
            conversation_id=conversation_id,
        )
        if conversation is None:
            raise RAGConversationNotFoundError
        ConversationService.ensure_access(
            conversation=conversation,
            user=user,
            membership=membership,
        )

        knowledge_base = self.knowledge_bases.get_by_id(
            organization_id=organization_id,
            knowledge_base_id=data.knowledge_base_id,
        )
        if knowledge_base is None:
            raise RAGKnowledgeBaseNotFoundError
        if (
            conversation.knowledge_base_id is not None
            and conversation.knowledge_base_id != data.knowledge_base_id
        ):
            raise RAGKnowledgeBaseMismatchError

        user_message = self.messages.create(
            organization_id=organization_id,
            conversation_id=conversation.id,
            role="user",
            content=data.question,
        )
        self.conversations.touch(conversation)
        self.db.commit()
        self.db.refresh(user_message)

        # Everything the providers spend from here on is counted against this
        # organization's daily budget. The scope covers the embedding and the
        # completion together, because a question costs both.
        with track_usage() as usage:
            try:
                return self._answer(
                    organization_id=organization_id,
                    conversation=conversation,
                    user_message=user_message,
                    data=data,
                )
            finally:
                # In `finally` so every exit is counted. A question that
                # retrieved nothing still paid to embed itself, and a
                # completion that failed after the provider billed for it is
                # spend either way — a meter that only counts happy paths
                # under-reports exactly when things are going wrong.
                UsageService(self.db).record(organization_id, usage)

    def _answer(
        self,
        *,
        organization_id: uuid.UUID,
        conversation,
        user_message,
        data: ChatMessageRequest,
    ) -> ChatMessageResponse:
        query_embedding = self.embedding_provider.embed_query(data.question)
        if len(query_embedding) != self.settings.embedding_dimensions:
            raise ValueError(
                f"Expected {self.settings.embedding_dimensions} query dimensions, "
                f"received {len(query_embedding)}"
            )
        # Hybrid rather than vector-only. Structure-aware chunking put rare
        # literal terms into small chunks whose embedding is dominated by the
        # rest of the section, and the eval caught two questions that broke
        # because of it; keyword search fused in by rank repairs exactly those
        # without costing anything on the paraphrases vector search is good at.
        matches = self.chunks.hybrid_search(
            organization_id=organization_id,
            knowledge_base_id=data.knowledge_base_id,
            query_text=data.question,
            query_embedding=query_embedding,
            top_k=data.top_k,
        )

        if not matches:
            return self._save_answer(
                organization_id=organization_id,
                conversation_id=conversation.id,
                user_message_id=user_message.id,
                answer=NO_CONTEXT_ANSWER,
                citations=[],
            )

        context_result = build_context(
            matches,
            max_chars=self.settings.rag_max_context_chars,
        )
        citations = build_citations(context_result.included_matches)
        if not context_result.context:
            return self._save_answer(
                organization_id=organization_id,
                conversation_id=conversation.id,
                user_message_id=user_message.id,
                answer=NO_CONTEXT_ANSWER,
                citations=[],
            )

        try:
            answer = self.chat_provider.generate_answer(
                GROUNDED_SUPPORT_SYSTEM_PROMPT,
                build_grounded_user_prompt(
                    question=data.question,
                    context=context_result.context,
                ),
            )
        except ChatProviderError as exc:
            self.db.rollback()
            raise RAGProviderError(str(exc)) from exc

        return self._save_answer(
            organization_id=organization_id,
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            answer=answer,
            citations=citations,
        )

    def _save_answer(
        self,
        *,
        organization_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_message_id: uuid.UUID,
        answer: str,
        citations: list[CitationData],
    ) -> ChatMessageResponse:
        assistant_message = self.messages.create(
            organization_id=organization_id,
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
        )
        conversation = self.conversations.get_by_id(
            organization_id=organization_id,
            conversation_id=conversation_id,
        )
        if conversation is None:
            raise RAGConversationNotFoundError
        self.conversations.touch(conversation)
        self.message_citations.create_many(
            organization_id=organization_id,
            message_id=assistant_message.id,
            citations=citations,
        )
        self.db.commit()
        self.db.refresh(assistant_message)

        return ChatMessageResponse(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message.id,
            answer=answer,
            citations=[
                CitationResponse(
                    document_id=citation.document_id,
                    document_title=citation.document_title,
                    chunk_id=citation.chunk_id,
                    quote=citation.quote,
                    score=citation.score,
                    chunk_metadata=citation.chunk_metadata,
                )
                for citation in citations
            ],
        )
