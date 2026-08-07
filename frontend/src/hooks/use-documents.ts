"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { useMemo } from "react";
import { toast } from "sonner";

import { getAPIErrorMessage, normalizeAPIError } from "@/lib/api/client";
import {
  deleteDocument,
  listDocuments,
  prepareDocument,
} from "@/lib/api/documents";
import { queryKeys } from "@/lib/query-keys";
import { isDocumentInProgress } from "@/lib/terminology";
import type { DocumentStatus } from "@/types/document";

const POLL_INTERVAL_MS = 2_000;
const PAGE_SIZE = 25;

interface UseDocumentsOptions {
  workspaceId: string | null;
  /** Restrict to a single knowledge space, for the detail page. */
  knowledgeSpaceId?: string | null;
  /** Title search, run by the database. Pass it debounced. */
  search?: string;
  /** Raw API statuses; callers get these from `terminology.ts`. */
  statuses?: readonly DocumentStatus[];
}

/**
 * Document list plus the "Prepare for chat" and delete actions.
 *
 * Paged rather than fetched whole. Search and status filtering are part of
 * the query key, so changing either asks the server a new question instead of
 * re-filtering rows the browser happens to be holding — which is the only
 * reason client-side filtering ever worked, and stops being true as soon as
 * the collection no longer arrives in one response.
 */
export function useDocuments({
  workspaceId,
  knowledgeSpaceId = null,
  search = "",
  statuses = [],
}: UseDocumentsOptions) {
  const queryClient = useQueryClient();
  const normalizedSearch = search.trim();
  // Spread into a plain array so the key is compared by value, not identity.
  const statusKey = [...statuses].sort();

  const documentsQuery = useInfiniteQuery({
    queryKey: queryKeys.documents(workspaceId, knowledgeSpaceId, {
      search: normalizedSearch,
      statuses: statusKey,
    }),
    queryFn: ({ pageParam }) =>
      listDocuments(workspaceId!, {
        knowledgeBaseId: knowledgeSpaceId,
        search: normalizedSearch,
        statuses,
        limit: PAGE_SIZE,
        cursor: pageParam,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) =>
      lastPage.has_more ? lastPage.next_cursor : null,
    enabled: Boolean(workspaceId),
    refetchInterval: (query) => {
      const anyInProgress = (query.state.data?.pages ?? []).some((page) =>
        page.items.some((document) => isDocumentInProgress(document.status)),
      );
      return anyInProgress ? POLL_INTERVAL_MS : false;
    },
    // Preparation outlives a tab switch; without this the list stops updating
    // on blur and comes back stale.
    refetchIntervalInBackground: true,
  });

  const documents = useMemo(
    () => (documentsQuery.data?.pages ?? []).flatMap((page) => page.items),
    [documentsQuery.data],
  );

  // Counts come from the first page: they describe the whole filtered set,
  // not the rows loaded so far, so a later page cannot change them.
  const statusCounts = documentsQuery.data?.pages[0]?.status_counts ?? {};

  const prepareMutation = useMutation({
    mutationFn: ({
      documentId,
      force = false,
    }: {
      documentId: string;
      force?: boolean;
    }) => prepareDocument(workspaceId!, documentId, force),
    onSuccess: () => {
      // Pick up the "processing" status immediately rather than waiting a
      // full poll interval for the row to react.
      void documentsQuery.refetch();
    },
    onError: (error) => {
      // 409 means it is already underway or already ready; polling will show
      // the real outcome, so there is nothing useful to tell the user.
      if (normalizeAPIError(error).status === 409) {
        void documentsQuery.refetch();
        return;
      }
      toast.error(getAPIErrorMessage(error));
    },
    onSettled: () => {
      // Counts on the knowledge space list and the dashboard summary both
      // depend on document status.
      void queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeBases(workspaceId),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.documentsSummary(workspaceId),
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => deleteDocument(workspaceId!, documentId),
    onSuccess: () => {
      toast.success("Document deleted.");
      // Every page is refetched, not just the one the row was on: removing a
      // row shifts nothing under a cursor, but the status counts change.
      void documentsQuery.refetch();
    },
    onError: (error) => {
      // 409 here is the API refusing to delete a document mid-preparation.
      // Its message says so, and it is the one the user needs.
      toast.error(getAPIErrorMessage(error));
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeBases(workspaceId),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.documentsSummary(workspaceId),
      });
    },
  });

  return {
    documents,
    statusCounts,
    isLoading: documentsQuery.isPending,
    isError: documentsQuery.isError,
    refetch: documentsQuery.refetch,
    hasMore: documentsQuery.hasNextPage,
    loadMore: () => void documentsQuery.fetchNextPage(),
    isLoadingMore: documentsQuery.isFetchingNextPage,
    prepare: (documentId: string, force = false) =>
      prepareMutation.mutate({ documentId, force }),
    /** The row currently awaiting a response, so only its button spins. */
    preparingDocumentId: prepareMutation.isPending
      ? prepareMutation.variables?.documentId
      : undefined,
    remove: (documentId: string) => deleteMutation.mutate(documentId),
    deletingDocumentId: deleteMutation.isPending
      ? deleteMutation.variables
      : undefined,
  };
}
