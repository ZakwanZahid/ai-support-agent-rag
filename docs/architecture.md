# Architecture

## Overview

AI Support Agent RAG is planned as a production-style support automation system with separate API, frontend, worker, database, cache, and agent orchestration layers.

## High-Level Components

| Component | Technology | Responsibility |
| --- | --- | --- |
| Frontend | Next.js | Customer chat UI, admin dashboard, document management, conversation review |
| Backend API | FastAPI | Auth, REST API, request validation, conversation endpoints, admin operations |
| Agent Orchestration | LangGraph | RAG workflow, tool routing, answer generation, escalation decisions |
| Database | PostgreSQL | Durable relational data for users, organizations, documents, conversations, messages |
| Vector Search | pgvector | Embedding storage and similarity search for document chunks |
| Cache and Broker | Redis | Caching, Celery broker, rate limiting support, transient state |
| Background Workers | Celery | Document ingestion, chunking, embedding generation, re-indexing, async tasks |

## Request Flow

### Chat Answer Flow

1. User sends a support question from the Next.js frontend.
2. FastAPI authenticates the request and stores the user message.
3. The backend invokes the LangGraph support workflow.
4. The retrieval step searches pgvector for relevant chunks.
5. The generation step produces an answer grounded in retrieved context.
6. The backend stores the assistant response and citations.
7. The frontend renders the answer, citations, and escalation options.

### Document Ingestion Flow

1. Admin uploads a document.
2. FastAPI stores document metadata and creates an ingestion job.
3. Celery worker extracts text from the document.
4. Worker chunks the text into retrieval-friendly sections.
5. Worker generates embeddings for each chunk.
6. Chunks and embeddings are stored in PostgreSQL with pgvector.
7. Document status is updated for admin visibility.

## Logical Boundaries

### API Layer

- Owns HTTP contracts.
- Validates input and output schemas.
- Enforces authentication, authorization, and organization boundaries.
- Delegates long-running work to Celery.
- Delegates RAG workflow execution to the agent layer.

### Agent Layer

- Owns support reasoning workflow.
- Performs retrieval, answer generation, citation selection, and escalation classification.
- Should remain framework-isolated enough to test independently from HTTP.

### Worker Layer

- Owns slow or retryable background work.
- Handles ingestion, embedding, re-indexing, cleanup, and scheduled maintenance.
- Must be idempotent where possible.

### Data Layer

- PostgreSQL is the source of truth.
- pgvector is used inside PostgreSQL for vector similarity search.
- Redis is not the source of truth.

## Deployment Shape

Initial deployment is expected to use Docker Compose for local development and a container-based production target.

Planned services:

- `web`: FastAPI backend
- `frontend`: Next.js app
- `worker`: Celery worker
- `scheduler`: Celery beat or equivalent scheduler, if needed
- `postgres`: PostgreSQL with pgvector
- `redis`: Redis broker/cache

## Open Questions

- Which authentication provider will be used?
- Which embedding model and chat model will be used?
- Should uploaded files be stored locally, in object storage, or both?
- Should streaming responses be supported in the first implementation?
- What tenant isolation guarantees are required for production?
