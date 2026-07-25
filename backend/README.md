# Backend

FastAPI backend for AI Support Agent RAG.

## Stack

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic Settings
- PostgreSQL

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

## Health Check

```http
GET /health
```

Expected response:

```json
{
  "status": "ok",
  "service": "AI Support Agent RAG",
  "environment": "local"
}
```

## Migrations

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Start the local pgvector database from the repository root before migrating:

```powershell
docker compose up -d postgres
```

The first migration creates the multi-tenant application tables, enables PostgreSQL `vector`, and creates an HNSW cosine-similarity index for document chunk embeddings.

