"use client";

import { LogOut } from "lucide-react";

import { PageHeader } from "@/components/common/page-header";
import {
  ComingLater,
  SettingsSection,
} from "@/components/settings/settings-section";
import { WorkspaceSettingsForm } from "@/components/settings/workspace-settings-form";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/hooks/use-workspace";
import { useAuth } from "@/lib/auth/auth-context";
import { formatDate } from "@/lib/utils";

export default function SettingsPage() {
  const { user, signOut } = useAuth();
  const { activeWorkspace } = useWorkspace();

  return (
    <div className="space-y-7">
      <PageHeader
        title="Settings"
        description="Manage this workspace and your account."
      />

      {activeWorkspace ? (
        <SettingsSection
          title="Workspace"
          description={`Created ${formatDate(activeWorkspace.created_at)}.`}
        >
          <WorkspaceSettingsForm workspace={activeWorkspace} />
        </SettingsSection>
      ) : null}

      <SettingsSection
        title="Account"
        description="Details from your SupportMind account."
      >
        <dl className="space-y-4">
          <div>
            <dt className="text-sm text-foreground-muted">Name</dt>
            <dd className="mt-0.5 text-sm text-foreground">
              {user?.full_name?.trim() || "Not set"}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-foreground-muted">Email</dt>
            <dd className="mt-0.5 text-sm text-foreground">
              {user?.email ?? "Not available"}
            </dd>
          </div>
        </dl>

        <div className="mt-6 border-t border-border pt-5">
          <Button variant="secondary" onClick={signOut}>
            <LogOut aria-hidden="true" />
            Sign out
          </Button>
        </div>
      </SettingsSection>

      <ComingLater
        title="API access"
        description="Programmatic access to your workspace, so you can ask questions from your own tools."
        planned={[
          "Create and revoke API keys scoped to a workspace",
          "Query a knowledge space from your own application",
          "Usage visible per key",
        ]}
      />

      <ComingLater
        title="Model settings"
        description="Control which model answers your questions and how much source material it reads."
        planned={[
          "Choose the chat model used for answers",
          "Adjust how many passages are retrieved per question",
          "Set a custom instruction for the assistant's tone",
        ]}
      />
    </div>
  );
}
