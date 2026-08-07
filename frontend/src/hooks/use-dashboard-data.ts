"use client";

import { useQuery } from "@tanstack/react-query";

import { listConversations } from "@/lib/api/conversations";
import { listDocuments } from "@/lib/api/documents";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import { documentFilterCount, isDocumentReady } from "@/lib/terminology";

const RECENT_LIMIT = 5;

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

  // Only the five rows the dashboard shows. The totals beside them come from
  // the page's own status counts, which describe the whole collection — so
  // the summary stays right without fetching every document to count it.
  const documentsQuery = useQuery({
    queryKey: queryKeys.documentsSummary(workspaceId),
    queryFn: () => listDocuments(workspaceId!, { limit: RECENT_LIMIT }),
    enabled,
  });

  const chatThreadsQuery = useQuery({
    queryKey: queryKeys.conversations(workspaceId),
    queryFn: () => listConversations(workspaceId!),
    enabled,
  });

  const knowledgeSpaces = knowledgeSpacesQuery.data ?? [];
  const documents = documentsQuery.data?.items ?? [];
  const chatThreads = chatThreadsQuery.data ?? [];
  const statusCounts = documentsQuery.data?.status_counts ?? {};

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
      documents: documentFilterCount("all", statusCounts),
      readyDocuments: documentFilterCount("ready", statusCounts),
      chatThreads: chatThreads.length,
    },
    // The API returns documents newest first and conversations by most
    // recently updated, so the first few are already the right ones.
    recentDocuments: documents,
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
