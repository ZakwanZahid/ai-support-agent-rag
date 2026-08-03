import { apiClient } from "./client";
import type { ISODateString, UUID } from "./types";

export interface OrganizationCreate {
  name: string;
  slug?: string | null;
}

export interface OrganizationResponse {
  id: UUID;
  name: string;
  slug: string;
  created_at: ISODateString;
  updated_at: ISODateString;
}

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

export const organizationsApi = {
  create: createOrganization,
  list: listOrganizations,
  get: getOrganization,
};
