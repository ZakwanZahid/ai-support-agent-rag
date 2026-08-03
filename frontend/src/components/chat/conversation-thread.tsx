"use client";

import { Info, MessageSquareText } from "lucide-react";
import { useEffect, useRef } from "react";

import { ChatInput } from "@/components/chat/chat-input";
import {
  ChatMessage,
  type ChatMessageData,
} from "@/components/chat/chat-message";
import { EmptyState } from "@/components/common/empty-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface ConversationThreadProps {
  messages: ChatMessageData[];
  onSend: (question: string) => void | Promise<void>;
  sending?: boolean;
  pendingQuestion?: string | null;
  disabled?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
}

function isNoContextAnswer(content: string) {
  const normalized = content.toLowerCase();
  return (
    normalized.includes("do not have enough information") ||
    normalized.includes("no relevant knowledge")
  );
}

export function ConversationThread({
  messages,
  onSend,
  sending = false,
  pendingQuestion,
  disabled = false,
  emptyTitle = "Ask your first question",
  emptyDescription = "Answers will be grounded in indexed documents and include source citations when context is available.",
}: ConversationThreadProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [messages.length, pendingQuestion, sending]);

  return (
    <div className="flex min-h-[34rem] flex-col overflow-hidden rounded-lg border border-zinc-200 bg-zinc-50">
      <div className="flex-1 space-y-6 overflow-y-auto px-4 py-5 sm:px-6 sm:py-6">
        {messages.length === 0 && !pendingQuestion ? (
          <EmptyState
            compact
            icon={MessageSquareText}
            title={emptyTitle}
            description={emptyDescription}
            className="min-h-64 bg-white"
          />
        ) : (
          messages.map((message) => (
            <div key={message.id}>
              <ChatMessage message={message} />
              {message.role === "assistant" &&
              isNoContextAnswer(message.content) ? (
                <Alert className="ml-11 mt-3 max-w-2xl">
                  <Info aria-hidden="true" />
                  <AlertTitle>More knowledge may be needed</AlertTitle>
                  <AlertDescription>
                    Check that relevant documents have reached the indexed
                    status, or add a source that answers this question.
                  </AlertDescription>
                </Alert>
              ) : null}
            </div>
          ))
        )}
        {pendingQuestion ? (
          <>
            <ChatMessage
              message={{ role: "user", content: pendingQuestion }}
            />
            <ChatMessage
              pending
              message={{ role: "assistant", content: "" }}
            />
          </>
        ) : null}
        <div ref={endRef} />
      </div>
      <div className="sticky bottom-0 border-t border-zinc-200 bg-white p-3 sm:p-4">
        <ChatInput
          onSubmit={onSend}
          loading={sending}
          disabled={disabled}
        />
      </div>
    </div>
  );
}
