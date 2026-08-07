"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ConfirmDeleteDialog } from "@/components/common/confirm-delete-dialog";
import { Button } from "@/components/ui/button";
import { getAPIErrorMessage } from "@/lib/api/client";
import { deleteKnowledgeBase } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import type { KnowledgeSpace } from "@/types/knowledge";

interface DeleteKnowledgeSpaceActionProps {
  workspaceId: string;
  knowledgeSpace: KnowledgeSpace;
  /** Where to go afterwards. Set from the detail page, which is about to 404. */
  redirectTo?: string;
  className?: string;
}

export function DeleteKnowledgeSpaceAction({
  workspaceId,
  knowledgeSpace,
  redirectTo,
  className,
}: DeleteKnowledgeSpaceActionProps) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const router = useRouter();

  const documentCount = knowledgeSpace.document_count ?? 0;

  const deleteMutation = useMutation({
    mutationFn: () => deleteKnowledgeBase(workspaceId, knowledgeSpace.id),
    onSuccess: async () => {
      setOpen(false);
      toast.success(`${knowledgeSpace.name} deleted.`);
      await queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeBases(workspaceId),
      });
      // The document list is keyed by knowledge space, and the "all" list
      // still holds rows that no longer exist.
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      await queryClient.invalidateQueries({ queryKey: ["documents-summary"] });
      if (redirectTo) {
        router.push(redirectTo);
      }
    },
    onError: (error) => {
      // 409 is the API refusing while a document is mid-preparation; its
      // message explains that better than anything generic would.
      toast.error(getAPIErrorMessage(error));
    },
  });

  return (
    <>
      <Button
        size="icon"
        variant="ghost"
        className={className}
        title="Delete knowledge space"
        onClick={() => setOpen(true)}
      >
        <Trash2 aria-hidden="true" />
        <span className="sr-only">Delete {knowledgeSpace.name}</span>
      </Button>

      <ConfirmDeleteDialog
        open={open}
        onOpenChange={setOpen}
        title={`Delete ${knowledgeSpace.name}?`}
        description={
          <>
            {documentCount > 0
              ? `Its ${documentCount} ${
                  documentCount === 1 ? "document is" : "documents are"
                } deleted too, along with everything prepared from them. `
              : "Nothing has been uploaded to it yet. "}
            Chat threads that used this knowledge space are kept, but they will
            have nothing left to search.
          </>
        }
        confirmLabel="Delete knowledge space"
        isPending={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate()}
      />
    </>
  );
}
