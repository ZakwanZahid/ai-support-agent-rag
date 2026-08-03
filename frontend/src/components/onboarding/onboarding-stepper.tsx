import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

export const ONBOARDING_STEPS = [
  { key: "workspace", label: "Workspace" },
  { key: "knowledge", label: "Knowledge space" },
  { key: "document", label: "First document" },
  { key: "question", label: "First question" },
] as const;

export type OnboardingStepKey = (typeof ONBOARDING_STEPS)[number]["key"];

interface OnboardingStepperProps {
  currentIndex: number;
  className?: string;
}

export function OnboardingStepper({
  currentIndex,
  className,
}: OnboardingStepperProps) {
  return (
    <nav aria-label="Setup progress" className={className}>
      <ol className="flex items-center gap-2 sm:gap-3">
        {ONBOARDING_STEPS.map((step, index) => {
          const isComplete = index < currentIndex;
          const isCurrent = index === currentIndex;

          return (
            <li key={step.key} className="flex min-w-0 flex-1 items-center gap-2">
              <span
                aria-current={isCurrent ? "step" : undefined}
                className={cn(
                  "flex size-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-medium",
                  isComplete && "border-primary bg-primary text-primary-foreground",
                  isCurrent && "border-primary text-foreground",
                  !isComplete &&
                    !isCurrent &&
                    "border-border text-foreground-subtle",
                )}
              >
                {isComplete ? (
                  <Check aria-hidden="true" className="size-3.5" />
                ) : (
                  index + 1
                )}
              </span>
              <span
                className={cn(
                  "hidden truncate text-xs font-medium sm:block",
                  isCurrent ? "text-foreground" : "text-foreground-subtle",
                )}
              >
                {step.label}
              </span>
              {index < ONBOARDING_STEPS.length - 1 ? (
                <span
                  aria-hidden="true"
                  className={cn(
                    "h-px flex-1",
                    isComplete ? "bg-primary" : "bg-border",
                  )}
                />
              ) : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
