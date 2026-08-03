"use client";

import { useQuery } from "@tanstack/react-query";

import { useWorkspace } from "@/hooks/use-workspace";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";

interface OnboardingStatus {
  isLoading: boolean;
  isError: boolean;
  /**
   * True until the user has both a workspace and somewhere to put documents.
   * Document count is deliberately excluded: an empty knowledge space is a
   * normal state the dashboard handles with an empty state, not a reason to
   * push someone back through setup.
   */
  needsOnboarding: boolean;
  /** Which step a returning user should resume at. */
  stepIndex: number;
  workspaceId: string | null;
  knowledgeSpaceId: string | null;
}

export function useOnboardingStatus(): OnboardingStatus {
  const {
    activeWorkspaceId,
    hasWorkspace,
    isLoading: workspacesLoading,
    isError: workspacesError,
  } = useWorkspace();

  const knowledgeSpacesQuery = useQuery({
    queryKey: queryKeys.knowledgeBases(activeWorkspaceId),
    queryFn: () => listKnowledgeBases(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId),
  });

  const knowledgeSpaces = knowledgeSpacesQuery.data ?? [];
  const isLoading =
    workspacesLoading || (Boolean(activeWorkspaceId) && knowledgeSpacesQuery.isPending);

  if (isLoading) {
    return {
      isLoading: true,
      isError: false,
      needsOnboarding: false,
      stepIndex: 0,
      workspaceId: activeWorkspaceId,
      knowledgeSpaceId: null,
    };
  }

  const hasKnowledgeSpace = knowledgeSpaces.length > 0;

  return {
    isLoading: false,
    isError: workspacesError || knowledgeSpacesQuery.isError,
    needsOnboarding: !hasWorkspace || !hasKnowledgeSpace,
    stepIndex: !hasWorkspace ? 0 : !hasKnowledgeSpace ? 1 : 2,
    workspaceId: activeWorkspaceId,
    knowledgeSpaceId: knowledgeSpaces[0]?.id ?? null,
  };
}
