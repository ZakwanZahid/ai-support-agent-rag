"use client";

import * as React from "react";
import { Loader2, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSubmit: (question: string) => void | Promise<void>;
  value?: string;
  onValueChange?: (value: string) => void;
  disabled?: boolean;
  loading?: boolean;
  placeholder?: string;
  className?: string;
}

export function ChatInput({
  onSubmit,
  value,
  onValueChange,
  disabled = false,
  loading = false,
  placeholder = "Ask a question about your support knowledge…",
  className,
}: ChatInputProps) {
  const [internalValue, setInternalValue] = React.useState("");
  const isControlled = value !== undefined;
  const currentValue = isControlled ? value : internalValue;

  function updateValue(nextValue: string) {
    if (!isControlled) setInternalValue(nextValue);
    onValueChange?.(nextValue);
  }

  async function submit() {
    const question = currentValue.trim();
    if (!question || disabled || loading) return;

    updateValue("");
    try {
      await onSubmit(question);
    } catch {
      // The calling mutation owns the user-facing error state. Keeping the
      // question here lets the user retry without retyping it.
      updateValue(question);
    }
  }

  return (
    <form
      className={cn(
        "rounded-lg border border-border bg-white p-2 focus-within:border-border-strong focus-within:ring-2 focus-within:ring-ring/5",
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
        value={currentValue}
        onChange={(event) => updateValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void submit();
          }
        }}
        disabled={disabled || loading}
        placeholder={placeholder}
        rows={2}
        className="min-h-20 resize-none border-0 px-2 py-2 shadow-none focus-visible:ring-0"
      />
      <div className="flex items-center justify-between gap-3 px-1 pb-1">
        <p className="hidden text-xs text-foreground-subtle sm:block">
          Enter to send · Shift + Enter for a new line
        </p>
        <Button
          type="submit"
          size="sm"
          disabled={!currentValue.trim() || disabled || loading}
          className="ml-auto"
        >
          {loading ? (
            <Loader2 aria-hidden="true" className="animate-spin" />
          ) : (
            <Send aria-hidden="true" />
          )}
          {loading ? "Generating" : "Send"}
        </Button>
      </div>
    </form>
  );
}
