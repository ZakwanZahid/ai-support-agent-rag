"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getAPIErrorMessage, normalizeAPIError } from "@/lib/api/client";
import { listDocuments, prepareDocument } from "@/lib/api/documents";
import { queryKeys } from "@/lib/query-keys";
import { isDocumentInProgress } from "@/lib/terminology";

const POLL_INTERVAL_MS = 2_000;

interface UseDocumentsOptions {
  workspaceId: string | null;
  /** Restrict to a single knowledge space, for the detail page. */
  knowledgeSpaceId?: string | null;
}

/**
 * Document list plus the "Prepare for chat" action.
 *
 * Unlike the single-document hook used during onboarding, this polls the list
 * as a whole while anything in it is still being prepared, so several
 * documents can be prepared at once without a watcher each.
 */
export function useDocuments({
  workspaceId,
  knowledgeSpaceId = null,
}: UseDocumentsOptions) {
  const queryClient = useQueryClient();

  const documentsQuery = useQuery({
    queryKey: queryKeys.documents(workspaceId, knowledgeSpaceId),
    queryFn: () => listDocuments(workspaceId!, knowledgeSpaceId),
    enabled: Boolean(workspaceId),
    refetchInterval: (query) => {
      const documents = query.state.data ?? [];
      const anyInProgress = documents.some((document) =>
        isDocumentInProgress(document.status),
      );
      return anyInProgress ? POLL_INTERVAL_MS : false;
    },
    // Preparation outlives a tab switch; without this the list stops updating
    // on blur and comes back stale.
    refetchIntervalInBackground: true,
  });

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
      // Counts on the knowledge space list depend on document status.
      void queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeBases(workspaceId),
      });
    },
  });

  const documents = documentsQuery.data ?? [];

  return {
    documents,
    isLoading: documentsQuery.isPending,
    isError: documentsQuery.isError,
    refetch: documentsQuery.refetch,
    prepare: (documentId: string, force = false) =>
      prepareMutation.mutate({ documentId, force }),
    /** The row currently awaiting a response, so only its button spins. */
    preparingDocumentId: prepareMutation.isPending
      ? prepareMutation.variables?.documentId
      : undefined,
  };
}
