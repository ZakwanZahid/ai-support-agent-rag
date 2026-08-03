"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import type { DocumentSummary } from "@/components/documents/document-card";
import { getAPIErrorMessage } from "@/lib/api/client";
import { indexDocument, ingestDocument } from "@/lib/api/documents";

export function useDocumentActions(organizationId: string) {
  const queryClient = useQueryClient();

  const refreshDocuments = () =>
    queryClient.invalidateQueries({
      queryKey: ["documents", organizationId],
    });

  const ingestMutation = useMutation({
    mutationFn: (document: DocumentSummary) =>
      ingestDocument(
        organizationId,
        document.id,
        document.status === "failed",
      ),
    onSuccess: () => {
      toast.success("Document ingestion started.");
      void refreshDocuments();
      window.setTimeout(() => void refreshDocuments(), 1_500);
    },
    onError: (error) => toast.error(getAPIErrorMessage(error)),
  });

  const indexMutation = useMutation({
    mutationFn: (document: DocumentSummary) =>
      indexDocument(
        organizationId,
        document.id,
        document.status === "indexed",
      ),
    onSuccess: () => {
      toast.success("Document indexing started.");
      void refreshDocuments();
      window.setTimeout(() => void refreshDocuments(), 1_500);
    },
    onError: (error) => toast.error(getAPIErrorMessage(error)),
  });

  return {
    ingest: (document: DocumentSummary) => ingestMutation.mutate(document),
    index: (document: DocumentSummary) => indexMutation.mutate(document),
    busyDocumentId:
      ingestMutation.variables?.id ?? indexMutation.variables?.id ?? null,
    busyAction: ingestMutation.isPending
      ? ("ingest" as const)
      : indexMutation.isPending
        ? ("index" as const)
        : null,
  };
}
