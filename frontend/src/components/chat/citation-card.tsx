import { FileText, Gauge } from "lucide-react";

import { cn, formatScore } from "@/lib/utils";

export interface CitationData {
  document_id: string;
  document_title: string;
  chunk_id: string;
  quote: string;
  score?: number | null;
  chunk_metadata?: Record<string, unknown> | null;
}

interface CitationCardProps {
  citation: CitationData;
  index?: number;
  className?: string;
}

export function CitationCard({
  citation,
  index,
  className,
}: CitationCardProps) {
  const score = formatScore(citation.score);

  return (
    <article
      className={cn(
        "rounded-md border border-zinc-200 bg-zinc-50 p-3.5",
        className,
      )}
    >
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <FileText
            aria-hidden="true"
            className="size-4 shrink-0 text-zinc-500"
          />
          <h4 className="truncate text-sm font-medium text-zinc-900">
            {citation.document_title || "Untitled document"}
          </h4>
        </div>
        {index !== undefined ? (
          <span className="shrink-0 text-xs font-medium text-zinc-500">
            Source {index + 1}
          </span>
        ) : null}
      </div>
      <blockquote className="mt-2.5 border-l-2 border-zinc-300 pl-3 text-sm leading-6 text-zinc-600">
        {citation.quote}
      </blockquote>
      {score ? (
        <div
          className="mt-3 flex items-center gap-1.5 text-xs text-zinc-500"
          title="Semantic relevance score"
        >
          <Gauge aria-hidden="true" className="size-3.5" />
          <span>{score} relevance</span>
        </div>
      ) : null}
    </article>
  );
}
