import Link from "next/link";
import { ArrowRight, BookOpen } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { formatDate } from "@/lib/utils";

export interface KnowledgeBaseSummary {
  id: string;
  name: string;
  description?: string | null;
  created_at?: string | null;
  document_count?: number | null;
}

interface KnowledgeBaseCardProps {
  knowledgeBase: KnowledgeBaseSummary;
  href?: string;
}

export function KnowledgeBaseCard({
  knowledgeBase,
  href = `/dashboard/knowledge-bases/${knowledgeBase.id}`,
}: KnowledgeBaseCardProps) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="flex-row items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-surface-hover text-foreground-muted">
          <BookOpen aria-hidden="true" className="size-4" />
        </span>
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-foreground">
            {knowledgeBase.name}
          </h2>
          <p className="mt-1 text-xs text-foreground-subtle">
            Created {formatDate(knowledgeBase.created_at)}
          </p>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col">
        <p className="line-clamp-3 min-h-[3rem] text-sm leading-6 text-foreground-muted">
          {knowledgeBase.description || "No description provided."}
        </p>
        <div className="mt-5 flex items-center justify-between gap-3">
          {knowledgeBase.document_count !== null &&
          knowledgeBase.document_count !== undefined ? (
            <span className="text-xs text-foreground-subtle">
              {knowledgeBase.document_count}{" "}
              {knowledgeBase.document_count === 1 ? "document" : "documents"}
            </span>
          ) : (
            <span />
          )}
          <Button asChild size="sm" variant="ghost">
            <Link href={href}>
              Open
              <ArrowRight aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
