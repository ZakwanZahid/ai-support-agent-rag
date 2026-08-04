import { FileText } from "lucide-react";
import Link from "next/link";

import { cn, formatScore } from "@/lib/utils";
import type { Source } from "@/types/conversation";

interface SourceCardProps {
  source: Source;
  /** Position in the answer's source list, shown as "Source 1". */
  index?: number;
  /**
   * Relevance is a cosine similarity. It means little without context, so it
   * is off unless something explicitly asks for it.
   */
  showScore?: boolean;
  knowledgeSpaceId?: string;
  className?: string;
}

export function SourceCard({
  source,
  index,
  showScore = false,
  knowledgeSpaceId,
  className,
}: SourceCardProps) {
  const score = showScore ? formatScore(source.score) : null;
  const title = source.document_title || "Untitled document";

  return (
    <article
      className={cn(
        "rounded-lg border border-border bg-surface-subtle p-3.5",
        className,
      )}
    >
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <FileText
            aria-hidden="true"
            className="size-3.5 shrink-0 text-foreground-subtle"
          />
          {knowledgeSpaceId ? (
            <Link
              href={`/dashboard/knowledge/${knowledgeSpaceId}`}
              className="truncate text-sm font-medium text-foreground underline-offset-4 hover:underline"
            >
              {title}
            </Link>
          ) : (
            <h4 className="truncate text-sm font-medium text-foreground">
              {title}
            </h4>
          )}
        </div>
        {index !== undefined ? (
          <span className="shrink-0 text-xs text-foreground-subtle">
            Source {index + 1}
          </span>
        ) : null}
      </div>

      <blockquote className="mt-2.5 border-l-2 border-border-strong pl-3 text-sm leading-6 text-foreground-muted">
        {source.quote}
      </blockquote>

      {score ? (
        <p className="mt-2.5 text-xs text-foreground-subtle">
          {score} relevance
        </p>
      ) : null}
    </article>
  );
}
