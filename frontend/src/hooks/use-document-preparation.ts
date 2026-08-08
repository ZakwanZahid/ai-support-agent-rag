"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { getAPIErrorMessage, normalizeAPIError } from "@/lib/api/client";
import { getDocument, prepareDocument } from "@/lib/api/documents";
import { queryKeys } from "@/lib/query-keys";
import { hasDocumentFailed, isDocumentReady } from "@/lib/terminology";
import type { KnowledgeDocument } from "@/types/document";

/** How often to re-check a document that is still being prepared. */
const POLL_INTERVAL_MS = 1_500;

/**
 * Stop polling after this long. Preparation is normally seconds; a document
 * still moving after two minutes means something is wrong upstream, and an
 * unbounded poll would keep hitting the API for as long as the tab is open.
 */
const POLL_TIMEOUT_MS = 120_000;

interface UseDocumentPreparationOptions {
  organizationId: string | null;
  /** Fired once, when the document first reports ready. */
  onReady?: (document: KnowledgeDocument) => void;
}

export function useDocumentPreparation({
  organizationId,
  onReady,
}: UseDocumentPreparationOptions) {
  const queryClient = useQueryClient();
  const [watchedDocumentId, setWatchedDocumentId] = useState<string | null>(
    null,
  );
  const [startedAt, setStartedAt] = useState<number | null>(null);

  // Guards the completion callback so it fires once per document, not on
  // every render that happens to observe a ready status.
  const notifiedForRef = useRef<string | null>(null);

  const documentQuery = useQuery({
    queryKey: queryKeys.document(organizationId, watchedDocumentId ?? ""),
    queryFn: () => getDocument(organizationId!, watchedDocumentId!),
    enabled: Boolean(organizationId && watchedDocumentId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Stop only once the document has actually finished, not merely
      // because a poll caught it in a status the general-purpose "in
      // progress" check does not consider transient. The very first poll
      // here can land before the prepare request's own status flip has
      // committed — `onMutate` starts watching synchronously, before the
      // POST that moves the document out of `pending` — so a poll landing
      // in that gap used to see `pending`, read it as "nothing to wait
      // for", and switch polling off for good. The document kept
      // preparing; nothing was left watching it.
      if (status && (isDocumentReady(status) || hasDocumentFailed(status))) {
        return false;
      }
      if (startedAt && Date.now() - startedAt > POLL_TIMEOUT_MS) {
        return false;
      }
      return POLL_INTERVAL_MS;
    },
    // Keep polling when the tab is in the background. Preparation takes long
    // enough that people switch away, and without this the interval pauses on
    // blur and they return to a timeline frozen mid-progress.
    refetchIntervalInBackground: true,
  });

  const document = documentQuery.data ?? null;
  const status = document?.status ?? null;

  const isReady = isDocumentReady(status);
  const hasFailed = hasDocumentFailed(status);
  // Mirrors the refetchInterval condition above: watching and not yet at a
  // terminal status, rather than "in progress" by the list's definition.
  const isPolling = Boolean(watchedDocumentId) && !isReady && !hasFailed;

  // Measured against the last successful fetch rather than a render-time
  // clock, so the value only changes when there is fresh data to react to.
  const timedOut =
    isPolling &&
    startedAt !== null &&
    documentQuery.dataUpdatedAt - startedAt > POLL_TIMEOUT_MS;

  useEffect(() => {
    if (!isReady || !document || notifiedForRef.current === document.id) {
      return;
    }
    notifiedForRef.current = document.id;
    void queryClient.invalidateQueries({
      queryKey: queryKeys.documents(organizationId),
    });
    onReady?.(document);
  }, [document, isReady, onReady, organizationId, queryClient]);

  const startWatching = useCallback((documentId: string) => {
    notifiedForRef.current = null;
    setStartedAt(Date.now());
    setWatchedDocumentId(documentId);
  }, []);

  const prepareMutation = useMutation({
    mutationFn: ({
      documentId,
      force = false,
    }: {
      documentId: string;
      force?: boolean;
    }) => prepareDocument(organizationId!, documentId, force),
    onMutate: ({ documentId }) => startWatching(documentId),
    onError: (error) => {
      // 409 means the document is already being prepared or already ready.
      // Neither is something the user did wrong, and polling will show the
      // real outcome, so stay quiet and keep watching.
      if (normalizeAPIError(error).status === 409) {
        return;
      }
      toast.error(getAPIErrorMessage(error));
    },
  });

  const prepare = useCallback(
    (documentId: string, force = false) =>
      prepareMutation.mutate({ documentId, force }),
    [prepareMutation],
  );

  const reset = useCallback(() => {
    notifiedForRef.current = null;
    setStartedAt(null);
    setWatchedDocumentId(null);
  }, []);

  return {
    prepare,
    /** Begin polling a document that is already being prepared elsewhere. */
    watch: startWatching,
    reset,
    document,
    status,
    isReady,
    hasFailed,
    timedOut,
    /** True from the moment the action is triggered until it settles. */
    isWorking: prepareMutation.isPending || isPolling,
    errorMessage: document?.error_message ?? null,
  };
}
