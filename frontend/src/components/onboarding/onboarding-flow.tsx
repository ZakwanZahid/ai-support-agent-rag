"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  ONBOARDING_STEPS,
  OnboardingStepper,
} from "@/components/onboarding/onboarding-stepper";
import { StepAddDocument } from "@/components/onboarding/step-add-document";
import { StepCreateKnowledgeSpace } from "@/components/onboarding/step-create-knowledge-space";
import { StepCreateWorkspace } from "@/components/onboarding/step-create-workspace";
import { StepFirstQuestion } from "@/components/onboarding/step-first-question";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/hooks/use-workspace";
import { queryKeys } from "@/lib/query-keys";
import type { KnowledgeDocument } from "@/types/document";

interface OnboardingFlowProps {
  /** Where the user already is, so a returning user resumes mid-flow. */
  initialStepIndex: number;
  initialWorkspaceId: string | null;
  initialKnowledgeSpaceId: string | null;
}

export function OnboardingFlow({
  initialStepIndex,
  initialWorkspaceId,
  initialKnowledgeSpaceId,
}: OnboardingFlowProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { setActiveWorkspace, refetch: refetchWorkspaces } = useWorkspace();

  const [stepIndex, setStepIndex] = useState(initialStepIndex);
  const [workspaceId, setWorkspaceId] = useState(initialWorkspaceId);
  const [knowledgeSpaceId, setKnowledgeSpaceId] = useState(
    initialKnowledgeSpaceId,
  );
  const [readyDocument, setReadyDocument] = useState<KnowledgeDocument | null>(
    null,
  );

  const finish = () => {
    // The dashboard gate re-reads both lists, so make sure they are current
    // before navigating or it may bounce straight back here.
    void queryClient.invalidateQueries({ queryKey: queryKeys.organizations });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.knowledgeBases(workspaceId),
    });
    router.replace("/dashboard");
  };

  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex h-16 w-full max-w-3xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Sparkles aria-hidden="true" className="size-4" />
            </span>
            <span className="text-[15px] font-semibold tracking-tight text-foreground">
              SupportMind
            </span>
          </Link>

          {/* An escape hatch matters here: setup should never feel like a trap. */}
          {workspaceId ? (
            <Button asChild size="sm" variant="ghost">
              <Link href="/dashboard">Skip setup</Link>
            </Button>
          ) : null}
        </div>
      </header>

      <main
        id="main-content"
        className="mx-auto w-full max-w-3xl px-5 py-10 sm:px-8 sm:py-14"
      >
        <OnboardingStepper currentIndex={stepIndex} className="mb-10" />

        {stepIndex === 0 ? (
          <StepCreateWorkspace
            onCreated={async (workspace) => {
              setWorkspaceId(workspace.id);
              await refetchWorkspaces();
              setActiveWorkspace(workspace.id);
              setStepIndex(1);
            }}
          />
        ) : null}

        {stepIndex === 1 && workspaceId ? (
          <StepCreateKnowledgeSpace
            workspaceId={workspaceId}
            onCreated={(knowledgeSpace) => {
              setKnowledgeSpaceId(knowledgeSpace.id);
              void queryClient.invalidateQueries({
                queryKey: queryKeys.knowledgeBases(workspaceId),
              });
              setStepIndex(2);
            }}
          />
        ) : null}

        {stepIndex === 2 && workspaceId && knowledgeSpaceId ? (
          <StepAddDocument
            workspaceId={workspaceId}
            knowledgeSpaceId={knowledgeSpaceId}
            onReady={(document) => {
              setReadyDocument(document);
              setStepIndex(3);
            }}
          />
        ) : null}

        {stepIndex === 3 && workspaceId && knowledgeSpaceId ? (
          <StepFirstQuestion
            workspaceId={workspaceId}
            knowledgeSpaceId={knowledgeSpaceId}
            documentTitle={readyDocument?.title}
            onFinish={finish}
          />
        ) : null}

        <p className="mt-10 text-xs text-foreground-subtle">
          Step {Math.min(stepIndex + 1, ONBOARDING_STEPS.length)} of{" "}
          {ONBOARDING_STEPS.length}
        </p>
      </main>
    </div>
  );
}
