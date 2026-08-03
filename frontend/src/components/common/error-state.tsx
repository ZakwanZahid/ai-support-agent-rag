import * as React from "react";
import { AlertCircle } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  action?: React.ReactNode;
  className?: string;
}

export function ErrorState({
  title = "We couldn’t load this content",
  message = "Try again. If the problem continues, check that the API is running and you still have access.",
  onRetry,
  action,
  className,
}: ErrorStateProps) {
  return (
    <Alert variant="destructive" role="alert" className={cn(className)}>
      <AlertCircle aria-hidden="true" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <p>{message}</p>
        {action || onRetry ? (
          <div className="mt-3">
            {action ?? (
              <Button size="sm" variant="outline" onClick={onRetry}>
                Try again
              </Button>
            )}
          </div>
        ) : null}
      </AlertDescription>
    </Alert>
  );
}
