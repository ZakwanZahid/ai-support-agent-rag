import { apiClient } from "./client";
import type { ISODateString, UUID } from "./types";

export type DocumentStatus =
  | "pending"
  | "processing"
  | "processed"
  | "indexed"
  | "failed";

export type DocumentSourceType = "upload" | "url" | "manual";

export interface DocumentResponse {
  id: UUID;
  organization_id: UUID;
  knowledge_base_id: UUID;
  title: string;
  source_type: DocumentSourceType;
  file_name: string | null;
  file_path: string | null;
  mime_type: string | null;
  status: DocumentStatus;
  error_message: string | null;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface UploadDocumentInput {
  file: File;
  title?: string | null;
}

export interface IngestionScheduledResponse {
  document_id: UUID;
  status: string;
  message: string;
}

export interface IndexingResponse {
  document_id: UUID;
  status: string;
  message: string;
}

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
