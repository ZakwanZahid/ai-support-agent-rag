"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, MessagesSquare } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ConversationThread } from "@/components/chat/conversation-thread";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader } from "@/components/common/page-header";
import { Button } from "@/components/ui/button";
import { getAPIErrorMessage } from "@/lib/api/client";
import {
  getConversation,
  sendChatMessage,
} from "@/lib/api/conversations";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";
import { useWorkspace } from "@/hooks/use-workspace";

export default function ConversationDetailPage() {
  const params = useParams<{ conversationId: string }>();
  const conversationId = params.conversationId;
  const { activeWorkspace } = useWorkspace();
  const organizationId = activeWorkspace?.id;
  const queryClient = useQueryClient();
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);

  const conversationQuery = useQuery({
    queryKey: queryKeys.conversation(organizationId, conversationId),
    queryFn: () => getConversation(organizationId!, conversationId),
    enabled: Boolean(organizationId),
  });
  const knowledgeBasesQuery = useQuery({
    queryKey: queryKeys.knowledgeBases(organizationId),
    queryFn: () => listKnowledgeBases(organizationId!),
    enabled: Boolean(organizationId),
  });

  const knowledgeBaseId = conversationQuery.data?.knowledge_base_id;
  const sendMutation = useMutation({
    mutationFn: (question: string) =>
      sendChatMessage(organizationId!, conversationId, {
        question,
        knowledge_base_id: knowledgeBaseId!,
      }),
    onMutate: (question) => setPendingQuestion(question),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.conversation(organizationId, conversationId),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.conversations(organizationId),
        }),
      ]);
    },
    onError: (error) => toast.error(getAPIErrorMessage(error)),
    onSettled: () => setPendingQuestion(null),
  });

  if (!activeWorkspace) {
    return (
      <EmptyState
        icon={MessagesSquare}
        title="Select an organization"
        description="The conversation must be opened inside its organization."
      />
    );
  }

  if (conversationQuery.isPending || knowledgeBasesQuery.isPending) {
    return <LoadingSkeleton variant="detail" rows={4} />;
  }

  if (conversationQuery.isError || knowledgeBasesQuery.isError) {
    return (
      <ErrorState
        title="Conversation could not be loaded"
        message={getAPIErrorMessage(
          conversationQuery.error ?? knowledgeBasesQuery.error,
        )}
        onRetry={() => {
          void conversationQuery.refetch();
          void knowledgeBasesQuery.refetch();
        }}
      />
    );
  }

  const knowledgeBase = knowledgeBasesQuery.data.find(
    (item) => item.id === conversationQuery.data.knowledge_base_id,
  );

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow={knowledgeBase?.name ?? "Saved conversation"}
        title={conversationQuery.data.title || "Untitled conversation"}
        description={`Started ${formatDate(conversationQuery.data.created_at)}. Continue asking questions against the same tenant-scoped knowledge base.`}
        actions={
          <Button asChild variant="outline">
            <Link
              href={
                knowledgeBaseId
                  ? `/dashboard/chat?knowledgeBaseId=${encodeURIComponent(knowledgeBaseId)}`
                  : "/dashboard/chat"
              }
            >
              <ArrowLeft aria-hidden="true" />
              Back to chat
            </Link>
          </Button>
        }
      />

      {!knowledgeBaseId ? (
        <ErrorState
          title="This conversation has no knowledge base"
          message="Start a new conversation with a selected knowledge base to continue chatting."
          action={
            <Button asChild>
              <Link href="/dashboard/chat">Start new conversation</Link>
            </Button>
          }
        />
      ) : (
        <ConversationThread
          messages={conversationQuery.data.messages}
          onSend={async (question) => {
            await sendMutation.mutateAsync(question);
          }}
          sending={sendMutation.isPending}
          pendingQuestion={pendingQuestion}
        />
      )}
    </div>
  );
}
