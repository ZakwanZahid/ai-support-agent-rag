import { Bot, UserRound } from "lucide-react";

import {
  CitationCard,
  type CitationData,
} from "@/components/chat/citation-card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatDate } from "@/lib/utils";

export interface ChatMessageData {
  id?: string;
  role: "user" | "assistant" | string;
  content: string;
  citations?: CitationData[] | null;
  created_at?: string | null;
}

interface ChatMessageProps {
  message: ChatMessageData;
  pending?: boolean;
  className?: string;
}

export function ChatMessage({
  message,
  pending = false,
  className,
}: ChatMessageProps) {
  const isUser = message.role === "user";
  const citations = message.citations ?? [];

  return (
    <article
      className={cn(
        "flex gap-3",
        isUser && "justify-end",
        className,
      )}
      aria-label={`${isUser ? "Your" : "Assistant"} message`}
    >
      {!isUser ? (
        <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md border border-zinc-200 bg-white text-zinc-700">
          <Bot aria-hidden="true" className="size-4" />
        </span>
      ) : null}

      <div
        className={cn(
          "min-w-0 max-w-[min(100%,48rem)]",
          isUser && "max-w-[min(88%,40rem)]",
        )}
      >
        <div
          className={cn(
            "rounded-lg px-4 py-3 text-sm leading-6",
            isUser
              ? "bg-zinc-900 text-white"
              : "border border-zinc-200 bg-white text-zinc-800",
          )}
        >
          {pending ? (
            <div className="space-y-2 py-1" aria-label="Generating answer">
              <Skeleton className="h-3 w-52 bg-zinc-200" />
              <Skeleton className="h-3 w-36 bg-zinc-200" />
            </div>
          ) : (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          )}
        </div>

        {!pending && citations.length > 0 ? (
          <details className="group mt-3" open>
            <summary className="cursor-pointer list-none text-xs font-medium text-zinc-600 outline-none hover:text-zinc-950 focus-visible:ring-2 focus-visible:ring-zinc-950 [&::-webkit-details-marker]:hidden">
              <span className="inline-flex items-center gap-1.5 rounded-sm">
                {citations.length} {citations.length === 1 ? "citation" : "citations"}
                <span
                  aria-hidden="true"
                  className="text-zinc-400 transition-transform group-open:rotate-180"
                >
                  ↓
                </span>
              </span>
            </summary>
            <div className="mt-2 grid gap-2 lg:grid-cols-2">
              {citations.map((citation, index) => (
                <CitationCard
                  key={`${citation.chunk_id}-${index}`}
                  citation={citation}
                  index={index}
                />
              ))}
            </div>
          </details>
        ) : null}

        {message.created_at ? (
          <p
            className={cn(
              "mt-1.5 text-xs text-zinc-400",
              isUser && "text-right",
            )}
          >
            {formatDate(message.created_at)}
          </p>
        ) : null}
      </div>

      {isUser ? (
        <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md bg-zinc-200 text-zinc-700">
          <UserRound aria-hidden="true" className="size-4" />
        </span>
      ) : null}
    </article>
  );
}
