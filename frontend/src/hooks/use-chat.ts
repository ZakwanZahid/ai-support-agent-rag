"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { getAPIErrorMessage } from "@/lib/api/client";
import {
  createConversation,
  getConversation,
  listConversations,
  sendChatMessage,
} from "@/lib/api/conversations";
import { listDocuments } from "@/lib/api/documents";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import { isDocumentReady } from "@/lib/terminology";

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

  const documentsQuery = useQuery({
    queryKey: queryKeys.documents(workspaceId),
    queryFn: () => listDocuments(workspaceId!),
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
   */
  const answerableSpaces = useMemo(() => {
    const readyBySpace = new Set(
      (documentsQuery.data ?? [])
        .filter((document) => isDocumentReady(document.status))
        .map((document) => document.knowledge_base_id),
    );
    return knowledgeSpaces.filter((space) => readyBySpace.has(space.id));
  }, [documentsQuery.data, knowledgeSpaces]);

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

  const messages = threadQuery.data?.messages ?? [];
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
    latestAnswer,
    pendingQuestion,

    ask: (question: string) => sendMutation.mutate(question),
    isSending: sendMutation.isPending,

    isLoading:
      knowledgeSpacesQuery.isPending ||
      documentsQuery.isPending ||
      threadsQuery.isPending,
    isThreadLoading: Boolean(threadId) && threadQuery.isPending,
    isError:
      knowledgeSpacesQuery.isError ||
      documentsQuery.isError ||
      threadsQuery.isError,
    refetch: () => {
      void knowledgeSpacesQuery.refetch();
      void documentsQuery.refetch();
      void threadsQuery.refetch();
    },
  };
}
