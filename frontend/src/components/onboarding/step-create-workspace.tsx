"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { getAPIErrorMessage } from "@/lib/api/client";
import { createOrganization } from "@/lib/api/organizations";
import type { Workspace } from "@/types/workspace";

const schema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Give your workspace a name.")
    .max(255, "Use a shorter name."),
});

type Values = z.infer<typeof schema>;

interface StepCreateWorkspaceProps {
  onCreated: (workspace: Workspace) => void;
}

export function StepCreateWorkspace({ onCreated }: StepCreateWorkspaceProps) {
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: Values) => createOrganization({ name: values.name }),
    onSuccess: onCreated,
  });

  return (
    <div>
      <h2 className="text-2xl font-semibold tracking-[-0.02em] text-foreground">
        Create your workspace
      </h2>
      <p className="mt-2 text-sm leading-6 text-foreground-muted">
        A workspace holds your documents and chats. Most teams name it after
        their company or department.
      </p>

      {mutation.isError ? (
        <Alert variant="destructive" className="mt-5">
          <AlertTitle>We couldn’t create the workspace</AlertTitle>
          <AlertDescription>
            {getAPIErrorMessage(mutation.error)}
          </AlertDescription>
        </Alert>
      ) : null}

      <Form {...form}>
        <form
          className="mt-6 space-y-5"
          onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          noValidate
        >
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Workspace name</FormLabel>
                <FormControl>
                  <Input
                    autoFocus
                    placeholder="Northwind Support"
                    disabled={mutation.isPending}
                    {...field}
                  />
                </FormControl>
                <FormDescription>
                  You can create more workspaces later.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button type="submit" size="lg" disabled={mutation.isPending}>
            {mutation.isPending ? (
              <LoaderCircle aria-hidden="true" className="animate-spin" />
            ) : null}
            Continue
          </Button>
        </form>
      </Form>
    </div>
  );
}
