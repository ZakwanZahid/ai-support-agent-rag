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

Auth, document ingestion, retrieval, AI generation, frontend, and workers are still pending.

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
