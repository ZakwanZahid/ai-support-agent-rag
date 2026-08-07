"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { getAPIErrorMessage } from "@/lib/api/client";
import {
  createConversation,
  getConversation,
  listConversationMessages,
  listConversations,
  sendChatMessage,
} from "@/lib/api/conversations";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import type { ChatMessage } from "@/types/conversation";

interface UseChatOptions {
  workspaceId: string | null;
  /** Knowledge space requested via the URL, e.g. from a document's "Ask about this". */
  requestedKnowledgeSpaceId?: string | null;
}

export function useChat({
  workspaceId,
  requestedKnowledgeSpaceId,
}: UseChatOptions) {
  const queryClient = useQueryClient();
  const enabled = Boolean(workspaceId);

  const [selectedSpaceId, setSelectedSpaceId] = useState<string | null>(null);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  /** Rendered immediately so the question appears before the answer returns. */
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);

  const knowledgeSpacesQuery = useQuery({
    queryKey: queryKeys.knowledgeBases(workspaceId),
    queryFn: () => listKnowledgeBases(workspaceId!),
    enabled,
  });

  const threadsQuery = useQuery({
    queryKey: queryKeys.conversations(workspaceId),
    queryFn: () => listConversations(workspaceId!),
    enabled,
  });

  const knowledgeSpaces = useMemo(
    () => knowledgeSpacesQuery.data ?? [],
    [knowledgeSpacesQuery.data],
  );

  /**
   * Only spaces with at least one ready document can answer anything. Offering
   * the others would produce confident "I don't know" replies.
   *
   * Read from the knowledge space's own `ready_document_count` rather than by
   * scanning every document. That aggregate has always been there (ADR-031);
   * pagination is what made using it necessary, since "every document" is no
   * longer something a single request returns.
   */
  const answerableSpaces = useMemo(
    () => knowledgeSpaces.filter((space) => (space.ready_document_count ?? 0) > 0),
    [knowledgeSpaces],
  );

  // Resolve the active space without storing it, so it stays valid when the
  // underlying lists change.
  const knowledgeSpaceId =
    answerableSpaces.find((space) => space.id === selectedSpaceId)?.id ??
    answerableSpaces.find((space) => space.id === requestedKnowledgeSpaceId)
      ?.id ??
    answerableSpaces[0]?.id ??
    null;

  const threads = useMemo(
    () =>
      (threadsQuery.data ?? []).filter(
        (thread) => thread.knowledge_base_id === knowledgeSpaceId,
      ),
    [knowledgeSpaceId, threadsQuery.data],
  );

  const threadId =
    threads.find((thread) => thread.id === activeThreadId)?.id ?? null;

  const threadQuery = useQuery({
    queryKey: queryKeys.conversation(workspaceId, threadId ?? ""),
    queryFn: () => getConversation(workspaceId!, threadId!),
    enabled: Boolean(workspaceId && threadId),
  });

  /**
   * Messages older than the page the thread opened with.
   *
   * Held separately from the thread query rather than merged into its cache:
   * asking a new question invalidates the thread, and rolling earlier pages
   * into that cache would throw them away on every message. Keyed by thread,
   * so switching threads starts empty.
   */
  const [earlier, setEarlier] = useState<{
    threadId: string | null;
    messages: ChatMessage[];
    cursor: string | null;
  }>({ threadId: null, messages: [], cursor: null });

  const earlierForThread = earlier.threadId === threadId ? earlier : null;
  const olderCursor =
    earlierForThread?.cursor ?? threadQuery.data?.next_message_cursor ?? null;

  const loadEarlierMutation = useMutation({
    mutationFn: () =>
      listConversationMessages(workspaceId!, threadId!, { cursor: olderCursor }),
    onSuccess: (page) => {
      setEarlier((current) => {
        const existing = current.threadId === threadId ? current.messages : [];
        return {
          threadId,
          messages: [...page.items, ...existing],
          cursor: page.has_more ? page.next_cursor : null,
        };
      });
    },
    onError: (error) => toast.error(getAPIErrorMessage(error)),
  });

  const sendMutation = useMutation({
    mutationFn: async (question: string) => {
      // A thread is created lazily on the first question, so an abandoned
      // "new chat" never leaves an empty thread behind.
      let targetThreadId = threadId;
      if (!targetThreadId) {
        const created = await createConversation(workspaceId!, {
          title: question.slice(0, 80),
          knowledge_base_id: knowledgeSpaceId,
        });
        targetThreadId = created.id;
        setActiveThreadId(created.id);
      }

      return sendChatMessage(workspaceId!, targetThreadId, {
        question,
        knowledge_base_id: knowledgeSpaceId!,
      });
    },
    onMutate: (question: string) => setPendingQuestion(question),
    onSuccess: async (response) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.conversation(
            workspaceId,
            response.conversation_id,
          ),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.conversations(workspaceId),
        }),
      ]);
    },
    onError: (error) => toast.error(getAPIErrorMessage(error)),
    onSettled: () => setPendingQuestion(null),
  });

  const startNewThread = useCallback(() => {
    setActiveThreadId(null);
    setPendingQuestion(null);
  }, []);

  const selectKnowledgeSpace = useCallback((spaceId: string) => {
    setSelectedSpaceId(spaceId);
    // Threads belong to one space, so the open thread no longer applies.
    setActiveThreadId(null);
  }, []);

  const messages = useMemo(
    () => [
      ...(earlierForThread?.messages ?? []),
      ...(threadQuery.data?.messages ?? []),
    ],
    [earlierForThread, threadQuery.data],
  );
  const hasEarlierMessages = Boolean(
    olderCursor &&
      (earlierForThread ? earlierForThread.cursor : threadQuery.data?.has_more_messages),
  );
  const latestAnswer = [...messages]
    .reverse()
    .find((message) => message.role === "assistant");

  return {
    knowledgeSpaces,
    answerableSpaces,
    knowledgeSpaceId,
    activeKnowledgeSpace:
      answerableSpaces.find((space) => space.id === knowledgeSpaceId) ?? null,
    selectKnowledgeSpace,

    threads,
    threadId,
    selectThread: setActiveThreadId,
    startNewThread,

    messages,
    hasEarlierMessages,
    loadEarlierMessages: () => loadEarlierMutation.mutate(),
    isLoadingEarlierMessages: loadEarlierMutation.isPending,
    latestAnswer,
    pendingQuestion,

    ask: (question: string) => sendMutation.mutate(question),
    isSending: sendMutation.isPending,

    isLoading: knowledgeSpacesQuery.isPending || threadsQuery.isPending,
    isThreadLoading: Boolean(threadId) && threadQuery.isPending,
    isError: knowledgeSpacesQuery.isError || threadsQuery.isError,
    refetch: () => {
      void knowledgeSpacesQuery.refetch();
      void threadsQuery.refetch();
    },
  };
}
