import { apiClient } from "./client";
import type { ISODateString, UUID } from "./types";

export interface KnowledgeBaseCreate {
  name: string;
  description?: string | null;
}

export interface KnowledgeBaseResponse {
  id: UUID;
  organization_id: UUID;
  name: string;
  description: string | null;
  created_at: ISODateString;
  updated_at: ISODateString;
}

function knowledgeBasesPath(organizationId: UUID): string {
  return `/api/v1/organizations/${encodeURIComponent(
    organizationId,
  )}/knowledge-bases`;
}

export async function createKnowledgeBase(
  organizationId: UUID,
  data: KnowledgeBaseCreate,
): Promise<KnowledgeBaseResponse> {
  const response = await apiClient.post<KnowledgeBaseResponse>(
    knowledgeBasesPath(organizationId),
    data,
  );
  return response.data;
}

export async function listKnowledgeBases(
  organizationId: UUID,
): Promise<KnowledgeBaseResponse[]> {
  const response = await apiClient.get<KnowledgeBaseResponse[]>(
    knowledgeBasesPath(organizationId),
  );
  return response.data;
}

export async function getKnowledgeBase(
  organizationId: UUID,
  knowledgeBaseId: UUID,
): Promise<KnowledgeBaseResponse> {
  const response = await apiClient.get<KnowledgeBaseResponse>(
    `${knowledgeBasesPath(organizationId)}/${encodeURIComponent(knowledgeBaseId)}`,
  );
  return response.data;
}

export const knowledgeBasesApi = {
  create: createKnowledgeBase,
  list: listKnowledgeBases,
  get: getKnowledgeBase,
};
