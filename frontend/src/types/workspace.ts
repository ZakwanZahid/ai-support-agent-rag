import type { ISODateString, UUID } from "./api";

/**
 * Called an "organization" by the API. Workspace is the product term; see
 * `src/lib/terminology.ts`.
 */
export interface Workspace {
  id: UUID;
  name: string;
  slug: string;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface WorkspaceDraft {
  name: string;
  /** Generated from the name by the backend when omitted. */
  slug?: string | null;
}
