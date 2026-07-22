# System Design Decisions

## Overview

This document records major design decisions for the AI Support Agent RAG project. It should evolve into an Architecture Decision Record (ADR) index as implementation begins.

## Decision Log

| Status | Decision | Rationale |
| --- | --- | --- |
| Proposed | Use FastAPI for the backend API | Strong Python ecosystem support, automatic OpenAPI generation, async-friendly request handling |
| Proposed | Use PostgreSQL as the primary database | Reliable relational source of truth with mature operational tooling |
| Proposed | Use pgvector for vector search | Keeps metadata, chunks, and embeddings close to relational data in the first production iteration |
| Proposed | Use Redis for broker and cache duties | Simple fit for Celery broker use cases and transient application state |
| Proposed | Use Celery for background jobs | Mature Python task queue for ingestion, embedding, retries, and scheduled work |
| Proposed | Use LangGraph for agent orchestration | Explicit graph-based control over retrieval, generation, tool use, and escalation paths |
| Proposed | Use Next.js for the frontend | Supports admin dashboard, customer chat UI, and production deployment patterns |

## Key Design Areas

### Multi-Tenancy

Current direction:

- Use organization-scoped records across core tables.
- Enforce organization boundaries in API queries and service logic.
- Avoid relying only on frontend filtering.

Open decision:

- Whether to add PostgreSQL row-level security.

### RAG Retrieval

Current direction:

- Store document chunks and embeddings in PostgreSQL with pgvector.
- Retrieve top relevant chunks per organization.
- Return citations tied to stored chunk IDs.

Open decisions:

- Embedding model.
- Chunking strategy.
- Hybrid keyword plus vector search.
- Reranking strategy.

### Agent Workflow

Current direction:

- Use LangGraph to model answer generation as explicit steps.
- Keep retrieval, generation, citation formatting, and escalation checks testable.

Open decisions:

- Whether escalation is rule-based, model-based, or hybrid.
- Whether the first implementation should support tool calls beyond retrieval.

### Background Processing

Current direction:

- Use Celery for document ingestion and embedding jobs.
- Make ingestion jobs retryable and observable.

Open decisions:

- File storage location.
- Dead-letter handling.
- Scheduling mechanism for cleanup and re-indexing.

### API Style

Current direction:

- REST API generated and documented through FastAPI OpenAPI.
- Synchronous chat endpoint for the first version unless streaming is required.

Open decisions:

- API versioning.
- Streaming protocol.
- Public widget authentication model.

### Observability

Current direction:

- Track request IDs, job IDs, conversation IDs, and model usage metadata.

Open decisions:

- Logging format.
- Metrics backend.
- Tracing provider.
- RAG evaluation storage.

## Risks

- Poor chunking can produce low-quality answers even with a good model.
- Missing tenant isolation checks can expose sensitive support data.
- Long document ingestion can fail silently without strong job visibility.
- Storing too much conversation metadata without retention rules can create compliance risk.
- Streaming and real-time UI can add complexity before the core RAG workflow is proven.

## ADR Template

Use this format when decisions become final:

```text
## ADR-000: Decision Title

Status: Proposed | Accepted | Superseded
Date: YYYY-MM-DD

### Context

What problem or constraint led to this decision?

### Decision

What are we choosing?

### Consequences

What tradeoffs, benefits, and risks follow from this choice?
```
