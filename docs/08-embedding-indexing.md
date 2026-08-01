# Embedding Indexing and Semantic Search

## What Embeddings Are

An embedding is a numeric representation of text. Texts with related meaning tend to produce vectors that are close together, even when they use different words. This lets the application retrieve support passages by meaning instead of relying only on exact keyword matches.

An embedding model is not a GPT/chat model. The embedding model converts text into vectors; it does not write an answer. A chat model will later receive retrieved chunks and generate a cited response as part of the RAG workflow.

## Dimensions and pgvector

An embedding dimension is one numeric position in a vector. The MVP uses OpenAI `text-embedding-3-small` with 1,536 dimensions, so `document_chunks.embedding` is PostgreSQL `vector(1536)`. Every stored chunk vector and search-query vector must have exactly the same dimension.

`EMBEDDING_DIMENSIONS` must match both the provider output and the pgvector column. Moving to a model with another size, such as a 384-dimensional local Sentence Transformer, may require:

1. A database migration changing the vector column dimension.
2. Clearing incompatible old embeddings.
3. Re-indexing every chunk.

## Why Indexing Follows Ingestion

Ingestion performs deterministic file parsing and chunking first. Indexing then selects those chunks, calls the configured embedding provider in batches, and stores vectors. Separating the stages makes extraction failures independent from API-key, provider, rate-limit, and model failures.

Chunks intentionally have null embeddings after ingestion. Successful indexing fills every embedding and changes the document from `processed` to `indexed`. A failure changes the status to `failed` and records `error_message`.

Force re-indexing (`force=true`) generates new vectors for every chunk, including chunks that already have embeddings. Without force, only chunks with null embeddings are sent to the provider.

## Provider Abstraction

Indexing and search depend on the `EmbeddingProvider` interface, not the OpenAI SDK. OpenAI-specific client construction and API calls live only in `app/embeddings/openai_provider.py`; `factory.py` selects the configured adapter.

`text-embedding-3-small` is the MVP default because it is practical, fast, broadly supported, and matches the existing 1,536-dimensional schema. A Gemini, Cohere, Voyage, or local sentence-transformer adapter can later implement the same `embed_texts` and `embed_query` methods and be registered in the factory.

## Indexing Flow

The owner/admin indexing endpoint schedules a FastAPI background task:

```http
POST /api/v1/organizations/{organization_id}/documents/{document_id}/index
```

The task opens its own SQLAlchemy session, loads the tenant-scoped processed document, batches chunks according to `INDEX_BATCH_SIZE`, validates vector dimensions, stores embeddings, and marks the document indexed. Already indexed documents require `force=true`.

FastAPI `BackgroundTasks` is sufficient for MVP demonstrations but is not durable across process restarts. A production worker should add retries, rate-limit handling, and recovery for interrupted jobs.

## Semantic Search

Members search one organization-owned knowledge base:

```http
POST /api/v1/organizations/{organization_id}/knowledge-bases/{knowledge_base_id}/search
```

The provider embeds the query, and PostgreSQL orders non-null chunk embeddings with pgvector cosine distance. Lower distance means closer vectors. The API also returns `score = 1 - distance`, where a higher score is more similar.

Every query filters both `document_chunks.organization_id` and the joined document's `organization_id` and `knowledge_base_id`. This explicit tenant filtering prevents chunks from another organization or knowledge base from entering retrieval.

Search returns evidence candidates only. It does not call a chat model, generate an answer, choose citations, or implement the final RAG workflow. Keeping this endpoint separate makes retrieval quality and tenant isolation easier to debug before answer generation is added.

## Configuration

```env
OPENAI_API_KEY=
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
INDEX_BATCH_SIZE=50
```

The OpenAI API key is required for the current indexing and search provider and must never be committed.

## Swagger Verification

1. Register or log in.
2. Authorize Swagger with the Bearer token.
3. Create an organization.
4. Create a knowledge base.
5. Upload a supported document.
6. Ingest the document.
7. Confirm its status is `processed`.
8. Call the indexing endpoint.
9. Confirm its status is `indexed`.
10. Confirm `document_chunks.embedding` is not null in pgAdmin.
11. Submit a search query against the knowledge base.
12. Confirm relevant chunks are returned in distance order.

Automatic ingestion may already process the document after upload. Indexing remains an explicit action in this phase.

## pgAdmin Verification

```sql
SELECT id, title, status, error_message
FROM documents
ORDER BY created_at DESC;

SELECT
    document_id,
    chunk_index,
    embedding IS NOT NULL AS has_embedding,
    vector_dims(embedding) AS dimensions
FROM document_chunks
WHERE document_id = '<document-uuid>'
ORDER BY chunk_index;
```

All indexed chunks should report `has_embedding = true` and `dimensions = 1536`.

## Future Improvements

- Durable RQ or Celery workers
- Provider retries and rate-limit backoff
- Per-organization token and cost tracking
- A versioned embedding-model migration strategy
- Hybrid semantic and keyword search
- Cross-encoder reranking
- HNSW tuning or IVFFlat for different scale and recall requirements
- Cloud object storage and dedicated indexing workers
