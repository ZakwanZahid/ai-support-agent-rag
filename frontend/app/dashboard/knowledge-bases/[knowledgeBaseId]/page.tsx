"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  FileSearch,
  MessagesSquare,
  ScanSearch,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader } from "@/components/common/page-header";
import { StatusBadge } from "@/components/common/status-badge";
import {
  DocumentList,
  type DocumentSummary,
} from "@/components/documents/document-card";
import { DocumentUploadForm } from "@/components/documents/document-upload-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getAPIErrorMessage } from "@/lib/api/client";
import {
  listDocuments,
  uploadDocument,
  type DocumentResponse,
} from "@/lib/api/documents";
import { getKnowledgeBase } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";
import { useWorkspace } from "@/hooks/use-workspace";
import { useDocumentActions } from "@/hooks/use-document-actions";

const lifecycle = [
  { title: "Upload", description: "Store a support source.", icon: Upload },
  { title: "Ingest", description: "Extract and chunk text.", icon: FileSearch },
  { title: "Index", description: "Create vector embeddings.", icon: ScanSearch },
  { title: "Chat", description: "Answer with citations.", icon: MessagesSquare },
];

export default function KnowledgeBaseDetailPage() {
  const params = useParams<{ knowledgeBaseId: string }>();
  const knowledgeBaseId = params.knowledgeBaseId;
  const { activeWorkspace } = useWorkspace();
  const organizationId = activeWorkspace?.id;
  const queryClient = useQueryClient();
  const [selectedDocument, setSelectedDocument] =
    useState<DocumentResponse | null>(null);

  const knowledgeBaseQuery = useQuery({
    queryKey: queryKeys.knowledgeBase(organizationId, knowledgeBaseId),
    queryFn: () => getKnowledgeBase(organizationId!, knowledgeBaseId),
    enabled: Boolean(organizationId),
  });
  const documentsQuery = useQuery({
    queryKey: queryKeys.documents(organizationId, knowledgeBaseId),
    queryFn: () => listDocuments(organizationId!, knowledgeBaseId),
    enabled: Boolean(organizationId),
    refetchInterval: (query) =>
      query.state.data?.some((document) => document.status === "processing")
        ? 2_000
        : false,
  });
  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      uploadDocument(organizationId!, knowledgeBaseId, { file }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["documents", organizationId],
      });
      window.setTimeout(
        () =>
          void queryClient.invalidateQueries({
            queryKey: ["documents", organizationId],
          }),
        1_500,
      );
      toast.success("Document uploaded.");
    },
    onError: (error) => toast.error(getAPIErrorMessage(error)),
  });
  const documentActions = useDocumentActions(organizationId ?? "");

  if (!organizationId) {
    return (
      <EmptyState
        icon={BookOpen}
        title="Select an organization"
        description="Choose an organization before opening a knowledge base."
      />
    );
  }

  if (knowledgeBaseQuery.isPending || documentsQuery.isPending) {
    return <LoadingSkeleton variant="detail" rows={4} />;
  }

  if (knowledgeBaseQuery.isError || documentsQuery.isError) {
    return (
      <ErrorState
        title="Knowledge base could not be loaded"
        onRetry={() => {
          void knowledgeBaseQuery.refetch();
          void documentsQuery.refetch();
        }}
      />
    );
  }

  const documents: DocumentSummary[] = documentsQuery.data.map((document) => ({
    ...document,
    knowledge_base_name: knowledgeBaseQuery.data.name,
  }));

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Knowledge base"
        title={knowledgeBaseQuery.data.name}
        description={
          knowledgeBaseQuery.data.description ||
          "A focused source collection for support retrieval."
        }
        actions={
          <Button asChild>
            <Link
              href={`/dashboard/chat?knowledgeBaseId=${encodeURIComponent(knowledgeBaseId)}`}
            >
              <MessagesSquare aria-hidden="true" />
              Chat with this knowledge
            </Link>
          </Button>
        }
      />

      <section aria-labelledby="lifecycle-heading">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 id="lifecycle-heading" className="text-sm font-semibold text-foreground">
            Document lifecycle
          </h2>
          <p className="text-xs text-foreground-subtle">Upload → ingest → index → chat</p>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {lifecycle.map(({ title, description, icon: Icon }, index) => (
            <Card key={title}>
              <CardContent className="flex items-start gap-3 p-4">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-surface-hover text-foreground-muted">
                  <Icon aria-hidden="true" className="size-4" />
                </span>
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {index + 1}. {title}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-foreground-subtle">
                    {description}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(18rem,0.7fr)_minmax(0,1.7fr)]">
        <Card className="h-fit">
          <CardHeader>
            <h2 className="text-base font-semibold text-foreground">
              Upload a source
            </h2>
            <p className="text-sm leading-6 text-foreground-muted">
              Add a text, Markdown, PDF, or Word document to this knowledge base.
            </p>
          </CardHeader>
          <CardContent>
            <DocumentUploadForm
              onUpload={async (file) => {
                await uploadMutation.mutateAsync(file);
              }}
              uploading={uploadMutation.isPending}
              accept=".txt,.md,.markdown,.pdf,.docx"
            />
          </CardContent>
        </Card>

        <div className="min-w-0">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-foreground">Documents</h2>
              <p className="mt-1 text-sm text-foreground-muted">
                {documents.length} {documents.length === 1 ? "source" : "sources"}
              </p>
            </div>
          </div>
          {documents.length === 0 ? (
            <EmptyState
              compact
              icon={Upload}
              title="No documents uploaded"
              description="Upload the first source, then ingest and index it for retrieval."
            />
          ) : (
            <DocumentList
              documents={documents}
              onIngest={documentActions.ingest}
              onIndex={documentActions.index}
              onView={(document) => {
                const fullDocument = documentsQuery.data.find(
                  (item) => item.id === document.id,
                );
                setSelectedDocument(fullDocument ?? null);
              }}
              busyDocumentId={documentActions.busyDocumentId}
              busyAction={documentActions.busyAction}
            />
          )}
        </div>
      </section>

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
              Source metadata and current processing state.
            </DialogDescription>
          </DialogHeader>
          {selectedDocument ? (
            <dl className="grid gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-foreground-subtle">Status</dt>
                <dd className="mt-1">
                  <StatusBadge status={selectedDocument.status} />
                </dd>
              </div>
              <div>
                <dt className="text-foreground-subtle">Uploaded</dt>
                <dd className="mt-1 font-medium text-foreground">
                  {formatDate(selectedDocument.created_at)}
                </dd>
              </div>
              <div>
                <dt className="text-foreground-subtle">Filename</dt>
                <dd className="mt-1 break-words font-medium text-foreground">
                  {selectedDocument.file_name ?? "Not available"}
                </dd>
              </div>
              <div>
                <dt className="text-foreground-subtle">Source type</dt>
                <dd className="mt-1 capitalize font-medium text-foreground">
                  {selectedDocument.source_type}
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
          <div className="flex justify-end">
            <Button variant="outline" onClick={() => setSelectedDocument(null)}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
