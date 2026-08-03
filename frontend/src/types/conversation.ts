import type { ISODateString, UUID } from "./api";

export type MessageRole = "user" | "assistant" | "system";

/**
 * A retrieved passage backing an answer. Called a "citation" by the API and
 * shown as a "source" in the product.
 */
export interface Source {
  document_id: UUID;
  document_title: string;
  chunk_id: UUID;
  quote: string;
  /** Cosine similarity. Not shown by default: a raw number means little to users. */
  score: number;
  chunk_metadata: Record<string, unknown> | null;
}

export interface ChatMessage {
  id: UUID;
  organization_id: UUID;
  conversation_id: UUID;
  role: MessageRole;
  content: string;
  created_at: ISODateString;
  citations: Source[];
}

/** Called a "conversation" by the API, shown as a "chat thread". */
export interface ChatThread {
  id: UUID;
  organization_id: UUID;
  user_id: UUID | null;
  knowledge_base_id: UUID | null;
  title: string | null;
  created_at: ISODateString;
  updated_at: ISODateString;
  /** Aggregates supplied by the backend for list rendering. */
  message_count?: number;
  last_message_preview?: string | null;
}

export interface ChatThreadDetail extends ChatThread {
  messages: ChatMessage[];
}

export interface ChatThreadDraft {
  title?: string | null;
  knowledge_base_id?: UUID | null;
}

export interface AskRequest {
  question: string;
  knowledge_base_id: UUID;
  top_k?: number;
}

export interface AskResponse {
  conversation_id: UUID;
  user_message_id: UUID;
  assistant_message_id: UUID;
  answer: string;
  citations: Source[];
}
