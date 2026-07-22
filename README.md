# AI Support Agent RAG

Production-style AI support agent using Retrieval-Augmented Generation (RAG) for customer support workflows.

This repository is intentionally documentation-first at this stage. Application code will be added after the architecture, data model, API boundaries, and system decisions are clear.

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
- [Database Schema](docs/database-schema.md)
- [API Design](docs/api-design.md)
- [System Design Decisions](docs/system-design-decisions.md)

## Repository Structure

```text
.
├── README.md
└── docs/
    ├── architecture.md
    ├── api-design.md
    ├── database-schema.md
    └── system-design-decisions.md
```

## Current Status

This project is in the planning and documentation stage.

No application code has been added yet.

## Local Setup

Setup instructions will be added once the backend, frontend, worker, and infrastructure folders are introduced.

## Demo

Demo instructions, screenshots, and deployment links will be added after the first usable implementation.

## Future Improvements

- Slack, WhatsApp, and website widget integrations
- RAG evaluation dashboard
- Billing and usage limits
- Role-based access control
- Advanced analytics for support teams
- Multi-region deployment strategy
