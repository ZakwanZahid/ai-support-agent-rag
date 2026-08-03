import type { ISODateString, UUID } from "./api";

/**
 * Called a "knowledge base" by the API, surfaced as a "knowledge space" in the
 * product. See `src/lib/terminology.ts`.
 */
export interface KnowledgeSpace {
  id: UUID;
  organization_id: UUID;
  name: string;
  description: string | null;
  created_at: ISODateString;
  updated_at: ISODateString;
  /**
   * Aggregates supplied by the backend so list views do not have to fetch
   * every document to render a count. Optional because older responses and
   * the create endpoint may omit them.
   */
  document_count?: number;
  ready_document_count?: number;
}

export interface KnowledgeSpaceDraft {
  name: string;
  description?: string | null;
}
