"use client";

import { Trash2 } from "lucide-react";
import { useState } from "react";

import { ConfirmDeleteDialog } from "@/components/common/confirm-delete-dialog";
import { Button } from "@/components/ui/button";
import { isDocumentInProgress } from "@/lib/terminology";
import type { KnowledgeDocument } from "@/types/document";

interface DeleteDocumentActionProps {
  document: KnowledgeDocument;
  onDelete: (documentId: string) => void;
  isDeleting?: boolean;
  className?: string;
}

/**
 * Delete control for a single document, with its own confirmation.
 *
 * The dialog lives here rather than at page level so every list that shows
 * documents gets the same wording by rendering one component. Radix only
 * mounts a dialog's contents while it is open, so a list of these costs a
 * button each and nothing more.
 */
export function DeleteDocumentAction({
  document,
  onDelete,
  isDeleting = false,
  className,
}: DeleteDocumentActionProps) {
  const [open, setOpen] = useState(false);
  // Preparation cannot be called back once it is running, so the API refuses
  // the delete. Disabling here says so before the user asks for it.
  const preparing = isDocumentInProgress(document.status);

  return (
    <>
      <Button
        size="icon"
        variant="ghost"
        className={className}
        disabled={preparing || isDeleting}
        title={
          preparing
            ? "You can delete this once it has finished preparing"
            : "Delete document"
        }
        onClick={() => setOpen(true)}
      >
        <Trash2 aria-hidden="true" />
        <span className="sr-only">Delete {document.title}</span>
      </Button>

      <ConfirmDeleteDialog
        open={open}
        onOpenChange={setOpen}
        title={`Delete ${document.title}?`}
        description="The document and the passages taken from it are removed for good. Past answers keep their text but will no longer list it as a source."
        confirmLabel="Delete document"
        isPending={isDeleting}
        onConfirm={() => {
          onDelete(document.id);
          setOpen(false);
        }}
      />
    </>
  );
}
