# Architecture Decisions

## ADR-001: Shared Database, Shared Schema, Organization ID

Status: Accepted

The MVP uses one PostgreSQL database and one shared schema. Tenant-owned tables carry `organization_id` directly. This keeps local operations simple, supports efficient tenant filters, and prepares the system for PostgreSQL Row Level Security. The tradeoff is that tenant scoping must be enforced consistently in application queries until RLS is added.

## ADR-002: PostgreSQL and pgvector for MVP Retrieval

Status: Accepted

Embeddings live beside chunk metadata in PostgreSQL through pgvector rather than in a separate vector database. This reduces infrastructure, preserves transactional relationships, and is sufficient for the expected MVP scale. A dedicated vector system remains an option if scale or retrieval requirements outgrow PostgreSQL.

## ADR-003: SQLAlchemy and Alembic for Schema Control

Status: Accepted

SQLAlchemy 2.0 declarative models define the application schema, and Alembic records the database history. This gives the backend typed relationships, reviewable migrations, repeatable local setup, and a controlled path to production schema changes.

## ADR-004: Citations Stored Separately from Messages

Status: Accepted

`message_citations` is a separate table rather than JSON embedded in a message. Each citation can point to the source document and exact chunk, preserving traceability, supporting audits and feedback analysis, and allowing retrieval metadata to evolve independently of chat content.

## ADR-005: Separate Upload from Ingestion

Status: Accepted

Upload stores the original file and a pending database record. Ingestion independently extracts and chunks that stored file. This keeps HTTP uploads responsive, gives failures a retry path, and creates a clear boundary for a future worker service.

## ADR-006: FastAPI BackgroundTasks for MVP Ingestion

Status: Accepted

The MVP schedules ingestion with FastAPI `BackgroundTasks`, and each task opens its own database session. This avoids introducing queue infrastructure before ingestion behavior is proven. The tradeoff is that tasks are not durable across process restarts, so RQ, Celery, or a dedicated worker is expected as the workload grows.

## ADR-007: Simple Custom Chunking Before Framework Splitters

Status: Accepted

The first splitter is a small character-based implementation with overlap and readable-boundary detection. Keeping it local makes chunk boundaries and metadata easy to inspect and demonstrates the underlying mechanics before evaluating LangChain or another framework splitter.

## ADR-008: Nullable Embeddings Until Indexing

Status: Accepted

Text extraction creates chunks with null embeddings and marks the document processed. Embedding generation is a separate indexing phase that will move documents to indexed. This separates deterministic file processing from model-dependent external calls and allows either phase to be retried independently.

## ADR-009: Provider Abstraction for Embeddings

Status: Accepted

Indexing and search depend on a small provider interface rather than an SDK-specific client. OpenAI is selected through a factory, while Gemini, Cohere, Voyage, or local sentence-transformer adapters can later implement the same contract. This contains provider-specific configuration and API behavior.

## ADR-010: OpenAI text-embedding-3-small for MVP

Status: Accepted

The MVP uses OpenAI `text-embedding-3-small`. It is practical, fast, widely supported, and fits the project's current PostgreSQL vector schema. Provider batching reduces request overhead while explicit dimension validation prevents incompatible vectors from reaching the database.

## ADR-011: Store Embeddings in PostgreSQL pgvector

Status: Accepted

Chunk vectors remain beside tenant IDs, document relationships, metadata, and content in PostgreSQL. pgvector supplies cosine-distance ordering and the existing HNSW index without introducing a separate vector database for the MVP.

## ADR-012: Use 1536-dimensional OpenAI Embeddings for MVP

Status: Accepted

Context:

The `document_chunks` table stores vector embeddings for semantic search. The vector column needs a fixed dimensionality.

Decision:

Use OpenAI `text-embedding-3-small` with 1,536-dimensional embeddings for the MVP.

Reasoning:

It is practical, fast, widely supported, and fits the current pgvector schema. The embedding provider is hidden behind an abstraction so other providers can be added later.

Consequences:

Changing to a model with a different embedding size, such as a 384-dimensional local Sentence Transformer, will require a schema migration and re-indexing all chunks.

## ADR-013: Add Search Before RAG Chat

Status: Accepted

A direct semantic-search endpoint ships before chat answer generation. It exposes chunk ranking, distance, metadata, and tenant filters directly, making retrieval relevance and isolation easier to test before prompts, citations, and model-generated answers add more variables.

## ADR-014: Add RAG Chat After Semantic Search

Status: Accepted

RAG chat is added only after tenant-scoped semantic search is working and tested. The chat flow reuses the proven embedding and retrieval path, then adds bounded context, grounded generation, persistence, and citations. This sequencing isolates retrieval quality from generation quality and makes failures easier to diagnose.

## ADR-015: Provider Abstraction for Chat Models

Status: Accepted

RAG services depend on a small `generate_answer(system_prompt, user_prompt)` protocol. OpenAI SDK details stay inside the OpenAI adapter, while selection happens in a factory. Gemini, Anthropic, or a local model can be added later without coupling routes, retrieval, prompting, or persistence to a vendor SDK.

## ADR-016: Simple RAG Service Before LangGraph

Status: Accepted

The first RAG workflow is an explicit synchronous service rather than a LangGraph graph. The flow is currently linear, has no tools or branching, and benefits from easy transaction boundaries and straightforward tests. LangGraph remains appropriate when orchestration adds routing, tool calls, retries, memory workflows, or human handoffs.

## ADR-017: Return Citation Metadata with the Answer

Status: Accepted

The chat response returns document ID, document title, chunk ID, quote, score, and chunk metadata alongside the answer. Clients can show sources immediately without parsing model-generated markdown or making an additional request. Citation identity is built by the application from retrieved rows, not invented by the model.

## ADR-018: Next.js App Router for the Frontend

Status: Accepted

Frontend v1 uses Next.js with the App Router and TypeScript. Nested layouts provide a natural boundary between public authentication pages and the protected dashboard shell, while file-based routes map directly to product areas and conversation detail views. This keeps routing and page composition explicit without introducing a separate routing framework.

## ADR-019: Tailwind CSS and shadcn/ui-Style Components

Status: Accepted

The frontend uses Tailwind CSS for design tokens and responsive layout, with reusable shadcn/ui-style primitives composed into project-specific components. This supports a restrained custom interface without committing the project to an opaque theme or a large component suite. Accessibility states, spacing, borders, and status colors remain consistent while product components stay editable in the repository.

## ADR-020: TanStack Query for Server State

Status: Accepted

Current-user, organization, knowledge-base, document, conversation, and message data come from the FastAPI backend and are managed as server state through TanStack Query. Query keys make tenant scope explicit, and targeted invalidation keeps reads fresh after writes. Local component state remains appropriate for transient UI such as open dialogs or draft input.

## ADR-021: localStorage JWT for MVP

Status: Accepted for MVP

Frontend v1 stores the API access token in browser `localStorage` and attaches it through the shared Axios client. This matches the existing bearer-token backend and keeps local setup straightforward. The tradeoff is exposure to token theft if an XSS vulnerability exists. A production authentication milestone should move session credentials to `Secure`, `HttpOnly` cookies with appropriate same-site and CSRF controls.

## ADR-022: Build the Frontend After the RAG API

Status: Accepted

The product UI is added after authentication, organization isolation, document ingestion and indexing, semantic search, and RAG chat with citations are working through the API. As a result, Frontend v1 can exercise the real upload-to-answer lifecycle rather than designing against guessed contracts or placeholder messages. The backend remains the authorization and tenant-isolation boundary.
