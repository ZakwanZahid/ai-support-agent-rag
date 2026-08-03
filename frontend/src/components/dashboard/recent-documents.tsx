import { FileText } from "lucide-react";
import Link from "next/link";

import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { formatRelativeDate } from "@/lib/utils";
import type { KnowledgeDocument } from "@/types/document";

interface RecentDocumentsProps {
  documents: KnowledgeDocument[];
}

export function RecentDocuments({ documents }: RecentDocumentsProps) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-foreground">
          Recent documents
        </h2>
        {documents.length > 0 ? (
          <Button asChild size="sm" variant="ghost">
            <Link href="/dashboard/documents">View all</Link>
          </Button>
        ) : null}
      </CardHeader>

      <CardContent>
        {documents.length === 0 ? (
          <div className="py-4">
            <p className="text-sm leading-6 text-foreground-muted">
              No documents uploaded yet. Add PDFs, FAQs, policies, or product
              docs to prepare your assistant.
            </p>
            <Button asChild size="sm" className="mt-4">
              <Link href="/dashboard/knowledge-bases">Upload document</Link>
            </Button>
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {documents.map((document) => (
              <li
                key={document.id}
                className="flex items-center gap-3 py-3 first:pt-0 last:pb-0"
              >
                <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-border bg-surface-subtle text-foreground-subtle">
                  <FileText aria-hidden="true" className="size-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">
                    {document.title}
                  </p>
                  <p className="text-xs text-foreground-subtle">
                    {formatRelativeDate(document.created_at)}
                  </p>
                </div>
                <StatusBadge status={document.status} />
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
