"use client";

import { useQuery } from "@tanstack/react-query";
import { Files, Upload } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader } from "@/components/common/page-header";
import { StatusBadge } from "@/components/common/status-badge";
import {
  DocumentList,
  type DocumentSummary,
} from "@/components/documents/document-card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { listDocuments, type DocumentResponse } from "@/lib/api/documents";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";
import { useDashboard } from "@/hooks/use-dashboard";
import { useDocumentActions } from "@/hooks/use-document-actions";

const statuses = [
  "all",
  "pending",
  "processing",
  "processed",
  "indexed",
  "failed",
] as const;

export default function DocumentsPage() {
  const { selectedOrganization } = useDashboard();
  const organizationId = selectedOrganization?.id;
  const [statusFilter, setStatusFilter] =
    useState<(typeof statuses)[number]>("all");
  const [selectedDocument, setSelectedDocument] =
    useState<DocumentResponse | null>(null);

  const knowledgeBasesQuery = useQuery({
    queryKey: queryKeys.knowledgeBases(organizationId),
    queryFn: () => listKnowledgeBases(organizationId!),
    enabled: Boolean(organizationId),
  });
  const documentsQuery = useQuery({
    queryKey: queryKeys.documents(organizationId),
    queryFn: () => listDocuments(organizationId!),
    enabled: Boolean(organizationId),
    refetchInterval: (query) =>
      query.state.data?.some((document) => document.status === "processing")
        ? 2_000
        : false,
  });
  const documentActions = useDocumentActions(organizationId ?? "");

  const knowledgeBaseNames = useMemo(
    () =>
      new Map(
        (knowledgeBasesQuery.data ?? []).map((knowledgeBase) => [
          knowledgeBase.id,
          knowledgeBase.name,
        ]),
      ),
    [knowledgeBasesQuery.data],
  );
  const documents: DocumentSummary[] = (documentsQuery.data ?? [])
    .filter(
      (document) =>
        statusFilter === "all" || document.status === statusFilter,
    )
    .map((document) => ({
      ...document,
      knowledge_base_name:
        knowledgeBaseNames.get(document.knowledge_base_id) ?? "Knowledge base",
    }));

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Sources"
        title="Documents"
        description="Track every source through upload, ingestion, and vector indexing."
        actions={
          <Button asChild>
            <Link href="/dashboard/knowledge-bases">
              <Upload aria-hidden="true" />
              Upload document
            </Link>
          </Button>
        }
      />

      {!selectedOrganization ? (
        <EmptyState
          icon={Files}
          title="Select an organization"
          description="Documents are always scoped to an organization."
        />
      ) : documentsQuery.isPending || knowledgeBasesQuery.isPending ? (
        <LoadingSkeleton rows={5} />
      ) : documentsQuery.isError || knowledgeBasesQuery.isError ? (
        <ErrorState
          onRetry={() => {
            void documentsQuery.refetch();
            void knowledgeBasesQuery.refetch();
          }}
        />
      ) : documentsQuery.data.length === 0 ? (
        <EmptyState
          icon={Files}
          title="No documents yet"
          description="Open a knowledge base and upload a support source to begin."
          action={
            <Button asChild>
              <Link href="/dashboard/knowledge-bases">Choose knowledge base</Link>
            </Button>
          }
        />
      ) : (
        <>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-zinc-600">
              Showing {documents.length} of {documentsQuery.data.length} documents
            </p>
            <div className="flex items-center gap-2">
              <label htmlFor="status-filter" className="text-sm text-zinc-600">
                Status
              </label>
              <select
                id="status-filter"
                value={statusFilter}
                onChange={(event) =>
                  setStatusFilter(
                    event.target.value as (typeof statuses)[number],
                  )
                }
                className="h-10 rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 outline-none focus-visible:ring-2 focus-visible:ring-zinc-950/10"
              >
                {statuses.map((status) => (
                  <option key={status} value={status}>
                    {status === "all"
                      ? "All statuses"
                      : status.charAt(0).toUpperCase() + status.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {documents.length === 0 ? (
            <EmptyState
              compact
              icon={Files}
              title="No documents match this status"
              description="Choose another filter to see the rest of your sources."
            />
          ) : (
            <DocumentList
              documents={documents}
              onIngest={documentActions.ingest}
              onIndex={documentActions.index}
              onView={(document) =>
                setSelectedDocument(
                  documentsQuery.data.find((item) => item.id === document.id) ??
                    null,
                )
              }
              busyDocumentId={documentActions.busyDocumentId}
              busyAction={documentActions.busyAction}
            />
          )}
        </>
      )}

      <Dialog
        open={Boolean(selectedDocument)}
        onOpenChange={(open) => {
          if (!open) setSelectedDocument(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedDocument?.title}</DialogTitle>
            <DialogDescription>
              Document metadata from the current organization.
            </DialogDescription>
          </DialogHeader>
          {selectedDocument ? (
            <dl className="grid gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-zinc-500">Status</dt>
                <dd className="mt-1">
                  <StatusBadge status={selectedDocument.status} />
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500">Uploaded</dt>
                <dd className="mt-1 font-medium text-zinc-900">
                  {formatDate(selectedDocument.created_at)}
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500">Knowledge base</dt>
                <dd className="mt-1 font-medium text-zinc-900">
                  {knowledgeBaseNames.get(selectedDocument.knowledge_base_id) ??
                    "Not available"}
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500">Filename</dt>
                <dd className="mt-1 break-words font-medium text-zinc-900">
                  {selectedDocument.file_name ?? "Not available"}
                </dd>
              </div>
              {selectedDocument.error_message ? (
                <div className="sm:col-span-2">
                  <dt className="text-red-700">Processing error</dt>
                  <dd className="mt-1 text-red-700">
                    {selectedDocument.error_message}
                  </dd>
                </div>
              ) : null}
            </dl>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
