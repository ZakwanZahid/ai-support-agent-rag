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

## ADR-023: Product Language in the UI, Backend Language in the API

Status: Accepted

The API keeps its domain vocabulary (organizations, knowledge bases, ingestion, indexing, citations) while the interface speaks only in product terms. A single module, `frontend/src/lib/terminology.ts`, owns the translation: status labels, tones, timeline position, and the decision about whether to keep polling all derive from one table. Components ask that module rather than mapping strings themselves, so the rule is enforced by construction instead of by reviewer memory, and a future rename is one edit. Raw identifiers never reach the interface; where a name is needed, the client resolves it from a list it already holds.

## ADR-024: Workspace and Knowledge Space as Product Terms

Status: Accepted

"Organization" is accurate but reads as billing and administration, and "knowledge base" describes the retrieval mechanism rather than the user's goal. The UI says workspace and knowledge space. The API is unchanged, so this is a presentation decision with no migration cost, and the mapping lives in the terminology module rather than being spelled out per component.

## ADR-025: One Prepare for Chat Action Instead of Ingest and Index

Status: Accepted

Extraction and indexing are two API operations with independent failure modes, which is right for the backend and wrong for the interface: it made the user sequence two calls and guess when the first had finished. `POST /documents/{id}/prepare` runs both server-side in one background task and stops if extraction produces nothing, so clients call one endpoint and poll one status. Ingest and index remain available for operating on a single phase. Doing this server-side rather than orchestrating in the browser keeps the sequencing correct when a client disconnects mid-flow.

## ADR-026: Guided Onboarding Before the Dashboard

Status: Accepted

A new account has no workspace, no knowledge space, and no documents, so the dashboard would open on four empty panels and no clear first move. Users without a workspace or knowledge space are routed to a four-step flow that creates each in turn and finishes with a real question against a real document. The gate is evaluated on entry only: completing a step mid-flow satisfies the condition that sent the user there, and re-checking would eject them before the end.

## ADR-027: Marketing Landing Page at the Root Route

Status: Accepted

The root route previously redirected straight to the dashboard, so an unauthenticated visitor met a login form with no explanation of the product. `/` is now a landing page covering the problem, the three-step flow, features, and use cases. For a portfolio project this is also the page a reviewer sees first, and it carries the positioning that the dashboard cannot.

## ADR-028: Responsive Dashboard with a Drawer Sidebar

Status: Accepted

The application shell uses a fixed sidebar that becomes a dialog-based drawer below the `lg` breakpoint, with a top bar carrying the workspace switcher and account menu. Data-dense views change shape rather than scroll: the documents table becomes stacked cards below `xl`, because the fixed sidebar leaves roughly 736px of content column at 1024px and five columns would have to scroll sideways. Layout is verified by measuring every element against the viewport at 360, 768, 1024, and 1440 rather than by inspection.

## ADR-029: Stock Next.js Instead of the vinext Adapter

Status: Accepted

Frontend v1 built through `vinext` with a Cloudflare Workers adapter. The redesign moved to the standard Next.js CLI. The application already used App Router conventions, so no application code changed; only the toolchain and its dependencies were removed. The reasons are that a pre-1.0 build adapter is a fair thing for a reviewer to question, and the planned deployment target expects standard Next.js output.

## ADR-030: Role-Named Design Tokens

Status: Accepted

Colour is defined once as CSS custom properties named for their role (`surface`, `foreground-muted`, `border-strong`, `success-surface`) and exposed to Tailwind through `@theme`. Components reference roles rather than palette positions, which is what makes a theme change a single file. The primary is a near-black neutral rather than a saturated accent, so colour is reserved for status and a green or amber badge carries meaning instead of competing with decoration.

## ADR-031: Aggregate Counts in List Responses

Status: Accepted

Knowledge bases return `document_count` and `ready_document_count`; conversations return `message_count` and `last_message_preview`. Without these a client renders a list by fetching every child record just to count it. Both use a single grouped or correlated query, so a list costs one round trip regardless of length, and the preview is truncated server-side so the response does not carry whole message bodies.

## ADR-032: Upload No Longer Starts Ingestion Automatically

Status: Accepted

`AUTO_INGEST_ON_UPLOAD` now defaults to false. With it enabled, upload left the document mid-flight in `processing`, so a `prepare` call moments later conflicted with work already running, and the document stalled after extraction with nothing to index it. Preparation is an explicit action that owns the whole lifecycle, which removes the race and matches the single user-facing action described in ADR-025.
