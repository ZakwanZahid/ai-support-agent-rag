"use client";

import { Toaster as Sonner, type ToasterProps } from "sonner";

function Toaster(props: ToasterProps) {
  return (
    <Sonner
      closeButton
      position="top-right"
      toastOptions={{
        classNames: {
          toast:
            "border border-border bg-white text-foreground shadow-lg",
          description: "text-foreground-muted",
          actionButton: "bg-primary text-white",
          cancelButton: "bg-surface-hover text-foreground-muted",
        },
      }}
      {...props}
    />
  );
}

export { Toaster };
