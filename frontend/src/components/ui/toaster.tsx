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
            "border border-zinc-200 bg-white text-zinc-950 shadow-lg",
          description: "text-zinc-600",
          actionButton: "bg-zinc-900 text-white",
          cancelButton: "bg-zinc-100 text-zinc-700",
        },
      }}
      {...props}
    />
  );
}

export { Toaster };
