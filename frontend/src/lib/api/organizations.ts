import type { UUID } from "@/types/api";
import type { Workspace, WorkspaceDraft } from "@/types/workspace";

import { apiClient } from "./client";

export type OrganizationCreate = WorkspaceDraft;
export type OrganizationResponse = Workspace;

export async function createOrganization(
  data: OrganizationCreate,
): Promise<OrganizationResponse> {
  const response = await apiClient.post<OrganizationResponse>(
    "/api/v1/organizations",
    data,
  );
  return response.data;
}

export async function listOrganizations(): Promise<OrganizationResponse[]> {
  const response = await apiClient.get<OrganizationResponse[]>("/api/v1/organizations");
  return response.data;
}

export async function getOrganization(
  organizationId: UUID,
): Promise<OrganizationResponse> {
  const response = await apiClient.get<OrganizationResponse>(
    `/api/v1/organizations/${encodeURIComponent(organizationId)}`,
  );
  return response.data;
}

/** Renames a workspace. The slug is fixed and cannot be changed. */
export async function updateOrganization(
  organizationId: UUID,
  data: { name: string },
): Promise<Workspace> {
  const response = await apiClient.patch<Workspace>(
    `/api/v1/organizations/${encodeURIComponent(organizationId)}`,
    data,
  );
  return response.data;
}

/** Permanently removes a workspace and everything in it. Owners only. */
export async function deleteOrganization(organizationId: UUID): Promise<void> {
  await apiClient.delete(
    `/api/v1/organizations/${encodeURIComponent(organizationId)}`,
  );
}

export const organizationsApi = {
  create: createOrganization,
  list: listOrganizations,
  get: getOrganization,
  update: updateOrganization,
  remove: deleteOrganization,
};
