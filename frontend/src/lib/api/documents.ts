import type { UUID } from "@/types/api";
import type {
  DocumentPage,
  DocumentSourceType,
  DocumentStatus,
  DocumentTaskAccepted,
  DocumentUpload,
  KnowledgeDocument,
} from "@/types/document";

import { apiClient } from "./client";

export type { DocumentSourceType, DocumentStatus };
export type DocumentResponse = KnowledgeDocument;
export type UploadDocumentInput = DocumentUpload;
export type IngestionScheduledResponse = DocumentTaskAccepted;
export type IndexingResponse = DocumentTaskAccepted;

function organizationPath(organizationId: UUID): string {
  return `/api/v1/organizations/${encodeURIComponent(organizationId)}`;
}

export interface ListDocumentsQuery {
  knowledgeBaseId?: UUID | null;
  /** Matched against the title, in the database rather than the browser. */
  search?: string | null;
  /** Raw API statuses. `terminology.ts` maps the product's filters onto these. */
  statuses?: readonly DocumentStatus[];
  limit?: number;
  /** Opaque cursor from a previous page. Never built by hand. */
  cursor?: string | null;
}

export async function listDocuments(
  organizationId: UUID,
  query: ListDocumentsQuery = {},
): Promise<DocumentPage> {
  const params = new URLSearchParams();
  if (query.knowledgeBaseId) {
    params.set("knowledge_base_id", query.knowledgeBaseId);
  }
  if (query.search?.trim()) {
    params.set("q", query.search.trim());
  }
  // Repeated rather than comma-joined: one product filter can cover several
  // API statuses, and FastAPI reads repeats into a list.
  for (const status of query.statuses ?? []) {
    params.append("status", status);
  }
  if (query.limit) {
    params.set("limit", String(query.limit));
  }
  if (query.cursor) {
    params.set("cursor", query.cursor);
  }

  const response = await apiClient.get<DocumentPage>(
    `${organizationPath(organizationId)}/documents`,
    { params },
  );
  return response.data;
}

export async function getDocument(
  organizationId: UUID,
  documentId: UUID,
): Promise<DocumentResponse> {
  const response = await apiClient.get<DocumentResponse>(
    `${organizationPath(organizationId)}/documents/${encodeURIComponent(documentId)}`,
  );
  return response.data;
}

export async function uploadDocument(
  organizationId: UUID,
  knowledgeBaseId: UUID,
  input: UploadDocumentInput,
): Promise<DocumentResponse> {
  const formData = new FormData();
  formData.append("file", input.file);
  if (input.title?.trim()) {
    formData.append("title", input.title.trim());
  }

  const response = await apiClient.post<DocumentResponse>(
    `${organizationPath(organizationId)}/knowledge-bases/${encodeURIComponent(
      knowledgeBaseId,
    )}/documents/upload`,
    formData,
  );
  return response.data;
}

export async function ingestDocument(
  organizationId: UUID,
  documentId: UUID,
  force = false,
): Promise<IngestionScheduledResponse> {
  const response = await apiClient.post<IngestionScheduledResponse>(
    `${organizationPath(organizationId)}/documents/${encodeURIComponent(
      documentId,
    )}/ingest`,
    undefined,
    { params: force ? { force: true } : undefined },
  );
  return response.data;
}

/**
 * Take a document from uploaded to ready in one call.
 *
 * The backend chains extraction and indexing, so the UI exposes a single
 * "Prepare for chat" action and polls the document until it reports ready or
 * failed. `ingestDocument` and `indexDocument` remain for the individual
 * steps but are not part of the normal user flow.
 */
export async function prepareDocument(
  organizationId: UUID,
  documentId: UUID,
  force = false,
): Promise<DocumentTaskAccepted> {
  const response = await apiClient.post<DocumentTaskAccepted>(
    `${organizationPath(organizationId)}/documents/${encodeURIComponent(
      documentId,
    )}/prepare`,
    undefined,
    { params: force ? { force: true } : undefined },
  );
  return response.data;
}

export async function indexDocument(
  organizationId: UUID,
  documentId: UUID,
  force = false,
): Promise<IndexingResponse> {
  const response = await apiClient.post<IndexingResponse>(
    `${organizationPath(organizationId)}/documents/${encodeURIComponent(
      documentId,
    )}/index`,
    undefined,
    { params: force ? { force: true } : undefined },
  );
  return response.data;
}

/**
 * Permanently removes a document, its extracted passages, and its file.
 *
 * Rejected with 409 while the document is being prepared: deleting the row
 * would not call back an embedding request already in flight, so the API
 * refuses rather than accepting a delete that cancels nothing.
 */
export async function deleteDocument(
  organizationId: UUID,
  documentId: UUID,
): Promise<void> {
  await apiClient.delete(
    `${organizationPath(organizationId)}/documents/${encodeURIComponent(documentId)}`,
  );
}

export const documentsApi = {
  list: listDocuments,
  get: getDocument,
  upload: uploadDocument,
  prepare: prepareDocument,
  ingest: ingestDocument,
  index: indexDocument,
  remove: deleteDocument,
};
