/* eslint-disable @typescript-eslint/no-unused-vars -- every renderer below
   destructures out the `node` prop react-markdown injects, precisely so it is
   not spread onto the DOM; the project's lint config has no `_`-prefix
   exception for that pattern, and 16 inline disables would be noisier than
   one at the top of a file whose only job is this. */
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

/**
 * Renders an assistant answer as Markdown, styled to match the chat bubble.
 *
 * The model is asked to format in Markdown (see `GROUNDED_SUPPORT_SYSTEM_PROMPT`)
 * so lists and emphasis actually render as lists and emphasis instead of raw
 * `**` and `-` characters. `react-markdown` renders no raw HTML by default —
 * deliberately left that way rather than adding `rehype-raw`, since the
 * "Markdown" being rendered here ultimately originates from retrieved
 * document content the model was asked to answer from, not just the model's
 * own words. Not treating that as trusted HTML is the safer default.
 *
 * Every renderer below destructures `node` out before spreading the rest onto
 * the DOM element. `react-markdown` includes it in the props object it hands
 * a custom component; spreading it unfiltered writes a `node="[object
 * Object]"` attribute onto real DOM nodes.
 */

const components: Components = {
  p: ({ node: _node, className, ...props }) => (
    <p
      className={cn("leading-7 [&:not(:first-child)]:mt-3", className)}
      {...props}
    />
  ),
  strong: ({ node: _node, className, ...props }) => (
    <strong className={cn("font-semibold text-foreground", className)} {...props} />
  ),
  a: ({ node: _node, className, ...props }) => (
    <a
      className={cn(
        "font-medium text-foreground underline underline-offset-2 hover:text-foreground-muted",
        className,
      )}
      target="_blank"
      rel="noopener noreferrer"
      {...props}
    />
  ),
  ul: ({ node: _node, className, ...props }) => (
    <ul
      className={cn("mt-3 list-disc space-y-1.5 pl-5 first:mt-0", className)}
      {...props}
    />
  ),
  ol: ({ node: _node, className, ...props }) => (
    <ol
      className={cn("mt-3 list-decimal space-y-1.5 pl-5 first:mt-0", className)}
      {...props}
    />
  ),
  li: ({ node: _node, className, ...props }) => (
    <li className={cn("leading-6 marker:text-foreground-subtle", className)} {...props} />
  ),
  h1: ({ node: _node, className, ...props }) => (
    <h2
      className={cn(
        "mt-4 text-base font-semibold text-foreground first:mt-0",
        className,
      )}
      {...props}
    />
  ),
  h2: ({ node: _node, className, ...props }) => (
    <h3
      className={cn(
        "mt-4 text-sm font-semibold text-foreground first:mt-0",
        className,
      )}
      {...props}
    />
  ),
  h3: ({ node: _node, className, ...props }) => (
    <h4
      className={cn(
        "mt-3 text-sm font-semibold text-foreground first:mt-0",
        className,
      )}
      {...props}
    />
  ),
  blockquote: ({ node: _node, className, ...props }) => (
    <blockquote
      className={cn(
        "mt-3 border-l-2 border-border-strong pl-3 text-foreground-muted first:mt-0",
        className,
      )}
      {...props}
    />
  ),
  code: ({ node: _node, className, ...props }) => (
    <code
      className={cn(
        "rounded bg-surface-hover px-1.5 py-0.5 font-mono text-[0.85em] text-foreground",
        className,
      )}
      {...props}
    />
  ),
  pre: ({ node: _node, className, ...props }) => (
    <pre
      className={cn(
        "mt-3 overflow-x-auto rounded-md border border-border bg-surface-hover p-3 text-[0.85em] first:mt-0",
        className,
      )}
      {...props}
    />
  ),
  hr: ({ node: _node, className, ...props }) => (
    <hr className={cn("my-4 border-border", className)} {...props} />
  ),
  table: ({ node: _node, className, ...props }) => (
    <div className="mt-3 overflow-x-auto first:mt-0">
      <table className={cn("w-full border-collapse text-left", className)} {...props} />
    </div>
  ),
  th: ({ node: _node, className, ...props }) => (
    <th
      className={cn(
        "border-b border-border py-1.5 pr-4 font-medium text-foreground-muted",
        className,
      )}
      {...props}
    />
  ),
  td: ({ node: _node, className, ...props }) => (
    <td className={cn("border-b border-border py-1.5 pr-4", className)} {...props} />
  ),
};

interface MarkdownAnswerProps {
  content: string;
  className?: string;
}

export function MarkdownAnswer({ content, className }: MarkdownAnswerProps) {
  return (
    <div className={cn("text-sm text-foreground", className)}>
      <Markdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </Markdown>
    </div>
  );
}
