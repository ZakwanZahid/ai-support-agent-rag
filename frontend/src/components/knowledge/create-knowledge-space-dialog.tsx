"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, Plus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { getAPIErrorMessage } from "@/lib/api/client";
import { createKnowledgeBase } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";

const schema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Give the knowledge space a name.")
    .max(255, "Use a shorter name."),
  description: z.string().trim().max(1000).optional(),
});

type Values = z.infer<typeof schema>;

interface CreateKnowledgeSpaceDialogProps {
  workspaceId: string;
  triggerLabel?: string;
  variant?: "default" | "secondary";
  onCreated?: (knowledgeSpaceId: string) => void;
}

export function CreateKnowledgeSpaceDialog({
  workspaceId,
  triggerLabel = "Create knowledge space",
  variant = "default",
  onCreated,
}: CreateKnowledgeSpaceDialogProps) {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", description: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: Values) =>
      createKnowledgeBase(workspaceId, {
        name: values.name,
        description: values.description || null,
      }),
    onSuccess: async (knowledgeSpace) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.knowledgeBases(workspaceId),
      });
      setOpen(false);
      form.reset();
      onCreated?.(knowledgeSpace.id);
      toast.success("Knowledge space created.");
    },
    onError: (error) => toast.error(getAPIErrorMessage(error)),
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) form.reset();
      }}
    >
      <DialogTrigger asChild>
        <Button variant={variant}>
          <Plus aria-hidden="true" />
          {triggerLabel}
        </Button>
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create a knowledge space</DialogTitle>
          <DialogDescription>
            Group documents that should be searched together, so answers stay
            focused on one area.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form
            className="space-y-5"
            onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
            noValidate
          >
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input
                      autoFocus
                      placeholder="Customer support"
                      disabled={mutation.isPending}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea
                      rows={3}
                      placeholder="Refund, shipping, and account policies."
                      disabled={mutation.isPending}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>Optional.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? (
                  <LoaderCircle aria-hidden="true" className="animate-spin" />
                ) : null}
                Create knowledge space
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
