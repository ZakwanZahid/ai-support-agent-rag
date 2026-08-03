"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { OnboardingFlow } from "@/components/onboarding/onboarding-flow";
import { useOnboardingStatus } from "@/hooks/use-onboarding-status";
import { useAuth } from "@/lib/auth/auth-context";

export default function OnboardingPage() {
  const router = useRouter();
  const { status } = useAuth();
  const onboarding = useOnboardingStatus();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [router, status]);

  // Someone who has already finished setup has no reason to be here. This is
  // an entry check only: creating a knowledge space part way through satisfies
  // needsOnboarding, and re-running the check would eject the user before they
  // reach the upload and first-question steps.
  const enteredFlowRef = useRef(false);
  useEffect(() => {
    if (
      status !== "authenticated" ||
      onboarding.isLoading ||
      onboarding.isError
    ) {
      return;
    }
    if (onboarding.needsOnboarding) {
      enteredFlowRef.current = true;
      return;
    }
    if (!enteredFlowRef.current) {
      router.replace("/dashboard");
    }
  }, [onboarding, router, status]);

  if (status !== "authenticated" || onboarding.isLoading) {
    return (
      <main className="mx-auto min-h-dvh w-full max-w-3xl px-5 py-14 sm:px-8">
        <LoadingSkeleton variant="detail" rows={2} />
      </main>
    );
  }

  if (onboarding.isError) {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-xl items-center px-5 py-10">
        <ErrorState
          title="We couldn’t start setup"
          message="Check that the API is running, then try again."
          onRetry={() => window.location.reload()}
        />
      </main>
    );
  }

  return (
    <OnboardingFlow
      initialStepIndex={onboarding.stepIndex}
      initialWorkspaceId={onboarding.workspaceId}
      initialKnowledgeSpaceId={onboarding.knowledgeSpaceId}
    />
  );
}
