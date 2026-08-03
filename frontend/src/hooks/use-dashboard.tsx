"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from "react";

import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { AppShell } from "@/components/layout/app-shell";
import { getCurrentUser, logoutUser, type UserResponse } from "@/lib/api/auth";
import {
  listOrganizations,
  type OrganizationResponse,
} from "@/lib/api/organizations";
import { getAccessToken } from "@/lib/auth-token";
import { queryKeys } from "@/lib/query-keys";

const SELECTED_ORGANIZATION_KEY = "ai-support-agent.selected-organization";
const SELECTED_ORGANIZATION_EVENT = "ai-support-agent.organization-change";

function subscribeToStorage(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(SELECTED_ORGANIZATION_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(SELECTED_ORGANIZATION_EVENT, callback);
  };
}

function getStoredOrganizationId() {
  return window.localStorage.getItem(SELECTED_ORGANIZATION_KEY);
}

function subscribeToToken() {
  return () => undefined;
}

interface DashboardContextValue {
  user: UserResponse;
  organizations: OrganizationResponse[];
  selectedOrganization: OrganizationResponse | null;
  setSelectedOrganizationId: (organizationId: string) => void;
  refetchOrganizations: () => Promise<unknown>;
}

const DashboardContext = createContext<DashboardContextValue | null>(null);

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const hasToken = useSyncExternalStore(
    subscribeToToken,
    () => Boolean(getAccessToken()),
    () => false,
  );
  const storedOrganizationId = useSyncExternalStore(
    subscribeToStorage,
    getStoredOrganizationId,
    () => null,
  );

  useEffect(() => {
    if (!hasToken) {
      router.replace("/login");
    }
  }, [hasToken, router]);

  const userQuery = useQuery({
    queryKey: queryKeys.currentUser,
    queryFn: getCurrentUser,
    enabled: hasToken,
  });

  const organizationsQuery = useQuery({
    queryKey: queryKeys.organizations,
    queryFn: listOrganizations,
    enabled: hasToken && userQuery.isSuccess,
  });

  const organizations = organizationsQuery.data ?? [];
  const selectedOrganizationId = organizations.some(
    (organization) => organization.id === storedOrganizationId,
  )
    ? storedOrganizationId
    : (organizations[0]?.id ?? null);

  const setSelectedOrganizationId = useCallback((organizationId: string) => {
    window.localStorage.setItem(SELECTED_ORGANIZATION_KEY, organizationId);
    window.dispatchEvent(new Event(SELECTED_ORGANIZATION_EVENT));
  }, []);

  const handleLogout = useCallback(() => {
    logoutUser();
    window.localStorage.removeItem(SELECTED_ORGANIZATION_KEY);
    queryClient.clear();
    router.replace("/login");
  }, [queryClient, router]);

  const selectedOrganization =
    organizationsQuery.data?.find(
      (organization) => organization.id === selectedOrganizationId,
    ) ?? null;

  const contextValue = useMemo<DashboardContextValue | null>(() => {
    if (!userQuery.data) {
      return null;
    }
    return {
      user: userQuery.data,
      organizations: organizationsQuery.data ?? [],
      selectedOrganization,
      setSelectedOrganizationId,
      refetchOrganizations: organizationsQuery.refetch,
    };
  }, [
    organizationsQuery.data,
    organizationsQuery.refetch,
    selectedOrganization,
    setSelectedOrganizationId,
    userQuery.data,
  ]);

  if (
    !hasToken ||
    userQuery.isPending ||
    organizationsQuery.isPending
  ) {
    return (
      <main className="mx-auto min-h-dvh max-w-6xl px-4 py-10 sm:px-6">
        <LoadingSkeleton variant="detail" rows={4} />
      </main>
    );
  }

  if (userQuery.isError || organizationsQuery.isError || !contextValue) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-xl items-center px-4 py-10">
        <ErrorState
          title="The workspace could not be loaded"
          message="Check that the backend is running, then try again."
          onRetry={() => {
            void userQuery.refetch();
            void organizationsQuery.refetch();
          }}
        />
      </main>
    );
  }

  return (
    <DashboardContext.Provider value={contextValue}>
      <AppShell
        organizations={contextValue.organizations}
        selectedOrganizationId={selectedOrganizationId}
        onOrganizationChange={setSelectedOrganizationId}
        user={{
          name: contextValue.user.full_name,
          email: contextValue.user.email,
        }}
        onLogout={handleLogout}
        environmentLabel="Local API"
      >
        {children}
      </AppShell>
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error("useDashboard must be used within DashboardShell");
  }
  return context;
}
