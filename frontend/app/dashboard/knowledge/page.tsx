"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpen } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader } from "@/components/common/page-header";
import { CreateKnowledgeSpaceDialog } from "@/components/knowledge/create-knowledge-space-dialog";
import { KnowledgeSpaceCard } from "@/components/knowledge/knowledge-space-card";
import { useWorkspace } from "@/hooks/use-workspace";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";

export default function KnowledgeSpacesPage() {
  const { activeWorkspace } = useWorkspace();
  const workspaceId = activeWorkspace?.id ?? null;

  const knowledgeSpacesQuery = useQuery({
    queryKey: queryKeys.knowledgeBases(workspaceId),
    queryFn: () => listKnowledgeBases(workspaceId!),
    enabled: Boolean(workspaceId),
  });

  const knowledgeSpaces = knowledgeSpacesQuery.data ?? [];

  return (
    <div className="space-y-7">
      <PageHeader
        title="Knowledge"
        description="Group related documents so your assistant searches the right material."
        actions={
          workspaceId && knowledgeSpaces.length > 0 ? (
            <CreateKnowledgeSpaceDialog workspaceId={workspaceId} />
          ) : undefined
        }
      />

      {knowledgeSpacesQuery.isPending ? (
        <LoadingSkeleton variant="cards" rows={3} />
      ) : knowledgeSpacesQuery.isError ? (
        <ErrorState
          title="We couldn’t load your knowledge spaces"
          onRetry={() => void knowledgeSpacesQuery.refetch()}
        />
      ) : knowledgeSpaces.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No knowledge spaces yet"
          description="Create your first knowledge space to organize documents for your AI assistant."
          action={
            workspaceId ? (
              <CreateKnowledgeSpaceDialog workspaceId={workspaceId} />
            ) : undefined
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {knowledgeSpaces.map((knowledgeSpace) => (
            <KnowledgeSpaceCard
              key={knowledgeSpace.id}
              knowledgeSpace={knowledgeSpace}
            />
          ))}
        </div>
      )}
    </div>
  );
}
