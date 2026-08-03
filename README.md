# AI Support Agent RAG

Production-style, multi-tenant AI support workspace using Retrieval-Augmented Generation (RAG) for customer support workflows.

The repository includes a FastAPI and PostgreSQL/pgvector backend plus a responsive Next.js dashboard for the full knowledge-base-to-cited-answer flow.

## Project Goals

- Ingest organization support documents, FAQs, policies, and internal knowledge.
- Generate grounded AI answers with citations.
- Support multi-turn conversations and escalation to human agents.
- Provide an admin experience for managing knowledge sources and reviewing usage.
- Use a production-minded backend, worker, database, cache, and frontend architecture.

## Tech Stack

- Backend API: FastAPI and SQLAlchemy
- Frontend: Next.js App Router, React, and TypeScript
- UI: Tailwind CSS and reusable shadcn/ui-style components
- Frontend data and forms: TanStack Query, Axios, React Hook Form, and Zod
- Database: PostgreSQL
- Vector Search: pgvector
- Local infrastructure: Docker and Docker Compose

Redis, durable workers, and LangGraph orchestration are future milestones rather than current runtime dependencies.

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
- [Embedding Indexing and Search](docs/08-embedding-indexing.md)
- [RAG Chat with Citations](docs/09-rag-chat.md)
- [Frontend v1](docs/10-frontend-v1.md)
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
|-- frontend/
|   |-- app/
|   |-- src/
|   |-- .env.example
|   |-- package.json
|   `-- README.md
`-- docs/
    |-- 06-decisions.md
    |-- 09-rag-chat.md
    `-- 10-frontend-v1.md
```

## Current Status

The current local product flow includes:

- FastAPI app factory and `/health` endpoint
- Pydantic settings and environment configuration
- SQLAlchemy session setup
- SQLAlchemy models and initial Alembic migration for the multi-tenant schema
- PostgreSQL + pgvector Docker Compose setup
- JWT authentication, current-user resolution, and organization membership enforcement
- Organization-scoped knowledge-base APIs and pending document uploads
- Background text extraction and custom document chunking
- OpenAI embedding indexing through a provider abstraction
- Tenant-scoped pgvector semantic search
- Grounded RAG chat with persisted conversations, messages, and citations
- OpenAI chat-model adapter behind a provider abstraction
- Next.js authentication, dashboard, knowledge-base, document, chat, and saved-conversation pages
- Responsive desktop and mobile application navigation
- Typed API modules with bearer authentication and consistent error handling
- Loading, empty, disabled, success, and error states backed by real API data

Streaming, LangGraph orchestration, escalation, billing, analytics, team invitations, and durable workers are not part of Frontend v1.

## Database Schema

The initial schema covers organizations and memberships, knowledge bases, documents and chunks, conversations and messages, citations, and message feedback. See [the database schema](docs/03-database-schema.md) for relationships, tenant isolation choices, indexes, and pgvector storage.

Start local PostgreSQL with pgvector:

```powershell
Copy-Item .env.example .env
docker compose up -d postgres
```

Run migrations from `backend/`:

```powershell
Copy-Item ..\.env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Backend API and Configuration

Required local backend settings:

```env
FRONTEND_ORIGIN=http://localhost:3000
JWT_SECRET_KEY=change-me-in-development
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
UPLOAD_DIR=storage/uploads
MAX_UPLOAD_SIZE_MB=10
AUTO_INGEST_ON_UPLOAD=true
CHUNK_SIZE=1200
CHUNK_OVERLAP=200
OPENAI_API_KEY=
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
INDEX_BATCH_SIZE=50
CHAT_PROVIDER=openai
CHAT_MODEL=gpt-4o-mini
CHAT_TEMPERATURE=0.2
RAG_TOP_K=5
RAG_MAX_CONTEXT_CHARS=12000
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
- `POST /api/v1/organizations/{organization_id}/documents/{document_id}/index`
- `POST /api/v1/organizations/{organization_id}/knowledge-bases/{knowledge_base_id}/search`
- `POST /api/v1/organizations/{organization_id}/conversations`
- `GET /api/v1/organizations/{organization_id}/conversations`
- `GET /api/v1/organizations/{organization_id}/conversations/{conversation_id}`
- `POST /api/v1/organizations/{organization_id}/conversations/{conversation_id}/messages`

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

Set a valid `OPENAI_API_KEY` in `backend/.env`, then index a processed document:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/documents/DOCUMENT_ID/index" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Search the indexed knowledge base:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/knowledge-bases/KNOWLEDGE_BASE_ID/search" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"query":"What is the refund policy?","top_k":5}'
```

Create a conversation:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/conversations" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"title":"Refund policy question","knowledge_base_id":"KNOWLEDGE_BASE_ID"}'
```

