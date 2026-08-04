"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquarePlus, MessagesSquare } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { toast } from "sonner";

import { ConversationThread } from "@/components/chat/conversation-thread";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader } from "@/components/common/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { getAPIErrorMessage } from "@/lib/api/client";
import {
  createConversation,
  getConversation,
  listConversations,
  sendChatMessage,
} from "@/lib/api/conversations";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import { useWorkspace } from "@/hooks/use-workspace";

function ChatWorkspace() {
  const searchParams = useSearchParams();
  const requestedKnowledgeBaseId = searchParams.get("knowledgeBaseId");
  const { activeWorkspace } = useWorkspace();
  const organizationId = activeWorkspace?.id;
  const queryClient = useQueryClient();
  const [knowledgeBaseSelection, setKnowledgeBaseSelection] = useState("");
  const [conversationSelection, setConversationSelection] = useState("");
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);

  const knowledgeBasesQuery = useQuery({
    queryKey: queryKeys.knowledgeBases(organizationId),
    queryFn: () => listKnowledgeBases(organizationId!),
    enabled: Boolean(organizationId),
  });
  const conversationsQuery = useQuery({
    queryKey: queryKeys.conversations(organizationId),
    queryFn: () => listConversations(organizationId!),
    enabled: Boolean(organizationId),
  });
  const knowledgeBases = knowledgeBasesQuery.data ?? [];
  const knowledgeBaseId = knowledgeBases.some(
    (knowledgeBase) => knowledgeBase.id === knowledgeBaseSelection,
  )
    ? knowledgeBaseSelection
    : knowledgeBases.some(
          (knowledgeBase) => knowledgeBase.id === requestedKnowledgeBaseId,
        )
      ? requestedKnowledgeBaseId!
      : (knowledgeBases[0]?.id ?? "");

  const matchingConversations = useMemo(
    () =>
      (conversationsQuery.data ?? []).filter(
        (conversation) => conversation.knowledge_base_id === knowledgeBaseId,
      ),
    [conversationsQuery.data, knowledgeBaseId],
  );

  const conversationId = matchingConversations.some(
    (conversation) => conversation.id === conversationSelection,
  )
    ? conversationSelection
    : "";
  const conversationQuery = useQuery({
    queryKey: queryKeys.conversation(organizationId, conversationId),
    queryFn: () => getConversation(organizationId!, conversationId),
    enabled: Boolean(organizationId && conversationId),
  });

  const createMutation = useMutation({
    mutationFn: () => {
      const knowledgeBase = knowledgeBasesQuery.data?.find(
        (item) => item.id === knowledgeBaseId,
      );
      return createConversation(organizationId!, {
        knowledge_base_id: knowledgeBaseId,
        title: knowledgeBase ? `${knowledgeBase.name} conversation` : "Support conversation",
      });
    },
    onSuccess: async (conversation) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.conversations(organizationId),
      });
      setConversationSelection(conversation.id);
      toast.success("Conversation started.");
    },
    onError: (error) => toast.error(getAPIErrorMessage(error)),
  });

  const sendMutation = useMutation({
    mutationFn: (question: string) =>
      sendChatMessage(organizationId!, conversationId, {
        question,
        knowledge_base_id: knowledgeBaseId,
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
        description="Chat conversations are always scoped to an organization and knowledge base."
      />
    );
  }

  if (knowledgeBasesQuery.isPending || conversationsQuery.isPending) {
    return <LoadingSkeleton variant="detail" rows={4} />;
  }

  if (knowledgeBasesQuery.isError || conversationsQuery.isError) {
    return (
      <ErrorState
        onRetry={() => {
          void knowledgeBasesQuery.refetch();
          void conversationsQuery.refetch();
        }}
      />
    );
  }

  if (knowledgeBasesQuery.data.length === 0) {
    return (
      <EmptyState
        icon={MessagesSquare}
        title="Create a knowledge base first"
        description="Chat needs an indexed source collection before it can retrieve grounded context."
        action={
          <Button asChild>
            <Link href="/dashboard/knowledge">Create knowledge base</Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="RAG chat"
        title="Ask your support knowledge"
        description="Every answer is generated from retrieved chunks and returned with source citations."
        actions={
          conversationId ? (
            <Button asChild variant="outline">
              <Link href={`/dashboard/conversations/${conversationId}`}>
                Open saved conversation
              </Link>
            </Button>
          ) : undefined
        }
      />

      <div className="grid gap-5 xl:grid-cols-[19rem_minmax(0,1fr)]">
        <Card className="h-fit">
          <CardHeader>
            <h2 className="text-base font-semibold text-foreground">
              Conversation setup
            </h2>
            <p className="text-sm leading-6 text-foreground-muted">
              Choose the source boundary, then start or resume a conversation.
            </p>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <label
                htmlFor="chat-knowledge-base"
                className="text-sm font-medium text-foreground"
              >
                Knowledge base
              </label>
              <select
                id="chat-knowledge-base"
                value={knowledgeBaseId}
                onChange={(event) => {
                  setKnowledgeBaseSelection(event.target.value);
                  setConversationSelection("");
                }}
                className="h-10 w-full rounded-md border border-border-strong bg-white px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/10"
              >
                {knowledgeBasesQuery.data.map((knowledgeBase) => (
                  <option key={knowledgeBase.id} value={knowledgeBase.id}>
                    {knowledgeBase.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="conversation-selector"
                className="text-sm font-medium text-foreground"
              >
                Saved conversation
              </label>
              <select
                id="conversation-selector"
                value={conversationId}
                onChange={(event) =>
                  setConversationSelection(event.target.value)
                }
                className="h-10 w-full rounded-md border border-border-strong bg-white px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/10"
              >
                <option value="">Start a new conversation</option>
                {matchingConversations.map((conversation) => (
                  <option key={conversation.id} value={conversation.id}>
                    {conversation.title || "Untitled conversation"}
                  </option>
                ))}
              </select>
            </div>

            {!conversationId ? (
              <Button
                className="w-full"
                onClick={() => createMutation.mutate()}
                disabled={!knowledgeBaseId || createMutation.isPending}
              >
                <MessageSquarePlus aria-hidden="true" />
                {createMutation.isPending ? "Starting..." : "Start conversation"}
              </Button>
            ) : null}
          </CardContent>
        </Card>

        <div className="min-w-0">
          {conversationId && conversationQuery.isPending ? (
            <LoadingSkeleton variant="detail" rows={3} />
          ) : conversationId && conversationQuery.isError ? (
            <ErrorState onRetry={() => void conversationQuery.refetch()} />
          ) : (
            <ConversationThread
              messages={conversationQuery.data?.messages ?? []}
              onSend={async (question) => {
                await sendMutation.mutateAsync(question);
              }}
              sending={sendMutation.isPending}
              pendingQuestion={pendingQuestion}
              disabled={!conversationId}
              emptyTitle={
                conversationId
                  ? "Ask your first question"
                  : "Start or select a conversation"
              }
              emptyDescription={
                conversationId
                  ? "The assistant will answer only from indexed context in the selected knowledge base."
                  : "Choose a knowledge base and start a conversation before sending a question."
              }
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<LoadingSkeleton variant="detail" rows={4} />}>
      <ChatWorkspace />
    </Suspense>
  );
}
