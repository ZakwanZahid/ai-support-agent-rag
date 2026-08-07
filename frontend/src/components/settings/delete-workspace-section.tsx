"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ConfirmDeleteDialog } from "@/components/common/confirm-delete-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { clearActiveWorkspace } from "@/hooks/use-workspace";
import { getAPIErrorMessage } from "@/lib/api/client";
import { deleteOrganization } from "@/lib/api/organizations";
import { queryKeys } from "@/lib/query-keys";
import type { Workspace } from "@/types/workspace";

interface DeleteWorkspaceSectionProps {
  workspace: Workspace;
}

/**
 * The only irreversible action that takes other people's work with it.
 *
 * Kept in its own panel rather than beside the rename field, and gated behind
 * typing the workspace name — the one place in the product where that friction
 * is proportionate. Everything else here can be rebuilt by re-uploading.
 */
export function DeleteWorkspaceSection({
  workspace,
}: DeleteWorkspaceSectionProps) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const router = useRouter();

  const deleteMutation = useMutation({
    mutationFn: () => deleteOrganization(workspace.id),
    onSuccess: async () => {
      setOpen(false);
      // The stored id points at a workspace that no longer exists; leaving it
      // would send every later request to a 404.
      clearActiveWorkspace();
      await queryClient.invalidateQueries({ queryKey: queryKeys.organizations });
      queryClient.removeQueries({ queryKey: ["documents"] });
      queryClient.removeQueries({ queryKey: ["documents-summary"] });
      queryClient.removeQueries({ queryKey: ["knowledge-bases"] });
      queryClient.removeQueries({ queryKey: ["conversations"] });
      toast.success(`${workspace.name} deleted.`);
      router.push("/dashboard");
    },
    onError: (error) => {
      // 403 lands here for an admin: only an owner may delete a workspace.
      toast.error(getAPIErrorMessage(error));
    },
  });

  return (
    <Card className="border-danger/40">
      <CardHeader>
        <h2 className="text-base font-semibold text-foreground">
          Delete this workspace
        </h2>
        <p className="text-sm leading-6 text-foreground-muted">
          Removes the workspace, every knowledge space and document in it, and
          all chat history — for everyone who uses it. This cannot be undone.
        </p>
      </CardHeader>
      <CardContent>
        <Button variant="destructive" onClick={() => setOpen(true)}>
          <Trash2 aria-hidden="true" />
          Delete workspace
        </Button>

        <ConfirmDeleteDialog
          open={open}
          onOpenChange={setOpen}
          title={`Delete ${workspace.name}?`}
          description="Every knowledge space, document and chat thread in this workspace is deleted, for every member. Your account and any other workspaces are unaffected."
          confirmLabel="Delete workspace"
          confirmPhrase={workspace.name}
          isPending={deleteMutation.isPending}
          onConfirm={() => deleteMutation.mutate()}
        />
      </CardContent>
    </Card>
  );
}
