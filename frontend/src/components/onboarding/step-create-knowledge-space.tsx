"use client";

import { useMutation } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getAPIErrorMessage } from "@/lib/api/client";
import { createKnowledgeBase } from "@/lib/api/knowledge-bases";
import { cn } from "@/lib/utils";
import type { KnowledgeSpace } from "@/types/knowledge";

/**
 * The four purposes from the product brief. Each seeds a sensible name and
 * description so the user can continue without writing copy.
 */
const PURPOSES = [
  {
    key: "support",
    label: "Customer support",
    name: "Customer support",
    description: "Policies and answers used when helping customers.",
  },
  {
    key: "product",
    label: "Product documentation",
    name: "Product documentation",
    description: "Product guides, release notes, and configuration docs.",
  },
  {
    key: "internal",
    label: "Internal team knowledge",
    name: "Internal knowledge",
    description: "Onboarding guides and internal processes.",
  },
  {
    key: "policies",
    label: "Policies and FAQs",
    name: "Policies and FAQs",
    description: "Published policies and frequently asked questions.",
  },
] as const;

interface StepCreateKnowledgeSpaceProps {
  workspaceId: string;
  onCreated: (knowledgeSpace: KnowledgeSpace) => void;
}

export function StepCreateKnowledgeSpace({
  workspaceId,
  onCreated,
}: StepCreateKnowledgeSpaceProps) {
  const [purposeKey, setPurposeKey] = useState<string | null>(null);
  const [name, setName] = useState("");

  const selectedPurpose = PURPOSES.find((purpose) => purpose.key === purposeKey);

  const mutation = useMutation({
    mutationFn: () =>
      createKnowledgeBase(workspaceId, {
        name: name.trim() || selectedPurpose?.name || "Knowledge space",
        description: selectedPurpose?.description ?? null,
      }),
    onSuccess: onCreated,
  });

  return (
    <div>
      <h2 className="text-2xl font-semibold tracking-[-0.02em] text-foreground">
        What will this assistant help with?
      </h2>
      <p className="mt-2 text-sm leading-6 text-foreground-muted">
        A knowledge space groups related documents. Pick the closest fit; you
        can rename it or add more later.
      </p>

      {mutation.isError ? (
        <Alert variant="destructive" className="mt-5">
          <AlertTitle>We couldn’t create the knowledge space</AlertTitle>
          <AlertDescription>
            {getAPIErrorMessage(mutation.error)}
          </AlertDescription>
        </Alert>
      ) : null}

      <div
        role="radiogroup"
        aria-label="Knowledge space purpose"
        className="mt-6 grid gap-3 sm:grid-cols-2"
      >
        {PURPOSES.map((purpose) => {
          const isSelected = purpose.key === purposeKey;
          return (
            <button
              key={purpose.key}
              type="button"
              role="radio"
              aria-checked={isSelected}
              disabled={mutation.isPending}
              onClick={() => {
                setPurposeKey(purpose.key);
                setName(purpose.name);
              }}
              className={cn(
                "rounded-lg border p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                isSelected
                  ? "border-primary bg-surface-hover"
                  : "border-border bg-surface hover:bg-surface-hover",
              )}
            >
              <span className="block text-sm font-medium text-foreground">
                {purpose.label}
              </span>
              <span className="mt-1 block text-xs leading-5 text-foreground-muted">
                {purpose.description}
              </span>
            </button>
          );
        })}
      </div>

      {purposeKey ? (
        <div className="mt-6 space-y-2">
          <Label htmlFor="knowledge-space-name">Name</Label>
          <Input
            id="knowledge-space-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={mutation.isPending}
            maxLength={255}
          />
        </div>
      ) : null}

      <Button
        className="mt-6"
        size="lg"
        disabled={!purposeKey || mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? (
          <LoaderCircle aria-hidden="true" className="animate-spin" />
        ) : null}
        Continue
      </Button>
    </div>
  );
}
