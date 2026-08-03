"use client";

import { useQuery } from "@tanstack/react-query";

import { listConversations } from "@/lib/api/conversations";
import { listDocuments } from "@/lib/api/documents";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import { isDocumentReady } from "@/lib/terminology";

/**
 * Everything the dashboard renders, gathered in one place so the page stays
 * about layout and the loading and error states are decided once rather than
 * per section.
 */
export function useDashboardData(workspaceId: string | null) {
  const enabled = Boolean(workspaceId);

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

  const chatThreadsQuery = useQuery({
    queryKey: queryKeys.conversations(workspaceId),
    queryFn: () => listConversations(workspaceId!),
    enabled,
  });

  const knowledgeSpaces = knowledgeSpacesQuery.data ?? [];
  const documents = documentsQuery.data ?? [];
  const chatThreads = chatThreadsQuery.data ?? [];

  const readyDocuments = documents.filter((document) =>
    isDocumentReady(document.status),
  );

  return {
    knowledgeSpaces,
    documents,
    chatThreads,
    readyDocuments,
    stats: {
      knowledgeSpaces: knowledgeSpaces.length,
      documents: documents.length,
      readyDocuments: readyDocuments.length,
      chatThreads: chatThreads.length,
    },
    // The API returns documents newest first and conversations by most
    // recently updated, so the first few are already the right ones.
    recentDocuments: documents.slice(0, 5),
    recentChatThreads: chatThreads.slice(0, 5),
    isLoading:
      knowledgeSpacesQuery.isPending ||
      documentsQuery.isPending ||
      chatThreadsQuery.isPending,
    isError:
      knowledgeSpacesQuery.isError ||
      documentsQuery.isError ||
      chatThreadsQuery.isError,
    refetch: () => {
      void knowledgeSpacesQuery.refetch();
      void documentsQuery.refetch();
      void chatThreadsQuery.refetch();
    },
  };
}
