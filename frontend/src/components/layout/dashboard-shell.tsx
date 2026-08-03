"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { AppShell } from "@/components/layout/app-shell";
import { useOnboardingStatus } from "@/hooks/use-onboarding-status";
import { useWorkspace } from "@/hooks/use-workspace";
import { useAuth } from "@/lib/auth/auth-context";

/**
 * Authentication and setup gate for everything under /dashboard.
 *
 * Renders the application shell once the session and workspace have resolved.
 * Unauthenticated visitors go to login; anyone without a workspace or a
 * knowledge space goes to onboarding rather than landing on a dashboard that
 * has nothing to show them.
 */
export function DashboardShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, status, signOut } = useAuth();
  const {
    workspaces,
    activeWorkspace,
    setActiveWorkspace,
    isError: workspacesError,
    refetch: refetchWorkspaces,
  } = useWorkspace();
  const onboarding = useOnboardingStatus();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [router, status]);

  useEffect(() => {
    if (
      status === "authenticated" &&
      !onboarding.isLoading &&
      !onboarding.isError &&
      onboarding.needsOnboarding
    ) {
      router.replace("/onboarding");
    }
  }, [onboarding, router, status]);

  if (status !== "authenticated" || onboarding.isLoading) {
    return (
      <main className="mx-auto min-h-dvh w-full max-w-6xl px-4 py-10 sm:px-6">
        <LoadingSkeleton variant="detail" rows={3} />
      </main>
    );
  }

  if (workspacesError || onboarding.isError) {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-xl items-center px-4 py-10">
        <ErrorState
          title="We couldn’t load your workspace"
          message="Check that the API is running, then try again."
          onRetry={() => void refetchWorkspaces()}
        />
      </main>
    );
  }

  // Redirecting; rendering the empty shell underneath would flash.
  if (onboarding.needsOnboarding) {
    return (
      <main className="mx-auto min-h-dvh w-full max-w-6xl px-4 py-10 sm:px-6">
        <LoadingSkeleton variant="detail" rows={3} />
      </main>
    );
  }

  return (
    <AppShell
      workspaces={workspaces}
      activeWorkspace={activeWorkspace}
      onWorkspaceSelect={setActiveWorkspace}
      user={user}
      onSignOut={signOut}
    >
      {children}
    </AppShell>
  );
}
