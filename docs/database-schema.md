# Database Schema

## Overview

PostgreSQL will store relational application data and pgvector embeddings. The schema should support multi-tenant organizations, document ingestion, conversation history, citations, and human escalation.

This document is a planning skeleton. Table names, columns, constraints, and indexes will be finalized before migrations are created.

## Core Entities

### organizations

Represents a customer workspace or company.

Planned fields:

- `id`
- `name`
- `slug`
- `created_at`
- `updated_at`

### users

Represents application users.

Planned fields:

- `id`
- `organization_id`
- `email`
- `name`
- `role`
- `created_at`
- `updated_at`

### documents

Represents uploaded knowledge sources.

Planned fields:

- `id`
- `organization_id`
- `uploaded_by_user_id`
- `title`
- `source_type`
- `source_uri`
- `status`
- `metadata`
- `created_at`
- `updated_at`

### document_chunks

Represents searchable chunks extracted from documents.

Planned fields:

- `id`
- `organization_id`
- `document_id`
- `chunk_index`
- `content`
- `content_hash`
- `token_count`
- `embedding`
- `metadata`
- `created_at`

Notes:

- `embedding` should use the pgvector `vector` type.
- Chunk records should preserve enough metadata to produce useful citations.

### conversations

Represents a support conversation.

Planned fields:

- `id`
- `organization_id`
- `user_id`
- `status`
- `channel`
- `created_at`
- `updated_at`

### messages

Represents user, assistant, system, and human-agent messages.

Planned fields:

- `id`
- `organization_id`
- `conversation_id`
- `role`
- `content`
- `metadata`
- `created_at`

### message_citations

Links assistant answers to retrieved document chunks.

Planned fields:

- `id`
- `message_id`
- `document_id`
- `document_chunk_id`
- `rank`
- `score`
- `quote`
- `created_at`

### escalations

Represents conversations requiring human support.

Planned fields:

- `id`
- `organization_id`
- `conversation_id`
- `requested_by_message_id`
- `status`
- `reason`
- `assigned_to_user_id`
- `created_at`
- `updated_at`

### ingestion_jobs

Tracks asynchronous document processing.

Planned fields:

- `id`
- `organization_id`
- `document_id`
- `status`
- `error_message`
- `attempt_count`
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`

## Indexing Plan

Planned indexes:

- Organization foreign-key indexes for tenant-scoped queries.
- `documents(organization_id, status)`.
- `conversations(organization_id, user_id, updated_at)`.
- `messages(conversation_id, created_at)`.
- Vector similarity index on `document_chunks.embedding`.
- Unique or deduplication index on `document_chunks(document_id, content_hash)`.

## Data Integrity Rules

- Every tenant-owned record should include `organization_id`.
- Conversation and message records must not cross organization boundaries.
- Deleting documents should define whether chunks are hard deleted, soft deleted, or versioned.
- Ingestion jobs should be retryable without creating duplicate chunks.

## Open Questions

- Should documents and chunks be versioned?
- Should messages store model name, token usage, latency, and retrieval metadata directly or in a separate trace table?
- Should user-facing customers and internal admin users share one `users` table?
- What retention policy is required for conversations and uploaded documents?
