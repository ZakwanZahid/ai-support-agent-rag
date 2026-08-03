"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  FileCheck2,
  Files,
  MessageSquareText,
  Upload,
} from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader } from "@/components/common/page-header";
import { CreateKnowledgeBaseDialog } from "@/components/kb/create-knowledge-base-dialog";
import { CreateOrganizationDialog } from "@/components/organizations/create-organization-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { listConversations } from "@/lib/api/conversations";
import { listDocuments } from "@/lib/api/documents";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import { useWorkspace } from "@/hooks/use-workspace";
import { useAuth } from "@/lib/auth/auth-context";

const stats = [
  { key: "knowledgeBases", label: "Knowledge bases", icon: BookOpen },
  { key: "documents", label: "Documents", icon: Files },
  { key: "indexed", label: "Indexed documents", icon: FileCheck2 },
  { key: "conversations", label: "Conversations", icon: MessageSquareText },
] as const;

export default function DashboardPage() {
  const { user } = useAuth();
  const {
    activeWorkspace,
    setActiveWorkspace,
    refetch: refetchWorkspaces,
  } = useWorkspace();
  const organizationId = activeWorkspace?.id;

  const knowledgeBasesQuery = useQuery({
    queryKey: queryKeys.knowledgeBases(organizationId),
    queryFn: () => listKnowledgeBases(organizationId!),
    enabled: Boolean(organizationId),
  });
  const documentsQuery = useQuery({
    queryKey: queryKeys.documents(organizationId),
    queryFn: () => listDocuments(organizationId!),
    enabled: Boolean(organizationId),
  });
  const conversationsQuery = useQuery({
    queryKey: queryKeys.conversations(organizationId),
    queryFn: () => listConversations(organizationId!),
    enabled: Boolean(organizationId),
  });

  const values = {
    knowledgeBases: knowledgeBasesQuery.data?.length ?? 0,
    documents: documentsQuery.data?.length ?? 0,
    indexed:
      documentsQuery.data?.filter((document) => document.status === "indexed")
        .length ?? 0,
    conversations: conversationsQuery.data?.length ?? 0,
  };
  const isLoading =
    knowledgeBasesQuery.isPending ||
    documentsQuery.isPending ||
    conversationsQuery.isPending;
  const isError =
    knowledgeBasesQuery.isError ||
    documentsQuery.isError ||
    conversationsQuery.isError;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow={activeWorkspace?.name ?? "Workspace"}
        title={`Welcome${user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}`}
        description="Manage the path from source documents to grounded support answers."
      />

      {!activeWorkspace ? (
        <EmptyState
          icon={BookOpen}
          title="Create your first organization"
          description="An organization is the tenant boundary for knowledge bases, documents, and conversations."
          action={
            <CreateOrganizationDialog
              onCreated={async (organizationId) => {
                await refetchWorkspaces();
                setActiveWorkspace(organizationId);
              }}
            />
          }
        />
      ) : isLoading ? (
        <LoadingSkeleton variant="cards" rows={4} />
      ) : isError ? (
        <ErrorState
          onRetry={() => {
            void knowledgeBasesQuery.refetch();
            void documentsQuery.refetch();
            void conversationsQuery.refetch();
          }}
        />
      ) : (
        <>
          <section aria-labelledby="workspace-stats">
            <h2 id="workspace-stats" className="sr-only">
              Workspace statistics
            </h2>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {stats.map(({ key, label, icon: Icon }) => (
                <Card key={key}>
                  <CardHeader className="flex-row items-center justify-between pb-3">
                    <p className="text-sm font-medium text-foreground-muted">{label}</p>
                    <Icon aria-hidden="true" className="size-4 text-foreground-subtle" />
                  </CardHeader>
                  <CardContent>
                    <p className="text-3xl font-semibold tracking-tight text-foreground">
                      {values[key]}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>

          <section className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
            <Card>
              <CardHeader>
                <h2 className="text-base font-semibold text-foreground">
                  Quick actions
                </h2>
                <p className="text-sm text-foreground-muted">
                  Continue the document-to-answer workflow.
                </p>
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-2">
                <Button asChild variant="outline" className="justify-start">
                  <Link href="/dashboard/knowledge-bases">
                    <Upload aria-hidden="true" />
                    Upload a document
                  </Link>
                </Button>
                <Button asChild variant="outline" className="justify-start">
                  <Link href="/dashboard/chat">
                    <MessageSquareText aria-hidden="true" />
                    Start a chat
                  </Link>
                </Button>
                <CreateKnowledgeBaseDialog
                  organizationId={activeWorkspace.id}
                  triggerLabel="Create knowledge base"
                  variant="outline"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h2 className="text-base font-semibold text-foreground">
                  Retrieval readiness
                </h2>
              </CardHeader>
              <CardContent>
                {values.indexed > 0 ? (
                  <>
                    <p className="text-3xl font-semibold text-foreground">
                      {values.indexed}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-foreground-muted">
                      Indexed {values.indexed === 1 ? "document is" : "documents are"}{" "}
                      available for semantic search and RAG chat.
                    </p>
                  </>
                ) : (
                  <p className="text-sm leading-6 text-foreground-muted">
                    Upload, ingest, and index a document before asking grounded
                    questions.
                  </p>
                )}
              </CardContent>
            </Card>
          </section>

          {values.knowledgeBases === 0 ? (
            <EmptyState
              compact
              icon={BookOpen}
              title="No knowledge bases yet"
              description="Create a knowledge base to organize the documents your support assistant can retrieve."
              action={
                <CreateKnowledgeBaseDialog
                  organizationId={activeWorkspace.id}
                />
              }
            />
          ) : null}
        </>
      )}
    </div>
  );
}
