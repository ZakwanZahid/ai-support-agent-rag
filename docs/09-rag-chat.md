# RAG Chat with Citations

## Purpose

The RAG chat API turns a user question into a grounded support answer. It searches one organization's selected knowledge base, gives the retrieved text to a chat model, stores the conversation history, stores traceable citations, and returns the answer with source metadata.

The main endpoint is:

```http
POST /api/v1/organizations/{organization_id}/conversations/{conversation_id}/messages
```

RAG chat is deliberately non-streaming and service-based in this milestone. It does not use LangGraph, a job queue, tools, or ticket escalation.

## Semantic Search Compared with RAG Chat

Semantic search stops after retrieval. It returns ranked chunks so developers can inspect similarity, metadata, and tenant filters:

```text
question -> query embedding -> pgvector retrieval -> ranked chunks
```

RAG chat continues from those chunks to generate and persist a support answer:

```text
question
  -> query embedding
  -> tenant-scoped pgvector retrieval
  -> bounded context building
  -> grounded LLM answer
  -> assistant message
  -> stored citations
  -> answer + citation metadata
```

Search is useful for retrieval debugging. RAG chat is the user-facing answering workflow.

## Endpoints

### Create a Conversation

```http
POST /api/v1/organizations/{organization_id}/conversations
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Refund policy question",
  "knowledge_base_id": "optional UUID"
}
```

The authenticated user must belong to the organization. An optional knowledge base must belong to the same organization. A conversation created with a knowledge base is bound to it; a later chat request using a different knowledge base returns `409 Conflict`.

### List Current User Conversations

```http
GET /api/v1/organizations/{organization_id}/conversations
Authorization: Bearer <token>
```

The MVP list contains only conversations owned by the authenticated user in that organization.

### Get a Conversation and Messages

```http
GET /api/v1/organizations/{organization_id}/conversations/{conversation_id}
Authorization: Bearer <token>
```

Users can read their own conversations. Organization owners and admins can read another member's conversation in the same organization. Other members receive `403 Forbidden`. A conversation outside the organization is treated as not found.

### Send a RAG Chat Message

```http
POST /api/v1/organizations/{organization_id}/conversations/{conversation_id}/messages
Authorization: Bearer <token>
Content-Type: application/json

{
  "question": "What is the refund policy?",
  "knowledge_base_id": "UUID",
  "top_k": 5
}
```

`top_k` defaults to `RAG_TOP_K`. It can be between 1 and 50.

Example response:

```json
{
  "conversation_id": "85a3b54c-80b9-4e89-a1de-a1fb9e81a7bb",
  "user_message_id": "fc458f1a-c869-4ed8-b025-bff35af2915b",
  "assistant_message_id": "bb863a4c-9ddf-42ab-a61d-946cf96ea978",
  "answer": "Customers can request a refund within 14 days of purchase.",
  "citations": [
    {
      "document_id": "c88fc21f-42c5-43dc-96f4-aa551edcd6a5",
      "document_title": "sample-faq",
      "chunk_id": "2ba67af6-3c33-44a5-8a46-2686b535781a",
      "quote": "Customers can request a refund within 14 days of purchase.",
      "score": 0.89,
      "chunk_metadata": {
        "chunk_index": 0
      }
    }
  ]
}
```

## Full RAG Flow

1. The route authenticates the user and resolves their organization membership.
2. The service loads the conversation using both `conversation_id` and `organization_id`.
3. The service verifies conversation ownership, allowing an owner or admin override.
4. The selected knowledge base is loaded using both `knowledge_base_id` and `organization_id`.
5. The question is stored as a user message with `organization_id`.
6. The existing embedding provider embeds the question.
7. The existing semantic-retrieval repository searches only indexed chunks whose embeddings are not null. Both the chunk and joined document are filtered by `organization_id`, and the document is filtered by `knowledge_base_id`.
8. Retrieved chunks become readable `[source N]` context blocks containing document ID, chunk ID, title, and content.
9. Context is capped by `RAG_MAX_CONTEXT_CHARS`. Only chunks actually included in the bounded context become citations.
10. The chat provider receives the grounding system prompt and the question plus context.
11. The assistant answer and all of its citation rows are committed together.
12. The API returns IDs, answer text, and citation metadata.

The user message is committed before the external chat-model call. If that call fails, the question remains in conversation history, but no fake assistant answer or citation is saved. The API returns `502 Bad Gateway` for a provider generation failure.

## Grounding and Prompt Design

Grounding makes the answer auditable and reduces unsupported policy claims. The model is instructed to:

- Act as an AI support assistant.
- Use only the supplied context.
- Say it does not have enough information when the answer is absent.
- Never invent refund, shipping, pricing, or other policy details.
- Stay concise, clear, and helpful.
- Explicitly mention conflicting information when retrieved documents disagree.
- Leave citation metadata to the application instead of inventing source IDs.

The application, not the model, creates citations from retrieved records. This means citation identity does not depend on the model formatting an ID correctly.

