# Knowledge Bases and Document Uploads

## Knowledge Bases

A knowledge base is an organization-owned collection of related support material, such as product documentation, policies, or internal procedures. Names are unique within one organization. Organization members can list and view knowledge bases, while only owners and admins can create them.

Every knowledge-base query includes `organization_id`. Looking up a knowledge base by its ID alone is not sufficient because every tenant boundary must remain explicit.

## Upload Flow

Owners and admins upload a file using multipart form data. The API validates the knowledge base against the organization, checks the declared MIME type and matching extension, enforces the configured size limit, and streams the file to local storage. It generates a UUID-based server filename and keeps the safe original basename in the database.

Files are stored under:

```text
storage/uploads/{organization_id}/{knowledge_base_id}/{generated_filename}
```

The default maximum upload size is 10 MB. Supported types are:

- PDF: `application/pdf` and `.pdf`
- Plain text: `text/plain` and `.txt`
- Markdown: `text/markdown` and `.md` or `.markdown`
- Word: `application/vnd.openxmlformats-officedocument.wordprocessingml.document` and `.docx`

Local storage is an MVP decision that keeps development and portfolio demonstrations self-contained. Stored paths are relative to the repository when `UPLOAD_DIR` is relative, making local data easier to inspect.

## Document Lifecycle

Uploading creates only the file and its document metadata row:

- `pending`: uploaded and waiting for ingestion
- `processing`: text extraction and chunk creation are running
- `processed`: text chunks exist and are waiting for embeddings
- `indexed`: chunks and embeddings are ready for retrieval
- `failed`: ingestion stopped and `error_message` explains why

Upload is intentionally separate from ingestion. HTTP requests finish after durable file and metadata storage, and the current MVP schedules extraction and chunking with FastAPI background tasks. Embedding remains a later phase.

## Authorization and Isolation

All document queries are scoped directly by `organization_id`. Members may list and view metadata. Only owners and admins may upload. A knowledge base or document from another organization is never returned through a mismatched organization path, and non-members receive the same `404` used for an unknown organization.

## Future Improvements

- S3, Google Cloud Storage, or another object store
- Background ingestion workers with retries
- File signature inspection instead of relying only on MIME type and extension
- Malware and virus scanning
- Checksums, deduplication, versioning, and retention policies
- Signed upload and download URLs
