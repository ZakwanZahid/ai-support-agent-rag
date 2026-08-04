import { MessagesSquare } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { formatRelativeDate } from "@/lib/utils";
import type { ChatThread } from "@/types/conversation";
import type { KnowledgeSpace } from "@/types/knowledge";

interface RecentChatThreadsProps {
  chatThreads: ChatThread[];
  knowledgeSpaces: KnowledgeSpace[];
  /** Chat is only reachable once something can actually be asked about. */
  canStartChat: boolean;
}

export function RecentChatThreads({
  chatThreads,
  knowledgeSpaces,
  canStartChat,
}: RecentChatThreadsProps) {
  // Resolve names locally so a thread row never has to show a raw id.
  const nameById = new Map(
    knowledgeSpaces.map((space) => [space.id, space.name]),
  );

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-foreground">
          Recent chats
        </h2>
        {chatThreads.length > 0 ? (
          <Button asChild size="sm" variant="ghost">
            <Link href="/dashboard/chat">Open chat</Link>
          </Button>
        ) : null}
      </CardHeader>

      <CardContent>
        {chatThreads.length === 0 ? (
          <div className="py-4">
            <p className="text-sm leading-6 text-foreground-muted">
              {canStartChat
                ? "No conversations yet. Start your first chat with your knowledge base."
                : "Your assistant is not ready yet. Upload and prepare at least one document before starting a chat."}
            </p>
            <Button asChild size="sm" className="mt-4">
              <Link
                href={
                  canStartChat ? "/dashboard/chat" : "/dashboard/knowledge"
                }
              >
                {canStartChat ? "Start chat" : "Add knowledge"}
              </Link>
            </Button>
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {chatThreads.map((thread) => (
              <li key={thread.id} className="py-3 first:pt-0 last:pb-0">
                <Link
                  href={`/dashboard/conversations/${thread.id}`}
                  className="flex items-start gap-3 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-border bg-surface-subtle text-foreground-subtle">
                    <MessagesSquare aria-hidden="true" className="size-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {thread.title?.trim() || "Untitled chat"}
                    </p>
                    {thread.last_message_preview ? (
                      <p className="mt-0.5 line-clamp-1 text-xs text-foreground-muted">
                        {thread.last_message_preview}
                      </p>
                    ) : null}
                    <p className="mt-0.5 text-xs text-foreground-subtle">
                      {thread.knowledge_base_id
                        ? `${nameById.get(thread.knowledge_base_id) ?? "Knowledge space"} · `
                        : ""}
                      {formatRelativeDate(thread.updated_at)}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
