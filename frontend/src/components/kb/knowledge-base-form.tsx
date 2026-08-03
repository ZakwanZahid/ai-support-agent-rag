"use client";

import { Loader2, Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
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

const knowledgeBaseSchema = z.object({
  name: z
    .string()
    .trim()
    .min(2, "Name must be at least 2 characters.")
    .max(120, "Name must be 120 characters or fewer."),
  description: z
    .string()
    .trim()
    .max(500, "Description must be 500 characters or fewer."),
});

export type KnowledgeBaseFormValues = z.infer<typeof knowledgeBaseSchema>;

interface KnowledgeBaseFormProps {
  onSubmit: (
    values: KnowledgeBaseFormValues,
  ) => void | Promise<void>;
  defaultValues?: Partial<KnowledgeBaseFormValues>;
  submitLabel?: string;
  disabled?: boolean;
}

export function KnowledgeBaseForm({
  onSubmit,
  defaultValues,
  submitLabel = "Create knowledge base",
  disabled = false,
}: KnowledgeBaseFormProps) {
  const form = useForm<KnowledgeBaseFormValues>({
    defaultValues: {
      name: defaultValues?.name ?? "",
      description: defaultValues?.description ?? "",
    },
  });

  async function submit(values: KnowledgeBaseFormValues) {
    const result = knowledgeBaseSchema.safeParse(values);
    if (!result.success) {
      for (const issue of result.error.issues) {
        const field = issue.path[0];
        if (field === "name" || field === "description") {
          form.setError(field, { message: issue.message });
        }
      }
      return;
    }

    try {
      await onSubmit(result.data);
      if (!defaultValues) form.reset();
    } catch {
      // The owning mutation renders the API error and keeps the form values
      // available for correction or retry.
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(submit)} className="space-y-5">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input
                  placeholder="Customer support knowledge"
                  autoComplete="off"
                  disabled={disabled || form.formState.isSubmitting}
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
                  placeholder="Policies, product guides, and common support answers."
                  disabled={disabled || form.formState.isSubmitting}
                  {...field}
                />
              </FormControl>
              <FormDescription>
                Describe what this knowledge base contains.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button
          type="submit"
          disabled={disabled || form.formState.isSubmitting}
        >
          {form.formState.isSubmitting ? (
            <Loader2 aria-hidden="true" className="animate-spin" />
          ) : (
            <Plus aria-hidden="true" />
          )}
          {form.formState.isSubmitting ? "Saving" : submitLabel}
        </Button>
      </form>
    </Form>
  );
}
