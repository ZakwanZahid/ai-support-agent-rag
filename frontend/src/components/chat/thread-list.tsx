"use client";

import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn, formatRelativeDate } from "@/lib/utils";
import type { ChatThread } from "@/types/conversation";

interface ThreadListProps {
  threads: ChatThread[];
  activeThreadId: string | null;
  onSelect: (threadId: string) => void;
  onNewThread: () => void;
  className?: string;
}

export function ThreadList({
  threads,
  activeThreadId,
  onSelect,
  onNewThread,
  className,
}: ThreadListProps) {
  return (
    <div className={cn("flex min-h-0 flex-col", className)}>
      <div className="p-3">
        <Button className="w-full" size="sm" onClick={onNewThread}>
          <Plus aria-hidden="true" />
          New chat
        </Button>
      </div>

      <nav
        aria-label="Chat threads"
        className="min-h-0 flex-1 overflow-y-auto px-2 pb-3"
      >
        {threads.length === 0 ? (
          <p className="px-2 py-3 text-xs leading-5 text-foreground-subtle">
            No chats in this knowledge space yet.
          </p>
        ) : (
          <ul className="space-y-0.5">
            {threads.map((thread) => {
              const isActive = thread.id === activeThreadId;
              return (
                <li key={thread.id}>
                  <button
                    type="button"
                    aria-current={isActive ? "true" : undefined}
                    onClick={() => onSelect(thread.id)}
                    className={cn(
                      "w-full rounded-md px-2.5 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      isActive
                        ? "bg-surface-hover"
                        : "hover:bg-surface-hover/60",
                    )}
                  >
                    <span className="block truncate text-sm font-medium text-foreground">
                      {thread.title?.trim() || "Untitled chat"}
                    </span>
                    {thread.last_message_preview ? (
                      <span className="mt-0.5 block truncate text-xs text-foreground-muted">
                        {thread.last_message_preview}
                      </span>
                    ) : null}
                    <span className="mt-0.5 block text-xs text-foreground-subtle">
                      {formatRelativeDate(thread.updated_at)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </nav>
    </div>
  );
}
