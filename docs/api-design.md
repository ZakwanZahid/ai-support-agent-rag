# API Design

## Overview

The FastAPI backend will expose HTTP APIs for authentication-aware support conversations, document management, ingestion status, and admin workflows.

This document defines the intended API surface at a planning level. Exact request and response schemas will be finalized before implementation.

## API Principles

- All tenant-scoped requests must enforce organization boundaries.
- Long-running work should return quickly and run through Celery.
- Responses should include stable IDs for follow-up operations.
- Error responses should use a consistent shape.
- API contracts should be documented with OpenAPI from FastAPI.

## Authentication

Authentication strategy is not finalized.

Possible options:

- Session-based auth for first-party frontend.
- JWT-based auth for API clients.
- Managed provider integration.

## Planned Endpoints

### Health

```http
GET /health
```

Purpose:

- Verify the API process is running.

```http
GET /ready
```

Purpose:

- Verify required dependencies are reachable, such as PostgreSQL and Redis.

### Organizations

```http
GET /organizations/current
```

Purpose:

- Return the current user workspace context.

### Documents

```http
GET /documents
POST /documents
GET /documents/{document_id}
DELETE /documents/{document_id}
```

Purpose:

- List, upload, inspect, and remove knowledge documents.

Expected behavior:

- Upload should create a document record and enqueue an ingestion job.
- Deletion behavior must match the database retention decision.

### Ingestion Jobs

```http
GET /ingestion-jobs
GET /ingestion-jobs/{job_id}
POST /documents/{document_id}/reindex
```

Purpose:

- Track and manage document processing.

### Conversations

```http
GET /conversations
POST /conversations
GET /conversations/{conversation_id}
GET /conversations/{conversation_id}/messages
```

Purpose:

- Create and review support conversations.

### Chat

```http
POST /conversations/{conversation_id}/messages
```

Purpose:

- Add a user message and generate an assistant response.

Planned response content:

- Assistant message
- Citations
- Retrieval metadata
- Escalation recommendation, if applicable

### Escalations

```http
GET /escalations
POST /conversations/{conversation_id}/escalations
PATCH /escalations/{escalation_id}
```

Purpose:

- Request, list, assign, and resolve human support escalations.

## Error Shape

Planned standard error response:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

## Pagination

List endpoints should use cursor-based pagination where result ordering changes frequently.

Candidate query parameters:

- `limit`
- `cursor`
- `sort`

## Streaming

Streaming chat responses are not yet decided.

Options:

- Start with regular request/response.
- Add Server-Sent Events for token streaming.
- Add WebSockets only if the product requires bidirectional real-time behavior.

## Open Questions

- Should public customer chat use separate unauthenticated session tokens?
- Should admin and customer-facing APIs be separated by route prefix?
- Is API versioning required from the first release?
- Should generated answers be synchronous or job-based for longer workflows?
