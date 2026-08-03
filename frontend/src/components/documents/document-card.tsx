import { FileText } from "lucide-react";

import {
  DocumentStatusActions,
  type DocumentActionTarget,
} from "@/components/documents/document-status-actions";
import { StatusBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { formatDate } from "@/lib/utils";

export interface DocumentSummary extends DocumentActionTarget {
  title?: string | null;
  filename?: string | null;
  file_name?: string | null;
  knowledge_base_id?: string | null;
  knowledge_base_name?: string | null;
  created_at?: string | null;
  uploaded_at?: string | null;
}

export interface DocumentInteractionProps {
  onIngest?: (document: DocumentSummary) => void;
  onIndex?: (document: DocumentSummary) => void;
  onView?: (document: DocumentSummary) => void;
  busyDocumentId?: string | null;
  busyAction?: "ingest" | "index" | null;
}

function getDocumentTitle(document: DocumentSummary) {
  return document.title || document.filename || document.file_name || "Untitled document";
}

export function DocumentCard({
  document,
  onIngest,
  onIndex,
  onView,
  busyDocumentId,
  busyAction,
}: { document: DocumentSummary } & DocumentInteractionProps) {
  return (
    <Card>
      <CardHeader className="flex-row items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-surface-hover text-foreground-muted">
          <FileText aria-hidden="true" className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-foreground">
            {getDocumentTitle(document)}
          </h3>
          <p className="mt-1 truncate text-xs text-foreground-subtle">
            {document.knowledge_base_name || "Knowledge base"}
          </p>
        </div>
        <StatusBadge status={document.status} />
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-foreground-subtle">
          Uploaded {formatDate(document.uploaded_at ?? document.created_at)}
        </p>
        <DocumentStatusActions
          document={document}
          onIngest={onIngest as ((document: DocumentActionTarget) => void) | undefined}
          onIndex={onIndex as ((document: DocumentActionTarget) => void) | undefined}
          onView={onView as ((document: DocumentActionTarget) => void) | undefined}
          busyAction={busyDocumentId === document.id ? busyAction : null}
        />
      </CardContent>
    </Card>
  );
}

interface DocumentListProps extends DocumentInteractionProps {
  documents: DocumentSummary[];
}

export function DocumentList({
  documents,
  onIngest,
  onIndex,
  onView,
  busyDocumentId,
  busyAction,
}: DocumentListProps) {
  const interactions = {
    onIngest,
    onIndex,
    onView,
    busyDocumentId,
    busyAction,
  };

  return (
    <>
      <div className="grid gap-3 md:hidden">
        {documents.map((document) => (
          <DocumentCard
            key={document.id}
            document={document}
            {...interactions}
          />
        ))}
      </div>
      <div className="hidden overflow-hidden rounded-lg border border-border bg-white md:block">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-border bg-surface-subtle text-xs font-medium uppercase tracking-wide text-foreground-subtle">
              <tr>
                <th className="px-5 py-3">Document</th>
                <th className="px-5 py-3">Knowledge base</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Uploaded</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {documents.map((document) => (
                <tr key={document.id} className="hover:bg-surface-hover/70">
                  <td className="px-5 py-4 font-medium text-foreground">
                    <span className="block max-w-64 truncate">
                      {getDocumentTitle(document)}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-foreground-muted">
                    {document.knowledge_base_name || "—"}
                  </td>
                  <td className="px-5 py-4">
                    <StatusBadge status={document.status} />
                  </td>
                  <td className="px-5 py-4 text-foreground-muted">
                    {formatDate(document.uploaded_at ?? document.created_at)}
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex justify-end">
                      <DocumentStatusActions
                        document={document}
                        onIngest={
                          onIngest as
                            | ((document: DocumentActionTarget) => void)
                            | undefined
                        }
                        onIndex={
                          onIndex as
                            | ((document: DocumentActionTarget) => void)
                            | undefined
                        }
                        onView={
                          onView as
                            | ((document: DocumentActionTarget) => void)
                            | undefined
                        }
                        busyAction={
                          busyDocumentId === document.id ? busyAction : null
                        }
                        compact
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
