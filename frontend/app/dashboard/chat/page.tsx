"use client";

import { BookOpen, LoaderCircle, MessagesSquare } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef } from "react";

import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessage } from "@/components/chat/chat-message";
import { ChatSuggestions } from "@/components/chat/chat-suggestions";
import { KnowledgeSpaceSelect } from "@/components/chat/knowledge-space-select";
import { SourcesPanel } from "@/components/chat/sources-panel";
import { ThreadList } from "@/components/chat/thread-list";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { Button } from "@/components/ui/button";
import { useChat } from "@/hooks/use-chat";
import { useWorkspace } from "@/hooks/use-workspace";

/** Height of the app top bar, so chat can fill exactly what remains. */
const CHAT_HEIGHT = "h-[calc(100dvh-4rem)]";

function ChatWorkspace() {
  const searchParams = useSearchParams();
  const { activeWorkspace } = useWorkspace();
  const chat = useChat({
    workspaceId: activeWorkspace?.id ?? null,
    requestedKnowledgeSpaceId: searchParams.get("knowledgeSpace"),
  });

  const scrollRef = useRef<HTMLDivElement>(null);

  // Keep the newest message in view as the thread grows.
  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;
    container.scrollTop = container.scrollHeight;
  }, [chat.messages.length, chat.pendingQuestion, chat.threadId]);

  if (chat.isLoading) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-10">
        <LoadingSkeleton variant="detail" rows={3} />
      </div>
    );
  }

  if (chat.isError) {
    return (
      <div className="mx-auto w-full max-w-xl px-4 py-10">
        <ErrorState
          title="We couldn’t load your chats"
          onRetry={chat.refetch}
        />
      </div>
    );
  }

  if (chat.knowledgeSpaces.length === 0) {
    return (
      <div className="mx-auto w-full max-w-2xl px-4 py-10">
        <EmptyState
          icon={BookOpen}
          title="No knowledge spaces yet"
          description="Create your first knowledge space to organize documents for your AI assistant."
          action={
            <Button asChild>
              <Link href="/dashboard/knowledge">Create knowledge space</Link>
            </Button>
          }
        />
      </div>
    );
  }

  if (chat.answerableSpaces.length === 0) {
    return (
      <div className="mx-auto w-full max-w-2xl px-4 py-10">
        <EmptyState
          icon={MessagesSquare}
          title="Your assistant is not ready yet"
          description="Upload and prepare at least one document before starting a chat."
          action={
            <Button asChild>
              <Link href="/dashboard/knowledge">Add knowledge</Link>
            </Button>
          }
        />
      </div>
    );
  }

  const hasMessages = chat.messages.length > 0 || Boolean(chat.pendingQuestion);

  return (
    <div className={`flex ${CHAT_HEIGHT} min-h-0`}>
      {/* Thread list: desktop only. On smaller screens the Chat threads page
          covers the same ground without stealing width from the conversation. */}
      <div className="hidden w-64 shrink-0 border-r border-border xl:flex xl:flex-col">
        <ThreadList
          threads={chat.threads}
          activeThreadId={chat.threadId}
          onSelect={chat.selectThread}
          onNewThread={chat.startNewThread}
        />
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
          <KnowledgeSpaceSelect
            className="w-full max-w-64"
            knowledgeSpaces={chat.answerableSpaces}
            value={chat.knowledgeSpaceId}
            onChange={chat.selectKnowledgeSpace}
          />
          <div className="flex-1" />
          <Button
            size="sm"
            variant="secondary"
            className="xl:hidden"
            onClick={chat.startNewThread}
          >
            New chat
          </Button>
          <Button asChild size="sm" variant="ghost" className="hidden sm:flex">
            <Link href="/dashboard/conversations">All chats</Link>
          </Button>
        </div>

        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
          {chat.isThreadLoading ? (
            <div className="mx-auto w-full max-w-3xl px-4 py-8">
              <LoadingSkeleton rows={2} />
            </div>
          ) : hasMessages ? (
            <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-6">
              {chat.hasEarlierMessages ? (
                <div className="flex justify-center">
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={chat.isLoadingEarlierMessages}
                    onClick={chat.loadEarlierMessages}
                  >
                    {chat.isLoadingEarlierMessages ? (
                      <LoaderCircle aria-hidden="true" className="animate-spin" />
                    ) : null}
                    Load earlier messages
                  </Button>
                </div>
              ) : null}

              {chat.messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  // Sources stay in the markup and are hidden on wide screens,
                  // where the side panel shows them instead.
                  className="xl:[&_details]:hidden"
                />
              ))}

              {chat.pendingQuestion ? (
                <>
                  <ChatMessage
                    message={{ role: "user", content: chat.pendingQuestion }}
                  />
                  <ChatMessage message={{ role: "assistant", content: "" }} pending />
                </>
              ) : null}
            </div>
          ) : (
            <ChatSuggestions
              knowledgeSpaceName={chat.activeKnowledgeSpace?.name}
              onSelect={chat.ask}
            />
          )}
        </div>

        <div className="border-t border-border p-3 sm:p-4">
          <div className="mx-auto w-full max-w-3xl">
            <ChatInput
              onSubmit={chat.ask}
              isSending={chat.isSending}
              disabled={chat.isSending || !chat.knowledgeSpaceId}
            />
          </div>
        </div>
      </div>

      <SourcesPanel
        className="hidden w-80 shrink-0 xl:flex"
        sources={chat.latestAnswer?.citations ?? []}
      />
    </div>
  );
}

export default function ChatPage() {
  // useSearchParams needs a Suspense boundary for this route to prerender.
  return (
    <Suspense
      fallback={
        <div className="mx-auto w-full max-w-3xl px-4 py-10">
          <LoadingSkeleton variant="detail" rows={3} />
        </div>
      }
    >
      <ChatWorkspace />
    </Suspense>
  );
}
