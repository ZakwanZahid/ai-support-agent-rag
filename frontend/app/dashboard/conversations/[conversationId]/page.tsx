"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ChatMessage } from "@/components/chat/chat-message";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/hooks/use-workspace";
import { getConversation } from "@/lib/api/conversations";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";

export default function ChatThreadDetailPage() {
  const params = useParams<{ conversationId: string }>();
  const threadId = params.conversationId;
  const { activeWorkspace } = useWorkspace();
  const workspaceId = activeWorkspace?.id ?? null;

  const threadQuery = useQuery({
    queryKey: queryKeys.conversation(workspaceId, threadId),
    queryFn: () => getConversation(workspaceId!, threadId),
    enabled: Boolean(workspaceId && threadId),
  });

  const knowledgeSpacesQuery = useQuery({
    queryKey: queryKeys.knowledgeBases(workspaceId),
    queryFn: () => listKnowledgeBases(workspaceId!),
    enabled: Boolean(workspaceId),
  });

  const thread = threadQuery.data;
  const knowledgeSpace = (knowledgeSpacesQuery.data ?? []).find(
    (space) => space.id === thread?.knowledge_base_id,
  );

  const backLink = (
    <Button asChild size="sm" variant="ghost" className="-ml-2">
      <Link href="/dashboard/conversations">
        <ArrowLeft aria-hidden="true" />
        Chat threads
      </Link>
    </Button>
  );

  if (threadQuery.isPending) {
    return (
      <div className="space-y-6">
        {backLink}
        <LoadingSkeleton variant="detail" rows={3} />
      </div>
    );
  }

  if (threadQuery.isError || !thread) {
    return (
      <div className="space-y-6">
        {backLink}
        <ErrorState
          title="We couldn’t load this chat"
          message="It may have been removed, or the API may be unavailable."
          onRetry={() => void threadQuery.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {backLink}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            {thread.title?.trim() || "Untitled chat"}
          </h1>
          <p className="mt-1.5 text-sm text-foreground-subtle">
            {knowledgeSpace ? `${knowledgeSpace.name} · ` : ""}
            Started {formatDate(thread.created_at)}
          </p>
        </div>

        {knowledgeSpace ? (
          <Button asChild className="shrink-0">
            <Link
              href={`/dashboard/chat?knowledgeSpace=${encodeURIComponent(
                knowledgeSpace.id,
              )}`}
            >
              <Sparkles aria-hidden="true" />
              Continue in chat
            </Link>
          </Button>
        ) : null}
      </div>

      {thread.messages.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border-strong bg-surface px-5 py-10 text-center text-sm text-foreground-muted">
          This chat has no messages yet.
        </p>
      ) : (
        <div className="space-y-6 rounded-lg border border-border bg-surface p-4 sm:p-6">
          {thread.messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
        </div>
      )}
    </div>
  );
}
