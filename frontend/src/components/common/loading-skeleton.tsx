import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface LoadingSkeletonProps {
  rows?: number;
  variant?: "cards" | "list" | "detail";
  className?: string;
}

export function LoadingSkeleton({
  rows = 3,
  variant = "list",
  className,
}: LoadingSkeletonProps) {
  if (variant === "detail") {
    return (
      <div
        aria-label="Loading content"
        aria-busy="true"
        className={cn("space-y-6", className)}
      >
        <div className="space-y-3">
          <Skeleton className="h-8 w-52" />
          <Skeleton className="h-4 w-full max-w-xl" />
        </div>
        <Skeleton className="h-48 w-full" />
        <div className="space-y-3">
          {Array.from({ length: rows }).map((_, index) => (
            <Skeleton key={index} className="h-16 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (variant === "cards") {
    return (
      <div
        aria-label="Loading content"
        aria-busy="true"
        className={cn(
          "grid gap-4 sm:grid-cols-2 xl:grid-cols-3",
          className,
        )}
      >
        {Array.from({ length: rows }).map((_, index) => (
          <div
            key={index}
            className="space-y-4 rounded-lg border border-zinc-200 bg-white p-5"
          >
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      aria-label="Loading content"
      aria-busy="true"
      className={cn(
        "divide-y divide-zinc-100 rounded-lg border border-zinc-200 bg-white",
        className,
      )}
    >
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex items-center gap-4 p-4 sm:p-5">
          <Skeleton className="size-10 shrink-0" />
          <div className="min-w-0 flex-1 space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-2/3" />
          </div>
        </div>
      ))}
    </div>
  );
}
