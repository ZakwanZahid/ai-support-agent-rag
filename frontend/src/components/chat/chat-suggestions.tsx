import { Sparkles } from "lucide-react";

/**
 * Deliberately generic. Suggesting "What is the refund policy?" to someone
 * whose documents are engineering runbooks would be a guess dressed up as a
 * recommendation, so these prompt shapes work against any content.
 */
const SUGGESTIONS = [
  "What does this document cover?",
  "Summarize the key points.",
  "What is the policy on refunds?",
] as const;

interface ChatSuggestionsProps {
  knowledgeSpaceName?: string | null;
  onSelect: (prompt: string) => void;
}

export function ChatSuggestions({
  knowledgeSpaceName,
  onSelect,
}: ChatSuggestionsProps) {
  return (
    <div className="mx-auto max-w-lg px-4 py-10 text-center">
      <span className="mx-auto mb-4 flex size-10 items-center justify-center rounded-md border border-border bg-surface text-foreground-muted">
        <Sparkles aria-hidden="true" className="size-4" />
      </span>

      <h2 className="text-base font-semibold text-foreground">
        Ask about {knowledgeSpaceName?.trim() || "your documents"}
      </h2>
      <p className="mt-2 text-sm leading-6 text-foreground-muted">
        Answers come from the documents in this knowledge space, and each one
        shows the passages it used.
      </p>

      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onSelect(prompt)}
            className="rounded-full border border-border bg-surface px-3 py-1.5 text-xs text-foreground-muted transition-colors hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
