"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { AppShell } from "@/components/layout/app-shell";
import { useWorkspace } from "@/hooks/use-workspace";
import { useAuth } from "@/lib/auth/auth-context";

/**
 * Authentication and workspace gate for everything under /dashboard.
 *
 * Renders the application shell once the session and workspace list have
 * resolved, and sends unauthenticated visitors to the login page.
 */
export function DashboardShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, status, signOut } = useAuth();
  const {
    workspaces,
    activeWorkspace,
    setActiveWorkspace,
    isLoading: workspacesLoading,
    isError: workspacesError,
    refetch: refetchWorkspaces,
  } = useWorkspace();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [router, status]);

  if (status !== "authenticated" || workspacesLoading) {
    return (
      <main className="mx-auto min-h-dvh w-full max-w-6xl px-4 py-10 sm:px-6">
        <LoadingSkeleton variant="detail" rows={3} />
      </main>
    );
  }

  if (workspacesError) {
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
