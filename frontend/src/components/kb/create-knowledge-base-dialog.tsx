"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BookPlus, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import {
  KnowledgeBaseForm,
  type KnowledgeBaseFormValues,
} from "@/components/kb/knowledge-base-form";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { createKnowledgeBase } from "@/lib/api/knowledge-bases";
import { getAPIErrorMessage } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

interface CreateKnowledgeBaseDialogProps {
  organizationId: string;
  triggerLabel?: string;
  variant?: "default" | "outline";
  onCreated?: (knowledgeBaseId: string) => void;
}

export function CreateKnowledgeBaseDialog({
  organizationId,
  triggerLabel = "Create knowledge base",
  variant = "default",
  onCreated,
}: CreateKnowledgeBaseDialogProps) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (values: KnowledgeBaseFormValues) =>
      createKnowledgeBase(organizationId, {
        name: values.name,
        description: values.description || null,
      }),
    onSuccess: async (knowledgeBase) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeBases(organizationId),
      });
      setOpen(false);
      onCreated?.(knowledgeBase.id);
      toast.success("Knowledge base created.");
    },
    onError: (error) => toast.error(getAPIErrorMessage(error)),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={variant}>
          <Plus aria-hidden="true" />
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <span className="mb-2 flex size-9 items-center justify-center rounded-md bg-zinc-100 text-zinc-700">
            <BookPlus aria-hidden="true" className="size-4" />
          </span>
          <DialogTitle>Create a knowledge base</DialogTitle>
          <DialogDescription>
            Group support documents that should be searched together.
          </DialogDescription>
        </DialogHeader>
        <KnowledgeBaseForm
          onSubmit={async (values) => {
            await mutation.mutateAsync(values);
          }}
          disabled={mutation.isPending}
        />
      </DialogContent>
    </Dialog>
  );
}
