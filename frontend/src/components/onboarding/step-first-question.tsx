"use client";

import { useMutation } from "@tanstack/react-query";
import { ArrowRight, FileText, LoaderCircle, Send } from "lucide-react";
import { useState } from "react";

import { MarkdownAnswer } from "@/components/chat/markdown-answer";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getAPIErrorMessage } from "@/lib/api/client";
import { createConversation, sendChatMessage } from "@/lib/api/conversations";
import type { AskResponse } from "@/types/conversation";

const SAMPLE_PROMPTS = [
  "What is the refund policy?",
  "How long does shipping take?",
  "Summarize the key points of this document.",
] as const;

interface StepFirstQuestionProps {
  workspaceId: string;
  knowledgeSpaceId: string;
  documentTitle?: string | null;
  onFinish: () => void;
}

export function StepFirstQuestion({
  workspaceId,
  knowledgeSpaceId,
  documentTitle,
  onFinish,
}: StepFirstQuestionProps) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskResponse | null>(null);

  const askMutation = useMutation({
    mutationFn: async (text: string) => {
      // Conversations are created implicitly; the user never sees this step.
      const conversation = await createConversation(workspaceId, {
        title: text.slice(0, 80),
        knowledge_base_id: knowledgeSpaceId,
      });
      return sendChatMessage(workspaceId, conversation.id, {
        question: text,
        knowledge_base_id: knowledgeSpaceId,
      });
    },
    onSuccess: setAnswer,
  });

  const ask = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || askMutation.isPending) return;
    setQuestion(trimmed);
    setAnswer(null);
    askMutation.mutate(trimmed);
  };

  return (
    <div>
      <h2 className="text-2xl font-semibold tracking-[-0.02em] text-foreground">
        Ask your first question
      </h2>
      <p className="mt-2 text-sm leading-6 text-foreground-muted">
        {documentTitle
          ? `Your assistant has read ${documentTitle}. Ask it something.`
          : "Your assistant is ready. Ask it something about your document."}
      </p>

      <form
        className="mt-6 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          ask(question);
        }}
      >
        <Input
          aria-label="Your question"
          placeholder="What is the refund policy?"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          disabled={askMutation.isPending}
        />
        <Button type="submit" disabled={askMutation.isPending || !question.trim()}>
          {askMutation.isPending ? (
            <LoaderCircle aria-hidden="true" className="animate-spin" />
          ) : (
            <Send aria-hidden="true" />
          )}
          <span className="sr-only sm:not-sr-only">Ask</span>
        </Button>
      </form>

      {!answer && !askMutation.isPending ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {SAMPLE_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => ask(prompt)}
              className="rounded-full border border-border bg-surface px-3 py-1.5 text-xs text-foreground-muted transition-colors hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {prompt}
            </button>
          ))}
        </div>
      ) : null}

      {askMutation.isError ? (
        <Alert variant="destructive" className="mt-5">
          <AlertTitle>We couldn’t answer that</AlertTitle>
          <AlertDescription>
            {getAPIErrorMessage(askMutation.error)}
          </AlertDescription>
        </Alert>
      ) : null}

      {answer ? (
        <div className="mt-6 rounded-lg border border-border bg-surface p-5">
          <MarkdownAnswer content={answer.answer} />

          {answer.citations.length > 0 ? (
            <div className="mt-5">
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-foreground-subtle">
                Sources
              </p>
              <ul className="space-y-2">
                {answer.citations.map((source) => (
                  <li
                    key={source.chunk_id}
                    className="rounded-md border border-border bg-surface-subtle p-3"
                  >
                    <p className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                      <FileText
                        aria-hidden="true"
                        className="size-3.5 shrink-0 text-foreground-subtle"
                      />
                      <span className="truncate">{source.document_title}</span>
                    </p>
                    <p className="mt-1.5 line-clamp-3 text-xs leading-5 text-foreground-muted">
                      {source.quote}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="mt-8 flex flex-wrap gap-3">
        <Button size="lg" onClick={onFinish}>
          {answer ? "Go to dashboard" : "Skip for now"}
          <ArrowRight aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
