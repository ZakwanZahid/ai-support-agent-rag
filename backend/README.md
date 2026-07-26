# Backend

FastAPI backend for AI Support Agent RAG.

## Stack

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic Settings
- PostgreSQL

## Project Structure

```
backend/
├── __main__.py           # Entry point for running the app as a module
├── requirements.txt      # Python dependencies
├── alembic/             # Database migrations
├── app/
│   ├── main.py          # FastAPI app factory
│   ├── core/            # Core configuration and utilities
│   │   └── config.py    # Settings (environment variables)
│   ├── api/             # API routers
│   │   ├── router.py    # Main API router
│   │   └── v1/          # API v1 endpoints
│   │       ├── router.py
│   │       └── routes/
│   │           └── health.py  # Health check endpoint
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic schemas for request/response validation
│   ├── services/        # Business logic services
│   └── db/              # Database utilities
│       ├── base.py      # Base model
│       └── session.py   # Database session management
```

## Local Setup

1. Create a virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:
```powershell
pip install -r requirements.txt
```

3. Set up environment variables (`.env` file is already configured):
```powershell
# If needed, update backend/.env with your local settings
```

4. Run the backend from the repository root with one of these methods:

**Option A:  Using the module entry point**
```powershell
python backend/__main__.py
```

**Option B: Using uvicorn from backend directory**
```powershell
cd backend
python -m uvicorn app.main:app --reload
```

**Option C: Using Docker Compose**
```powershell
docker compose up backend
```

The server will start on `http://localhost:8000`

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

