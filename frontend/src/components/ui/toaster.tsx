"use client";

import { Toaster as Sonner, type ToasterProps } from "sonner";

function Toaster(props: ToasterProps) {
  return (
    <Sonner
      closeButton
      richColors
      position="top-right"
      duration={4_000}
      // Sonner's own mobile rule sets width:100% while also applying left and
      // right offsets, so the container ends up wider than the screen. Its
      // stylesheet is injected after ours, so the override has to be important
      // to win.
      className="max-sm:!inset-x-4 max-sm:!w-auto"
      toastOptions={{
        classNames: {
          toast: "border border-border bg-surface text-foreground shadow-lg",
          description: "text-foreground-muted",
          actionButton: "bg-primary text-primary-foreground",
          cancelButton: "bg-surface-hover text-foreground-muted",
        },
      }}
      {...props}
    />
  );
}

export { Toaster };
