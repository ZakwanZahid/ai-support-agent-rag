"use client";

import { useQuery } from "@tanstack/react-query";
import { MessagesSquare } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader } from "@/components/common/page-header";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/hooks/use-workspace";
import { listConversations } from "@/lib/api/conversations";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import { formatRelativeDate } from "@/lib/utils";

export default function ChatThreadsPage() {
  const { activeWorkspace } = useWorkspace();
  const workspaceId = activeWorkspace?.id ?? null;
  const enabled = Boolean(workspaceId);

  const threadsQuery = useQuery({
    queryKey: queryKeys.conversations(workspaceId),
    queryFn: () => listConversations(workspaceId!),
    enabled,
  });

  const knowledgeSpacesQuery = useQuery({
    queryKey: queryKeys.knowledgeBases(workspaceId),
    queryFn: () => listKnowledgeBases(workspaceId!),
    enabled,
  });

  const threads = threadsQuery.data ?? [];
  const nameById = new Map(
    (knowledgeSpacesQuery.data ?? []).map((space) => [space.id, space.name]),
  );

  return (
    <div className="space-y-7">
      <PageHeader
        title="Chat threads"
        description="Every conversation you’ve had, with the sources behind each answer."
        actions={
          threads.length > 0 ? (
            <Button asChild>
              <Link href="/dashboard/chat">New chat</Link>
            </Button>
          ) : undefined
        }
      />

      {threadsQuery.isPending ? (
        <LoadingSkeleton rows={4} />
      ) : threadsQuery.isError ? (
        <ErrorState
          title="We couldn’t load your chats"
          onRetry={() => void threadsQuery.refetch()}
        />
      ) : threads.length === 0 ? (
        <EmptyState
          icon={MessagesSquare}
          title="No conversations yet"
          description="Start your first chat with your knowledge base."
          action={
            <Button asChild>
              <Link href="/dashboard/chat">Start chat</Link>
            </Button>
          }
        />
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border bg-surface">
          {threads.map((thread) => (
            <li key={thread.id}>
              <Link
                href={`/dashboard/conversations/${thread.id}`}
                className="flex items-start gap-3 p-4 transition-colors hover:bg-surface-hover/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md border border-border bg-surface-subtle text-foreground-subtle">
                  <MessagesSquare aria-hidden="true" className="size-4" />
                </span>

                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">
                    {thread.title?.trim() || "Untitled chat"}
                  </p>
                  {thread.last_message_preview ? (
                    <p className="mt-0.5 line-clamp-2 text-sm leading-6 text-foreground-muted">
                      {thread.last_message_preview}
                    </p>
                  ) : null}
                  <p className="mt-1 text-xs text-foreground-subtle">
                    {thread.knowledge_base_id
                      ? `${nameById.get(thread.knowledge_base_id) ?? "Knowledge space"} · `
                      : ""}
                    {thread.message_count
                      ? `${thread.message_count} ${
                          thread.message_count === 1 ? "message" : "messages"
                        } · `
                      : ""}
                    Started {formatRelativeDate(thread.created_at)}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
