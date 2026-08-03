"use client";

import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader } from "@/components/common/page-header";
import { QuickActions } from "@/components/dashboard/quick-actions";
import { RecentChatThreads } from "@/components/dashboard/recent-chat-threads";
import { RecentDocuments } from "@/components/dashboard/recent-documents";
import { SetupChecklist } from "@/components/dashboard/setup-checklist";
import { StatCards } from "@/components/dashboard/stat-cards";
import { useDashboardData } from "@/hooks/use-dashboard-data";
import { useWorkspace } from "@/hooks/use-workspace";
import { useAuth } from "@/lib/auth/auth-context";

function firstName(fullName: string | null | undefined): string | null {
  const trimmed = fullName?.trim();
  if (!trimmed) return null;
  return trimmed.split(/\s+/)[0];
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { activeWorkspace } = useWorkspace();
  const data = useDashboardData(activeWorkspace?.id ?? null);

  const greeting = firstName(user?.full_name)
    ? `Welcome back, ${firstName(user?.full_name)}`
    : "Welcome back";

  if (data.isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow={activeWorkspace?.name}
          title={greeting}
          description="Here’s where your assistant stands."
        />
        <LoadingSkeleton variant="cards" rows={4} />
      </div>
    );
  }

  if (data.isError) {
    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow={activeWorkspace?.name}
          title={greeting}
          description="Here’s where your assistant stands."
        />
        <ErrorState
          title="We couldn’t load your dashboard"
          message="Check that the API is running, then try again."
          onRetry={data.refetch}
        />
      </div>
    );
  }

  const hasReadyDocument = data.stats.readyDocuments > 0;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow={activeWorkspace?.name}
        title={greeting}
        description="Here’s where your assistant stands."
      />

      <SetupChecklist
        hasKnowledgeSpace={data.stats.knowledgeSpaces > 0}
        hasDocument={data.stats.documents > 0}
        hasReadyDocument={hasReadyDocument}
        hasAskedSomething={data.stats.chatThreads > 0}
      />

      <section aria-labelledby="workspace-stats">
        <h2 id="workspace-stats" className="sr-only">
          Workspace overview
        </h2>
        <StatCards
          knowledgeSpaces={data.stats.knowledgeSpaces}
          documents={data.stats.documents}
          readyDocuments={data.stats.readyDocuments}
          chatThreads={data.stats.chatThreads}
        />
      </section>

      <div className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-5">
          <RecentDocuments documents={data.recentDocuments} />
          <RecentChatThreads
            chatThreads={data.recentChatThreads}
            knowledgeSpaces={data.knowledgeSpaces}
            canStartChat={hasReadyDocument}
          />
        </div>
        <QuickActions canAsk={hasReadyDocument} />
      </div>
    </div>
  );
}
