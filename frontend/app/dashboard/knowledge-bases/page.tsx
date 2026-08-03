"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpen } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader } from "@/components/common/page-header";
import { CreateKnowledgeBaseDialog } from "@/components/kb/create-knowledge-base-dialog";
import { KnowledgeBaseCard } from "@/components/kb/knowledge-base-card";
import { CreateOrganizationDialog } from "@/components/organizations/create-organization-dialog";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import { useDashboard } from "@/hooks/use-dashboard";

export default function KnowledgeBasesPage() {
  const {
    selectedOrganization,
    refetchOrganizations,
    setSelectedOrganizationId,
  } = useDashboard();
  const organizationId = selectedOrganization?.id;
  const knowledgeBasesQuery = useQuery({
    queryKey: queryKeys.knowledgeBases(organizationId),
    queryFn: () => listKnowledgeBases(organizationId!),
    enabled: Boolean(organizationId),
  });

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Knowledge"
        title="Knowledge bases"
        description="Keep related support documents together so retrieval stays focused and tenant-safe."
        actions={
          organizationId ? (
            <CreateKnowledgeBaseDialog organizationId={organizationId} />
          ) : undefined
        }
      />

      {!selectedOrganization ? (
        <EmptyState
          icon={BookOpen}
          title="An organization is required"
          description="Create an organization before adding knowledge bases."
          action={
            <CreateOrganizationDialog
              onCreated={async (createdId) => {
                await refetchOrganizations();
                setSelectedOrganizationId(createdId);
              }}
            />
          }
        />
      ) : knowledgeBasesQuery.isPending ? (
        <LoadingSkeleton variant="cards" rows={3} />
      ) : knowledgeBasesQuery.isError ? (
        <ErrorState onRetry={() => void knowledgeBasesQuery.refetch()} />
      ) : knowledgeBasesQuery.data.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No knowledge bases yet"
          description="Create one for policies, product guides, FAQs, or another focused support domain."
          action={
            <CreateKnowledgeBaseDialog organizationId={selectedOrganization.id} />
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {knowledgeBasesQuery.data.map((knowledgeBase) => (
            <KnowledgeBaseCard
              key={knowledgeBase.id}
              knowledgeBase={knowledgeBase}
            />
          ))}
        </div>
      )}
    </div>
  );
}
