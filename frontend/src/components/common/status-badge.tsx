import { Circle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { describeDocumentStatus, type StatusTone } from "@/lib/terminology";
import { cn } from "@/lib/utils";

const TONE_TO_VARIANT = {
  neutral: "secondary",
  info: "info",
  warning: "warning",
  success: "success",
  danger: "danger",
} as const satisfies Record<
  StatusTone,
  "secondary" | "info" | "warning" | "success" | "danger"
>;

const TONE_TO_DOT = {
  neutral: "fill-foreground-subtle text-foreground-subtle",
  info: "fill-info text-info",
  warning: "fill-warning text-warning",
  success: "fill-success text-success",
  danger: "fill-danger text-danger",
} as const satisfies Record<StatusTone, string>;

interface StatusBadgeProps {
  /** Raw backend status; translated to product language before rendering. */
  status?: string | null;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const { label, tone } = describeDocumentStatus(status);

  return (
    <Badge variant={TONE_TO_VARIANT[tone]} className={cn("gap-1.5", className)}>
      <Circle
        aria-hidden="true"
        className={cn("size-1.5", TONE_TO_DOT[tone])}
      />
      {label}
    </Badge>
  );
}
