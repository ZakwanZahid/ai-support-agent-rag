"use client";

import { useQuery } from "@tanstack/react-query";
import { useCallback, useSyncExternalStore } from "react";

import { listOrganizations } from "@/lib/api/organizations";
import { useAuth } from "@/lib/auth/auth-context";
import { queryKeys } from "@/lib/query-keys";
import type { Workspace } from "@/types/workspace";

const ACTIVE_WORKSPACE_KEY = "supportmind.active-workspace";
const ACTIVE_WORKSPACE_EVENT = "supportmind.workspace-change";

function subscribe(callback: () => void): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  window.addEventListener(ACTIVE_WORKSPACE_EVENT, callback);
  window.addEventListener("storage", callback);

  return () => {
    window.removeEventListener(ACTIVE_WORKSPACE_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

function getStoredId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(ACTIVE_WORKSPACE_KEY);
}

function getServerStoredId(): string | null {
  return null;
}

export function clearActiveWorkspace(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(ACTIVE_WORKSPACE_KEY);
  window.dispatchEvent(new Event(ACTIVE_WORKSPACE_EVENT));
}

interface UseWorkspaceResult {
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  /** Convenience for the many API calls that need the id and nothing else. */
  activeWorkspaceId: string | null;
  setActiveWorkspace: (workspaceId: string) => void;
  hasWorkspace: boolean;
  isLoading: boolean;
  isError: boolean;
  refetch: () => Promise<unknown>;
}

/**
 * Workspace list plus the user's current selection.
 *
 * The selection is persisted in localStorage and read through an external
 * store, so every consumer of this hook reacts to a switch without needing a
 * dedicated context provider. The workspace list itself is shared through the
 * TanStack Query cache for the same reason.
 */
export function useWorkspace(): UseWorkspaceResult {
  const { status } = useAuth();

  const query = useQuery({
    queryKey: queryKeys.organizations,
    queryFn: listOrganizations,
    enabled: status === "authenticated",
  });

  const storedId = useSyncExternalStore(
    subscribe,
    getStoredId,
    getServerStoredId,
  );

  const workspaces = query.data ?? [];

  // Fall back to the first workspace when the stored id is missing or points
  // at a workspace the user no longer belongs to.
  const activeWorkspace =
    workspaces.find((workspace) => workspace.id === storedId) ??
    workspaces[0] ??
    null;

  const setActiveWorkspace = useCallback((workspaceId: string) => {
    window.localStorage.setItem(ACTIVE_WORKSPACE_KEY, workspaceId);
    window.dispatchEvent(new Event(ACTIVE_WORKSPACE_EVENT));
  }, []);

  return {
    workspaces,
    activeWorkspace,
    activeWorkspaceId: activeWorkspace?.id ?? null,
    setActiveWorkspace,
    hasWorkspace: workspaces.length > 0,
    isLoading: status === "loading" || query.isPending,
    isError: query.isError,
    refetch: query.refetch,
  };
}

export { ACTIVE_WORKSPACE_KEY };
