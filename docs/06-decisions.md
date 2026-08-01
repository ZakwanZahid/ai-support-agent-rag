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
