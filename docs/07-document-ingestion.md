# Document Ingestion Pipeline

## Why Upload and Ingestion Are Separate

Upload is responsible for durably storing a file and its metadata. Ingestion is responsible for reading that file, extracting text, splitting it into retrieval-ready chunks, and recording the result. Keeping these steps separate makes uploads responsive and lets failed extraction be retried without asking a user to upload the file again.

The upload endpoint can schedule ingestion automatically when `AUTO_INGEST_ON_UPLOAD=true`. Owners and admins can also schedule or retry it through:

```http
POST /api/v1/organizations/{organization_id}/documents/{document_id}/ingest
```

Completed documents require `force=true` to replace existing chunks.

## Document Lifecycle

- `pending`: file and metadata are stored but ingestion has not started.
- `processing`: extraction and chunk creation are running.
- `processed`: text chunks exist, but embeddings have not been generated.
- `indexed`: embeddings exist and the document is ready for retrieval.
- `failed`: ingestion failed; `error_message` contains a concise cause.

This phase moves documents through `pending`, `processing`, and `processed`, or to `failed`. The later embedding phase will move `processed` documents to `indexed`.

## Pipeline Steps

The background pipeline opens its own database session, reloads the tenant-scoped document, marks it as processing, resolves its local file, extracts text, replaces stale chunks on retries or forced runs, inserts `document_chunks`, and marks the document processed. Any extraction or persistence error rolls back chunk changes and records a failed status.

Each chunk stores:

- Tenant and document IDs
- A zero-based chunk index
- Text content
- An approximate token count based on character length
- JSON metadata with source, character offsets, and PDF page number when available
- A null embedding for the next indexing phase

## Supported Files

- UTF-8 plain text
- UTF-8 Markdown
- PDFs containing embedded text
- DOCX paragraphs

PDF extraction uses `pypdf` page by page. It does not perform OCR. A scanned or image-only PDF is marked failed with a message explaining that OCR is not supported yet.

## Chunking Strategy

The default chunk size is 1,200 characters with 200 characters of overlap. The custom splitter prefers paragraph, line, sentence, or whitespace boundaries in the latter half of a chunk. Character offsets describe each chunk within its source section.

Overlap preserves context around boundaries, which will help later retrieval when a useful answer spans the end of one chunk and the start of the next. The strategy is intentionally small and inspectable before introducing a framework splitter.

## Why Embeddings Remain Null

Extraction and indexing fail for different reasons and may use different infrastructure. Keeping `embedding` nullable lets this phase persist useful text chunks without choosing an embedding model or calling an external AI service. A later indexing pipeline can select processed chunks, generate vectors, and mark the document indexed.

## BackgroundTasks for the MVP

FastAPI `BackgroundTasks` keeps the first implementation operationally simple. Each task creates its own SQLAlchemy session rather than reusing the request session. This is suitable for local development and low-volume demonstrations, but tasks are not durable: a process restart can interrupt work and leave a document processing until retried.

## Configuration

```env
AUTO_INGEST_ON_UPLOAD=true
CHUNK_SIZE=1200
CHUNK_OVERLAP=200
```

`CHUNK_OVERLAP` must be smaller than `CHUNK_SIZE`.

## Manual Verification

After uploading or manually ingesting a document, inspect the row and its chunks:

```sql
SELECT id, title, status, error_message
FROM documents
ORDER BY created_at DESC;

SELECT document_id, chunk_index, token_count, chunk_metadata, content
FROM document_chunks
WHERE document_id = '<document-uuid>'
ORDER BY chunk_index;
```

`embedding` should be null in every chunk during this phase.

## Future Upgrade Path

- RQ with Redis for a small durable worker queue
- Celery for richer retry, scheduling, and workflow requirements
- A separate worker service with health checks and independent scaling
- S3, GCS, or another cloud object store
- OCR for scanned PDFs
- Structured task attempts, heartbeat detection, and automatic recovery for stuck processing documents
