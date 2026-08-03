import type { UUID } from "@/types/api";
import type {
  AskRequest,
  AskResponse,
  ChatMessage,
  ChatThread,
  ChatThreadDetail,
  ChatThreadDraft,
  MessageRole,
  Source,
} from "@/types/conversation";

import { apiClient } from "./client";

export type { MessageRole };
export type ConversationCreate = ChatThreadDraft;
export type CitationResponse = Source;
export type MessageResponse = ChatMessage;
export type ConversationResponse = ChatThread;
export type ConversationDetailResponse = ChatThreadDetail;
export type ChatMessageRequest = AskRequest;
export type ChatMessageResponse = AskResponse;

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
