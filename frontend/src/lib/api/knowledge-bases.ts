import type { UUID } from "@/types/api";
import type { KnowledgeSpace, KnowledgeSpaceDraft } from "@/types/knowledge";

import { apiClient } from "./client";

export type KnowledgeBaseCreate = KnowledgeSpaceDraft;
export type KnowledgeBaseResponse = KnowledgeSpace;

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

/**
 * Permanently removes a knowledge space and every document in it.
 *
 * Chat threads that used it survive with no knowledge space attached: the
 * history stays readable, it just has nothing left to search.
 */
export async function deleteKnowledgeBase(
  organizationId: UUID,
  knowledgeBaseId: UUID,
): Promise<void> {
  await apiClient.delete(
    `${knowledgeBasesPath(organizationId)}/${encodeURIComponent(knowledgeBaseId)}`,
  );
}

export const knowledgeBasesApi = {
  create: createKnowledgeBase,
  list: listKnowledgeBases,
  get: getKnowledgeBase,
  remove: deleteKnowledgeBase,
};
