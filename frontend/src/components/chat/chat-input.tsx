"use client";

import { LoaderCircle, Send } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSubmit: (question: string) => void | Promise<void>;
  disabled?: boolean;
  isSending?: boolean;
  placeholder?: string;
  className?: string;
}

export function ChatInput({
  onSubmit,
  disabled = false,
  isSending = false,
  placeholder = "Ask a question about your documents…",
  className,
}: ChatInputProps) {
  const [value, setValue] = useState("");

  async function submit() {
    const question = value.trim();
    if (!question || disabled || isSending) return;

    setValue("");
    try {
      await onSubmit(question);
    } catch {
      // The caller surfaces the error. Restoring the text means a failed send
      // does not cost the user their question.
      setValue(question);
    }
  }

  return (
    <form
      className={cn(
        "rounded-xl border border-border bg-surface p-2 focus-within:border-border-strong",
        className,
      )}
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <label htmlFor="chat-question" className="sr-only">
        Ask a question
      </label>
      <Textarea
        id="chat-question"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          // Enter sends; Shift+Enter is a newline. Standard for chat, and the
          // hint below says so for anyone who expects otherwise.
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void submit();
          }
        }}
        disabled={disabled}
        placeholder={placeholder}
        rows={1}
        className="max-h-40 min-h-11 resize-none border-0 bg-transparent px-2 py-2.5 shadow-none focus-visible:ring-0"
      />

      <div className="flex items-center justify-between gap-3 px-1 pb-0.5">
        <p className="hidden text-xs text-foreground-subtle sm:block">
          Enter to send · Shift + Enter for a new line
        </p>
        <Button
          type="submit"
          size="sm"
          className="ml-auto"
          disabled={!value.trim() || disabled || isSending}
        >
          {isSending ? (
            <LoaderCircle aria-hidden="true" className="animate-spin" />
          ) : (
            <Send aria-hidden="true" />
          )}
          {isSending ? "Answering" : "Send"}
        </Button>
      </div>
    </form>
  );
}
