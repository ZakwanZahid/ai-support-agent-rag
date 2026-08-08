import { Sparkles } from "lucide-react";

import { MarkdownAnswer } from "@/components/chat/markdown-answer";
import { SourceCard } from "@/components/chat/source-card";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageModel } from "@/types/conversation";

interface ChatMessageProps {
  message: Pick<ChatMessageModel, "role" | "content"> & {
    id?: string;
    citations?: ChatMessageModel["citations"];
  };
  /** Renders the thinking state while an answer is being generated. */
  pending?: boolean;
  /**
   * Hides the inline sources. The chat page shows them in a side panel on wide
   * screens, and inline underneath everywhere else.
   */
  hideInlineSources?: boolean;
  className?: string;
}

export function ChatMessage({
  message,
  pending = false,
  hideInlineSources = false,
  className,
}: ChatMessageProps) {
  const isUser = message.role === "user";
  const sources = message.citations ?? [];

  if (isUser) {
    return (
      <article
        aria-label="Your message"
        className={cn("flex justify-end", className)}
      >
        <p className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm leading-6 text-primary-foreground">
          {message.content}
        </p>
      </article>
    );
  }

  return (
    <article aria-label="Assistant message" className={cn("flex gap-3", className)}>
      <span className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-md border border-border bg-surface text-foreground-muted">
        <Sparkles aria-hidden="true" className="size-3.5" />
      </span>

      <div className="min-w-0 flex-1">
        {pending ? (
          <p
            className="flex items-center gap-1 py-2 text-sm text-foreground-subtle"
            aria-live="polite"
          >
            <span className="sr-only">Generating an answer</span>
            {/* Three dots that fade in sequence, rather than a spinner that
                implies a fixed-length wait. */}
            {[0, 1, 2].map((dot) => (
              <span
                key={dot}
                aria-hidden="true"
                className="size-1.5 animate-pulse rounded-full bg-foreground-subtle"
                style={{ animationDelay: `${dot * 160}ms` }}
              />
            ))}
          </p>
        ) : (
          <MarkdownAnswer className="break-words" content={message.content} />
        )}

        {!pending && sources.length > 0 && !hideInlineSources ? (
          <details className="group mt-3" open>
            <summary className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-sm text-xs font-medium text-foreground-muted outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
              {sources.length} {sources.length === 1 ? "source" : "sources"}
              <span
                aria-hidden="true"
                className="text-foreground-subtle transition-transform group-open:rotate-180"
              >
                ↓
              </span>
            </summary>
            <div className="mt-2 grid gap-2">
              {sources.map((source, index) => (
                <SourceCard
                  key={`${source.chunk_id}-${index}`}
                  source={source}
                  index={index}
                />
              ))}
            </div>
          </details>
        ) : null}
      </div>
    </article>
  );
}
