import { BookOpen, Sparkles, Upload } from "lucide-react";
import Link from "next/link";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface QuickActionsProps {
  /** Asking is pointless until at least one document is ready. */
  canAsk: boolean;
}

export function QuickActions({ canAsk }: QuickActionsProps) {
  const actions = [
    {
      label: "Add document",
      description: "Upload a policy, FAQ, or guide",
      href: "/dashboard/knowledge",
      icon: Upload,
      disabled: false,
    },
    {
      label: "Ask AI",
      description: canAsk
        ? "Ask a question about your documents"
        : "Prepare a document first",
      href: "/dashboard/chat",
      icon: Sparkles,
      disabled: !canAsk,
    },
    {
      label: "Create knowledge space",
      description: "Group related documents",
      href: "/dashboard/knowledge",
      icon: BookOpen,
      disabled: false,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <h2 className="text-base font-semibold text-foreground">
          Quick actions
        </h2>
      </CardHeader>
      <CardContent className="grid gap-2">
        {actions.map(({ label, description, href, icon: Icon, disabled }) => {
          const content = (
            <>
              <span
                className={cn(
                  "flex size-8 shrink-0 items-center justify-center rounded-md border border-border",
                  disabled
                    ? "bg-surface-subtle text-foreground-subtle/60"
                    : "bg-surface-subtle text-foreground-muted",
                )}
              >
                <Icon aria-hidden="true" className="size-4" />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium">{label}</span>
                <span className="block text-xs text-foreground-subtle">
                  {description}
                </span>
              </span>
            </>
          );

          if (disabled) {
            return (
              <span
                key={label}
                aria-disabled="true"
                className="flex cursor-not-allowed items-center gap-3 rounded-md border border-border p-3 text-foreground-subtle"
              >
                {content}
              </span>
            );
          }

          return (
            <Link
              key={label}
              href={href}
              className="flex items-center gap-3 rounded-md border border-border p-3 text-foreground transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {content}
            </Link>
          );
        })}
      </CardContent>
    </Card>
  );
}
