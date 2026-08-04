import { Quote } from "lucide-react";

import { SourceCard } from "@/components/chat/source-card";
import { cn } from "@/lib/utils";
import type { Source } from "@/types/conversation";

interface SourcesPanelProps {
  sources: Source[];
  className?: string;
}

/**
 * Sources for the most recent answer, shown beside the conversation on wide
 * screens. Narrower layouts collapse the same information under each answer
 * instead, so the two never appear at once.
 */
export function SourcesPanel({ sources, className }: SourcesPanelProps) {
  return (
    <aside
      aria-label="Sources"
      className={cn("flex min-h-0 flex-col border-l border-border", className)}
    >
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-medium text-foreground">Sources</h2>
        <p className="mt-0.5 text-xs text-foreground-subtle">
          {sources.length > 0
            ? "Passages behind the latest answer"
            : "Passages appear here once you ask something"}
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {sources.length === 0 ? (
          <div className="flex flex-col items-center px-4 py-10 text-center">
            <span className="mb-3 flex size-9 items-center justify-center rounded-md border border-border bg-surface-subtle text-foreground-subtle">
              <Quote aria-hidden="true" className="size-4" />
            </span>
            <p className="text-xs leading-5 text-foreground-subtle">
              Every answer lists the passages it came from, so you can check it.
            </p>
          </div>
        ) : (
          <div className="grid gap-2">
            {sources.map((source, index) => (
              <SourceCard
                key={`${source.chunk_id}-${index}`}
                source={source}
                index={index}
                showScore
              />
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
