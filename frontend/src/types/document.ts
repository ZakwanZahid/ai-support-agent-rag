import type { DocumentStatus } from "@/lib/terminology";

import type { ISODateString, Page, UUID } from "./api";

export type { DocumentStatus };

export type DocumentSourceType = "upload" | "url" | "manual";

export interface KnowledgeDocument {
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

/**
 * A page of documents, plus the numbers shown on the filter controls.
 *
 * The counts describe the current search but ignore the selected status, so
 * every filter chip can show how many documents it would reveal.
 */
export interface DocumentPage extends Page<KnowledgeDocument> {
  status_counts: Partial<Record<DocumentStatus, number>>;
}

export interface DocumentUpload {
  file: File;
  title?: string | null;
}

/** Response from the endpoints that schedule background work on a document. */
export interface DocumentTaskAccepted {
  document_id: UUID;
  status: string;
  message: string;
}
