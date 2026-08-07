import type { Page, UUID } from "@/types/api";
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

/**
 * Messages older than a cursor, for "load earlier" in a long thread.
 *
 * Returned oldest-first, the order they are read in, so a caller prepends the
 * page as-is rather than reversing it.
 */
export async function listConversationMessages(
  organizationId: UUID,
  conversationId: UUID,
  options: { cursor?: string | null; limit?: number } = {},
): Promise<Page<MessageResponse>> {
  const response = await apiClient.get<Page<MessageResponse>>(
    `${conversationsPath(organizationId)}/${encodeURIComponent(
      conversationId,
    )}/messages`,
    {
      params: {
        ...(options.cursor ? { cursor: options.cursor } : {}),
        ...(options.limit ? { limit: options.limit } : {}),
      },
    },
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