## Citation Creation and Storage

Each context chunk becomes one citation containing:

- Tenant `organization_id`
- Assistant `message_id`
- Source `document_id`
- Exact `chunk_id`
- A whitespace-normalized, bounded quote
- Cosine similarity score (`1 - distance`)

The API also returns document title and chunk metadata from the retrieved source.

Citations live in `message_citations` instead of being embedded in assistant text. Separate rows preserve foreign keys to documents and chunks, support audits, make source metadata queryable, and allow citation behavior to evolve without rewriting message content. Citations are created only for assistant messages.

## Conversation and Message Lifecycle

```text
conversation created
  -> user message committed
  -> retrieval
  -> assistant message + citations committed atomically
  -> conversation detail returns ordered messages and citations
```

When no indexed chunks exist, the service stores and returns:

> I do not have enough information in the indexed knowledge base to answer that question.

No LLM call is made and the assistant message has no citations.

## Tenant Isolation

Tenant isolation is enforced at every boundary:

- Organization membership is required before route execution.
- Conversation reads include `organization_id`.
- Knowledge-base reads include `organization_id`.
- Retrieval filters both `document_chunks.organization_id` and `documents.organization_id`.
- Retrieval always filters the selected `knowledge_base_id`.
- Only chunks with non-null embeddings are eligible.
- Every saved message and citation includes `organization_id`.
- Citation foreign keys point to the exact retrieved document and chunk.

An ID from another tenant therefore cannot be used to read a conversation, select a knowledge base, retrieve a chunk, or save a message in the current organization.

## Chat Provider Abstraction

RAG services and routes depend only on:

```python
generate_answer(system_prompt: str, user_prompt: str) -> str
```

Only `app/llm/openai_provider.py` imports the OpenAI SDK. The factory selects the adapter from `CHAT_PROVIDER`, and model and temperature come from settings. A Gemini, Anthropic, or local adapter can later implement the same protocol and be added to the factory without changing retrieval, prompting, persistence, or routes.

Required configuration:

```env
OPENAI_API_KEY=
CHAT_PROVIDER=openai
CHAT_MODEL=gpt-4o-mini
CHAT_TEMPERATURE=0.2
RAG_TOP_K=5
RAG_MAX_CONTEXT_CHARS=12000
```

## Swagger Manual Verification

Start PostgreSQL, apply migrations, and run the API. Open `http://127.0.0.1:8000/docs`, then:

1. Call `POST /api/v1/auth/register`.
2. Call `POST /api/v1/auth/login` and copy `access_token`.
3. Select **Authorize** in Swagger and enter `Bearer <access_token>`.
4. Call `POST /api/v1/organizations` and copy the organization ID.
5. Call `POST /api/v1/organizations/{organization_id}/knowledge-bases` and copy the knowledge-base ID.
6. Call the document upload endpoint with a text file containing a testable policy.
7. Call `POST /api/v1/organizations/{organization_id}/documents/{document_id}/ingest`.
8. Call `POST /api/v1/organizations/{organization_id}/documents/{document_id}/index`.
9. Call `POST /api/v1/organizations/{organization_id}/conversations` using the knowledge-base ID.
10. Call `POST /api/v1/organizations/{organization_id}/conversations/{conversation_id}/messages` with a question answered by the document.
11. Confirm the answer contains only facts from the uploaded document.
12. Confirm the response contains the expected document ID, chunk ID, quote, score, and chunk metadata.
13. In pgAdmin, confirm the conversation has one `user` and one `assistant` message.
14. In pgAdmin, confirm `message_citations` has rows linked to the assistant message and none linked to the user message.

Useful pgAdmin queries:

```sql
SELECT id, organization_id, user_id, knowledge_base_id, title, created_at
FROM conversations
WHERE id = '<conversation_id>';

SELECT id, organization_id, conversation_id, role, content, created_at
FROM messages
WHERE conversation_id = '<conversation_id>'
ORDER BY created_at, id;

SELECT
    mc.id,
    mc.organization_id,
    mc.message_id,
    m.role,
    mc.document_id,
    mc.chunk_id,
    mc.quote,
    mc.score
FROM message_citations AS mc
JOIN messages AS m ON m.id = mc.message_id
WHERE m.conversation_id = '<conversation_id>'
ORDER BY mc.created_at, mc.id;
```

## Automated Tests

The test suite overrides the embedding and chat provider dependencies. It never calls the real OpenAI API. Coverage includes authentication, membership, cross-tenant knowledge bases, message and citation persistence, no-context answers, conversation ownership, and chat-provider failure behavior.

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

## Current Limitations

- No streaming
- No reranking
- No conversation-memory summarization
- No tool use
- No LangGraph orchestration

## Future Improvements

- Streaming responses
- Cross-encoder or model-based reranking
- Conversation-memory summarization
- LangGraph RAG flow
- Human escalation
- Support ticket creation
- RQ or Celery workers
- Observability, tracing, latency metrics, and model-cost reporting
