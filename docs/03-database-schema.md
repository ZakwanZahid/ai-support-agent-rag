# Database Schema

## Overview

The initial schema supports a shared PostgreSQL database for multiple organizations. UUIDs identify every record, timestamps are timezone-aware, and PostgreSQL enforces the primary uniqueness and relationship rules.

## Tables

- `users`: global application identities. It holds the email, optional full name, future authentication password hash, active flag, and audit timestamps.
- `organizations`: customer workspaces identified by a unique slug.
- `organization_members`: maps users to organizations and records an `owner`, `admin`, or `member` role. This lets a user belong to more than one organization.
- `knowledge_bases`: named document collections within one organization. Names are unique per organization.
- `documents`: source records in a knowledge base. A document can originate from an upload, URL, or manual entry and tracks ingestion state and errors.
- `document_chunks`: ordered, searchable pieces of a document. It stores content, optional token count, optional JSONB chunk metadata, and a `vector(1536)` embedding.
- `conversations`: tenant-scoped chat threads. `user_id` is nullable to support future external customer conversations.
- `messages`: ordered message content for a conversation with `user`, `assistant`, or `system` role.
- `message_citations`: evidence links from a message to the exact document and chunk used, with an optional quote and retrieval score.
- `message_feedback`: one optional up/down rating and comment per message.

## Relationships

`users` and `organizations` are many-to-many through `organization_members`. An organization owns knowledge bases, documents, chunks, conversations, messages, citations, and feedback. A knowledge base contains documents; each document contains ordered chunks. Conversations contain messages, and messages can have citations plus one feedback record.

## Multi-tenancy

Every tenant-owned table includes `organization_id` directly, even when the organization could be reached through a parent record. The duplication is intentional: it makes tenant-scoped filters explicit and efficient, simplifies operational queries, and provides a straightforward foundation for future PostgreSQL Row Level Security (RLS). Application services must verify that related records belong to the same organization until RLS is introduced.

## Constraints and Indexes

- Unique indexes: `users.email`, `organizations.slug`.
- Composite uniqueness: membership per user/organization, knowledge-base name per organization, document chunk position per document, and one feedback record per message.
- Check constraints restrict membership roles, document source/status values, message roles, and feedback ratings.
- Foreign-key indexes exist on the tenant and parent lookup columns specified by the model. Cascade behavior removes dependent tenant data when its owning record is deleted; conversations keep a nullable user reference when a user is removed.

## Embeddings

The migration enables the `vector` extension and stores embeddings in `document_chunks.embedding` as `vector(1536)`. It creates an HNSW index using cosine distance (`vector_cosine_ops`) for future similarity retrieval. The 1536 dimension is an MVP assumption and should be changed only through a deliberate migration when the embedding model changes.

## Future Hardening

The next database hardening step is PostgreSQL RLS policies keyed to an application-set organization context. Future work should also add tenant-consistency enforcement across related foreign keys, retention policies, and ingestion observability as those workflows are implemented.
