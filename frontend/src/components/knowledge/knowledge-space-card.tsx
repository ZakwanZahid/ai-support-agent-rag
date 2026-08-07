import { ArrowRight, BookOpen, Check, CircleDashed } from "lucide-react";
import Link from "next/link";

import { DeleteKnowledgeSpaceAction } from "@/components/knowledge/delete-knowledge-space-action";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { formatRelativeDate } from "@/lib/utils";
import type { KnowledgeSpace } from "@/types/knowledge";

interface KnowledgeSpaceCardProps {
  knowledgeSpace: KnowledgeSpace;
  workspaceId: string;
}

export function KnowledgeSpaceCard({
  knowledgeSpace,
  workspaceId,
}: KnowledgeSpaceCardProps) {
  const documentCount = knowledgeSpace.document_count ?? 0;
  const readyCount = knowledgeSpace.ready_document_count ?? 0;
  const isReady = readyCount > 0;

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="flex-row items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-surface-hover text-foreground-muted">
          <BookOpen aria-hidden="true" className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-base font-semibold text-foreground">
            {knowledgeSpace.name}
          </h2>
          <p className="mt-0.5 text-xs text-foreground-subtle">
            Updated {formatRelativeDate(knowledgeSpace.updated_at)}
          </p>
        </div>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col">
        <p className="line-clamp-2 min-h-[2.5rem] text-sm leading-6 text-foreground-muted">
          {knowledgeSpace.description || "No description yet."}
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs">
          <span className="text-foreground-subtle">
            {documentCount} {documentCount === 1 ? "document" : "documents"}
          </span>
          <span
            className={
              isReady
                ? "inline-flex items-center gap-1 text-success"
                : "inline-flex items-center gap-1 text-foreground-subtle"
            }
          >
            {isReady ? (
              <Check aria-hidden="true" className="size-3.5" />
            ) : (
              <CircleDashed aria-hidden="true" className="size-3.5" />
            )}
            {isReady
              ? `${readyCount} ready for chat`
              : "Nothing ready for chat yet"}
          </span>
        </div>

        <div className="mt-5 flex items-center justify-end gap-1">
          <DeleteKnowledgeSpaceAction
            workspaceId={workspaceId}
            knowledgeSpace={knowledgeSpace}
          />
          <Button asChild size="sm" variant="secondary">
            <Link href={`/dashboard/knowledge/${knowledgeSpace.id}`}>
              Open
              <ArrowRight aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
