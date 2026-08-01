# AI Support Agent RAG

Production-style AI support agent using Retrieval-Augmented Generation (RAG) for customer support workflows.

This repository now includes the initial FastAPI backend and a multi-tenant PostgreSQL/pgvector schema foundation.

## Project Goals

- Ingest organization support documents, FAQs, policies, and internal knowledge.
- Generate grounded AI answers with citations.
- Support multi-turn conversations and escalation to human agents.
- Provide an admin experience for managing knowledge sources and reviewing usage.
- Use a production-minded backend, worker, database, cache, and frontend architecture.

## Tech Stack

- Backend API: FastAPI
- Frontend: Next.js
- Database: PostgreSQL
- Vector Search: pgvector
- Cache and Broker: Redis
- Background Jobs: Celery
- Agent Orchestration: LangGraph
- Deployment: Docker and Docker Compose

## Planned Capabilities

- User authentication and organization workspaces
- Document upload and source management
- Text extraction, chunking, embedding, and indexing
- Semantic search over support knowledge
- RAG answer generation with source citations
- Conversation history
- Human escalation workflow
- Admin dashboard
- Background ingestion pipeline
- Observability, evaluation, and usage reporting

## Documentation

- [Architecture](docs/architecture.md)
- [Database Schema](docs/03-database-schema.md)
- [Authentication and Tenancy](docs/04-auth-tenancy.md)
- [Knowledge Bases and Document Uploads](docs/05-document-upload.md)
- [Document Ingestion](docs/07-document-ingestion.md)
- [API Design](docs/api-design.md)
- [System Design Decisions](docs/06-decisions.md)

## Repository Structure

```text
.
|-- README.md
|-- backend/
|   |-- app/
|   |-- alembic/
|   |-- alembic.ini
|   |-- requirements.txt
|   `-- README.md
`-- docs/
    |-- architecture.md
    |-- api-design.md
    |-- database-schema.md
    `-- system-design-decisions.md
```

## Current Status

This project has the first backend foundation in place:

- FastAPI app factory and `/health` endpoint
- Pydantic settings and environment configuration
- SQLAlchemy session setup
- SQLAlchemy models and initial Alembic migration for the multi-tenant schema
- PostgreSQL + pgvector Docker Compose setup
- JWT authentication, current-user resolution, and organization membership enforcement
- Organization-scoped knowledge-base APIs and pending document uploads
- Background text extraction and custom document chunking

Embeddings, retrieval, AI generation, frontend, and durable workers are still pending.

## Database Schema

The initial schema covers organizations and memberships, knowledge bases, documents and chunks, conversations and messages, citations, and message feedback. See [the database schema](docs/03-database-schema.md) for relationships, tenant isolation choices, indexes, and pgvector storage.

Start local PostgreSQL with pgvector:

```powershell
Copy-Item .env.example .env
docker compose up -d postgres
```

Run migrations from `backend/`:

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Authentication

Required authentication settings:

```env
JWT_SECRET_KEY=change-me-in-development
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
UPLOAD_DIR=storage/uploads
MAX_UPLOAD_SIZE_MB=10
AUTO_INGEST_ON_UPLOAD=true
CHUNK_SIZE=1200
CHUNK_OVERLAP=200
```

Available endpoints:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/organizations`
- `GET /api/v1/organizations`
- `GET /api/v1/organizations/{organization_id}`
- `POST /api/v1/organizations/{organization_id}/knowledge-bases`
- `GET /api/v1/organizations/{organization_id}/knowledge-bases`
- `GET /api/v1/organizations/{organization_id}/knowledge-bases/{knowledge_base_id}`
- `POST /api/v1/organizations/{organization_id}/knowledge-bases/{knowledge_base_id}/documents/upload`
- `GET /api/v1/organizations/{organization_id}/documents`
- `GET /api/v1/organizations/{organization_id}/documents/{document_id}`
- `POST /api/v1/organizations/{organization_id}/documents/{document_id}/ingest`

Register:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d '{"email":"user@example.com","password":"strongpassword","full_name":"User Name"}'
```

Login:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"user@example.com","password":"strongpassword"}'
```

Use the returned access token in protected requests:

```powershell
curl.exe http://127.0.0.1:8000/api/v1/auth/me `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Create a knowledge base:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/knowledge-bases `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"name":"Product Docs","description":"Product support documents"}'
```

Upload a document:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/knowledge-bases/KNOWLEDGE_BASE_ID/documents/upload `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -F "title=Getting Started" `
  -F "file=@C:\path\to\getting-started.txt;type=text/plain"
```

Uploads create a `pending` document. Background ingestion changes it to `processing`, then `processed` or `failed`. A later embedding phase will move processed documents to `indexed`. Files are stored under `storage/uploads/{organization_id}/{knowledge_base_id}/`.

Manually schedule ingestion:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/documents/DOCUMENT_ID/ingest" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Reprocess a completed document and replace its chunks:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/documents/DOCUMENT_ID/ingest?force=true" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Apply the status-constraint migration before testing ingestion:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Run tests from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Local Setup

Backend setup instructions are in [backend/README.md](backend/README.md).

## Demo

Demo instructions, screenshots, and deployment links will be added after the first usable implementation.

## Future Improvements

- Slack, WhatsApp, and website widget integrations
- RAG evaluation dashboard
- Billing and usage limits
- Role-based access control
- Advanced analytics for support teams
- Multi-region deployment strategy
