import { apiClient } from "./client";
import type { ISODateString, UUID } from "./types";

export interface ConversationCreate {
  title?: string | null;
  knowledge_base_id?: UUID | null;
}

export interface CitationResponse {
  document_id: UUID;
  document_title: string;
  chunk_id: UUID;
  quote: string;
  score: number;
  chunk_metadata: Record<string, unknown> | null;
}

export type MessageRole = "user" | "assistant" | "system";

export interface MessageResponse {
  id: UUID;
  organization_id: UUID;
  conversation_id: UUID;
  role: MessageRole;
  content: string;
  created_at: ISODateString;
  citations: CitationResponse[];
}

export interface ConversationResponse {
  id: UUID;
  organization_id: UUID;
  user_id: UUID | null;
  knowledge_base_id: UUID | null;
  title: string | null;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface ConversationDetailResponse extends ConversationResponse {
  messages: MessageResponse[];
}

export interface ChatMessageRequest {
  question: string;
  knowledge_base_id: UUID;
  top_k?: number;
}

export interface ChatMessageResponse {
  conversation_id: UUID;
  user_message_id: UUID;
  assistant_message_id: UUID;
  answer: string;
  citations: CitationResponse[];
}

function conversationsPath(organizationId: UUID): string {
  return `/api/v1/organizations/${encodeURIComponent(
    organizationId,
  )}/conversations`;
}

export async function createConversation(
  organizationId: UUID,
  data: ConversationCreate,
): Promise<ConversationResponse> {
  const response = await apiClient.post<ConversationResponse>(
    conversationsPath(organizationId),
    data,
  );
  return response.data;
}

export async function listConversations(
  organizationId: UUID,
): Promise<ConversationResponse[]> {
  const response = await apiClient.get<ConversationResponse[]>(
    conversationsPath(organizationId),
  );
  return response.data;
}

export async function getConversation(
  organizationId: UUID,
  conversationId: UUID,
): Promise<ConversationDetailResponse> {
  const response = await apiClient.get<ConversationDetailResponse>(
    `${conversationsPath(organizationId)}/${encodeURIComponent(conversationId)}`,
  );
  return response.data;
}

export async function sendChatMessage(
  organizationId: UUID,
  conversationId: UUID,
  data: ChatMessageRequest,
): Promise<ChatMessageResponse> {
  const response = await apiClient.post<ChatMessageResponse>(
    `${conversationsPath(organizationId)}/${encodeURIComponent(
      conversationId,
    )}/messages`,
    data,
  );
  return response.data;
}

export const conversationsApi = {
  create: createConversation,
  list: listConversations,
  get: getConversation,
  sendMessage: sendChatMessage,
};
