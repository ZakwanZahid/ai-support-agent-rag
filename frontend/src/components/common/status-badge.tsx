import { Circle } from "lucide-react";

import { Badge, type badgeVariants } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { VariantProps } from "class-variance-authority";

type BadgeVariant = VariantProps<typeof badgeVariants>["variant"];

const statusMap: Record<
  string,
  { label: string; variant: BadgeVariant; dotClassName: string }
> = {
  pending: {
    label: "Pending",
    variant: "secondary",
    dotClassName: "fill-zinc-400 text-zinc-400",
  },
  uploaded: {
    label: "Uploaded",
    variant: "info",
    dotClassName: "fill-blue-500 text-blue-500",
  },
  processing: {
    label: "Processing",
    variant: "warning",
    dotClassName: "fill-amber-500 text-amber-500",
  },
  processed: {
    label: "Processed",
    variant: "info",
    dotClassName: "fill-blue-500 text-blue-500",
  },
  indexing: {
    label: "Indexing",
    variant: "warning",
    dotClassName: "fill-amber-500 text-amber-500",
  },
  indexed: {
    label: "Indexed",
    variant: "success",
    dotClassName: "fill-emerald-500 text-emerald-500",
  },
  failed: {
    label: "Failed",
    variant: "danger",
    dotClassName: "fill-red-500 text-red-500",
  },
};

interface StatusBadgeProps {
  status?: string | null;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const normalizedStatus = status?.toLowerCase().trim() || "pending";
  const config = statusMap[normalizedStatus] ?? {
    label: normalizedStatus.replaceAll("_", " "),
    variant: "outline" as const,
    dotClassName: "fill-zinc-400 text-zinc-400",
  };

  return (
    <Badge
      variant={config.variant}
      className={cn("gap-1.5 capitalize", className)}
    >
      <Circle
        aria-hidden="true"
        className={cn("size-1.5", config.dotClassName)}
      />
      {config.label}
    </Badge>
  );
}
