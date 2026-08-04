import { ArrowRight, Check, Sparkles } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface SetupChecklistProps {
  hasKnowledgeSpace: boolean;
  hasDocument: boolean;
  hasReadyDocument: boolean;
  hasAskedSomething: boolean;
}

/**
 * Shown until setup is finished, then replaced by a short confirmation.
 * Each step links to the place that completes it, so the checklist is a
 * route into the product rather than a list of instructions.
 */
export function SetupChecklist({
  hasKnowledgeSpace,
  hasDocument,
  hasReadyDocument,
  hasAskedSomething,
}: SetupChecklistProps) {
  const steps = [
    {
      label: "Create a knowledge space",
      done: hasKnowledgeSpace,
      href: "/dashboard/knowledge",
      action: "Create one",
    },
    {
      label: "Add your first document",
      done: hasDocument,
      href: "/dashboard/knowledge",
      action: "Add knowledge",
    },
    {
      label: "Prepare a document for chat",
      done: hasReadyDocument,
      href: "/dashboard/documents",
      action: "Prepare",
    },
    {
      label: "Ask your first question",
      done: hasAskedSomething,
      href: "/dashboard/chat",
      action: "Ask AI",
    },
  ];

  const isComplete = steps.every((step) => step.done);

  if (isComplete) {
    return (
      <Card>
        <CardContent className="flex flex-wrap items-center gap-4 py-5">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-success-surface text-success">
            <Sparkles aria-hidden="true" className="size-[18px]" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-foreground">
              Your assistant is ready
            </p>
            <p className="mt-0.5 text-sm text-foreground-muted">
              It can answer from the documents you&rsquo;ve prepared.
            </p>
          </div>
          <Button asChild size="sm">
            <Link href="/dashboard/chat">
              Ask AI
              <ArrowRight aria-hidden="true" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  const completedCount = steps.filter((step) => step.done).length;
  const nextStepIndex = steps.findIndex((step) => !step.done);

  return (
    <Card>
      <CardContent className="py-5">
        <div className="mb-4 flex items-baseline justify-between gap-3">
          <p className="text-sm font-medium text-foreground">
            Finish setting up your assistant
          </p>
          <p className="text-xs text-foreground-subtle">
            {completedCount} of {steps.length} done
          </p>
        </div>

        <ol className="space-y-1">
          {steps.map((step, index) => (
            <li
              key={step.label}
              className="flex items-center gap-3 rounded-md py-1.5"
            >
              <span
                className={cn(
                  "flex size-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-medium",
                  step.done
                    ? "border-success bg-success text-primary-foreground"
                    : "border-border text-foreground-subtle",
                )}
              >
                {step.done ? (
                  <Check aria-hidden="true" className="size-3" />
                ) : (
                  index + 1
                )}
              </span>

              <span
                className={cn(
                  "min-w-0 flex-1 text-sm",
                  step.done
                    ? "text-foreground-subtle line-through"
                    : "text-foreground",
                )}
              >
                {step.label}
              </span>

              {/* Only the next incomplete step gets an action, so there is one
                  obvious thing to do rather than four competing links. */}
              {index === nextStepIndex ? (
                <Button asChild size="sm" variant="secondary">
                  <Link href={step.href}>{step.action}</Link>
                </Button>
              ) : null}
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
