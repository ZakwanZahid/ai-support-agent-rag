import { FileText, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * A static illustration of an answer with its sources.
 *
 * Deliberately labelled as an example: it is drawn, not fetched, and should
 * never be mistaken for live product state.
 */
const exampleSources = [
  {
    title: "Refund Policy.pdf",
    quote:
      "Customers may request a full refund within 30 days of delivery, provided the item is unused and in its original packaging.",
  },
  {
    title: "Support Handbook.md",
    quote:
      "Refund requests are reviewed within two business days. Approved refunds return to the original payment method.",
  },
];

export function ProductPreview({ className }: { className?: string }) {
  return (
    <figure
      className={cn(
        "overflow-hidden rounded-xl border border-border bg-surface shadow-sm",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="flex size-6 items-center justify-center rounded bg-primary text-primary-foreground">
            <Sparkles aria-hidden="true" className="size-3.5" />
          </span>
          <span className="text-sm font-medium text-foreground">Ask AI</span>
        </div>
        <span className="rounded-full border border-border bg-surface-subtle px-2 py-0.5 text-[11px] font-medium text-foreground-subtle">
          Example
        </span>
      </div>

      <div className="space-y-5 p-4 sm:p-6">
        <div className="flex justify-end">
          <p className="max-w-[85%] rounded-lg rounded-br-sm bg-primary px-3.5 py-2.5 text-sm text-primary-foreground">
            What is the refund policy?
          </p>
        </div>

        <div className="space-y-4">
          <p className="max-w-[92%] text-sm leading-6 text-foreground">
            Customers can request a full refund within 30 days of delivery, as
            long as the item is unused and in its original packaging. Requests
            are reviewed within two business days, and approved refunds go back
            to the original payment method.
          </p>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-foreground-subtle">
              Sources
            </p>
            <ul className="grid gap-2 sm:grid-cols-2">
              {exampleSources.map((source) => (
                <li
                  key={source.title}
                  className="rounded-lg border border-border bg-surface-subtle p-3"
                >
                  <p className="flex items-center gap-1.5 text-xs font-medium text-foreground">
                    <FileText
                      aria-hidden="true"
                      className="size-3.5 shrink-0 text-foreground-subtle"
                    />
                    <span className="truncate">{source.title}</span>
                  </p>
                  <p className="mt-1.5 line-clamp-3 text-xs leading-5 text-foreground-muted">
                    {source.quote}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <figcaption className="sr-only">
        An example answer about a refund policy, shown with the two source
        passages it was drawn from.
      </figcaption>
    </figure>
  );
}
