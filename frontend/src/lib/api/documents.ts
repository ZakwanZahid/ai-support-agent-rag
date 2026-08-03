import type { UUID } from "@/types/api";
import type {
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

export async function listDocuments(
  organizationId: UUID,
  knowledgeBaseId?: UUID | null,
): Promise<DocumentResponse[]> {
  const response = await apiClient.get<DocumentResponse[]>(
    `${organizationPath(organizationId)}/documents`,
    {
      params: knowledgeBaseId ? { knowledge_base_id: knowledgeBaseId } : undefined,
    },
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

export const documentsApi = {
  list: listDocuments,
  get: getDocument,
  upload: uploadDocument,
  ingest: ingestDocument,
  index: indexDocument,
};