Send a grounded RAG question:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/conversations/CONVERSATION_ID/messages" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"question":"What is the refund policy?","knowledge_base_id":"KNOWLEDGE_BASE_ID","top_k":5}'
```

The response contains the stored user and assistant message IDs, the grounded answer, and application-generated citation metadata:

```json
{
  "conversation_id": "...",
  "user_message_id": "...",
  "assistant_message_id": "...",
  "answer": "Customers can request a refund within 14 days of purchase.",
  "citations": [
    {
      "document_id": "...",
      "document_title": "sample-faq",
      "chunk_id": "...",
      "quote": "Customers can request a refund within 14 days of purchase.",
      "score": 0.89,
      "chunk_metadata": {}
    }
  ]
}
```

## Complete Manual RAG Test Flow

Use Swagger at `http://127.0.0.1:8000/docs`:

1. Register a user and log in.
2. Authorize Swagger with `Bearer <access_token>`.
3. Create an organization.
4. Create a knowledge base.
5. Upload a sample support document.
6. Ingest the document.
7. Index the document.
8. Create a conversation associated with the knowledge base.
9. Send a question to the conversation message endpoint.
10. Confirm the answer uses only uploaded facts and returns source citations.
11. Get the conversation and confirm both messages and assistant citations are present.

Verify persistence in pgAdmin:

```sql
SELECT * FROM conversations WHERE id = '<conversation_id>';
SELECT * FROM messages WHERE conversation_id = '<conversation_id>' ORDER BY created_at, id;
SELECT mc.*
FROM message_citations AS mc
JOIN messages AS m ON m.id = mc.message_id
WHERE m.conversation_id = '<conversation_id>';
```

See [RAG Chat with Citations](docs/09-rag-chat.md) for the full flow, tenant-isolation rules, error behavior, and 14-step Swagger checklist.

The lifecycle is `pending → processing → processed → indexed`, with `failed` used when ingestion or indexing cannot complete. OpenAI credentials are required for indexing and search in the current MVP.

Run tests from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Frontend Setup

Frontend requirements:

- Node.js 22.13 or newer
- The FastAPI backend available at the configured API base URL

Install and configure from the repository root:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
```

The frontend environment contains only the public API origin:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Do not put an OpenAI key or another server secret in a `NEXT_PUBLIC_*` variable. Browser code can read all variables with that prefix.

Frontend v1 stores the API JWT in `localStorage`. This is acceptable for the local MVP; a production authentication milestone should move it to a server-managed `Secure`, `HttpOnly` cookie with appropriate CSRF protection.

Useful frontend checks:

```powershell
npm run typecheck
npm run lint
npm run build
```

Start local development with:

```powershell
npm run dev
```

The dashboard is then available at `http://localhost:3000`. See [frontend/README.md](frontend/README.md) for project structure and troubleshooting.

## Run Backend and Frontend Together

From the repository root, prepare the backend:

```powershell
Copy-Item .env.example .env
Copy-Item .env.example backend/.env
docker compose up -d postgres
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Set a valid `OPENAI_API_KEY` in the backend environment before indexing or RAG chat. Never commit the populated `.env`.

Run the API in one terminal:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Run the frontend in a second terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Use:

- Frontend: `http://localhost:3000`
- FastAPI OpenAPI/Swagger: `http://127.0.0.1:8000/docs`
- FastAPI health check: `http://127.0.0.1:8000/health`

If browser API requests are blocked, verify that the frontend base URL matches the running API and that backend `FRONTEND_ORIGIN` is exactly `http://localhost:3000`. The FastAPI CORS middleware uses that origin only in local or development environments; it does not open the API to `*`.

## Manual Product Demo

1. Register through the frontend and log in.
2. Create or select an organization.
3. Create a knowledge base for a small set of support policies.
4. Upload a text document through the knowledge-base detail page.
5. Ingest the document, then index it.
6. Open Chat and select that knowledge base.
7. Start a conversation and ask a question answered by the document.
8. Confirm the assistant answer is grounded and its citation shows the source title and supporting quote.
9. Open the saved conversation and confirm the messages and citations reload.
10. Ask an unrelated question and confirm the app shows the safe no-context answer without invented sources.
11. Log out and confirm the protected dashboard is no longer available.

The backend-only Swagger and pgAdmin verification flow remains documented in [RAG Chat with Citations](docs/09-rag-chat.md).

## Screenshots

Screenshot slots are intentionally left explicit until final demo data and deployment branding are ready:

| View | Placeholder |
| --- | --- |
| Authentication | `docs/screenshots/frontend-auth.png` |
| Dashboard overview | `docs/screenshots/frontend-dashboard.png` |
| Knowledge-base documents | `docs/screenshots/frontend-knowledge-base.png` |
| Grounded chat with citations | `docs/screenshots/frontend-chat-citations.png` |
| Mobile chat | `docs/screenshots/frontend-mobile-chat.png` |

These paths are placeholders, not claims that screenshots or a public deployment are already available.

## Local Setup References

- [Backend setup](backend/README.md)
- [Frontend setup](frontend/README.md)
- [Frontend v1 architecture and manual testing](docs/10-frontend-v1.md)

## Future Improvements

- Slack, WhatsApp, and website widget integrations
- RAG evaluation dashboard
- Billing and usage limits
- Role-based access control
- Advanced analytics for support teams
- Multi-region deployment strategy
