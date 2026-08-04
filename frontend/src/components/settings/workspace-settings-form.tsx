"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
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
import { updateOrganization } from "@/lib/api/organizations";
import { queryKeys } from "@/lib/query-keys";
import type { Workspace } from "@/types/workspace";

const schema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Give your workspace a name.")
    .max(255, "Use a shorter name."),
});

type Values = z.infer<typeof schema>;

export function WorkspaceSettingsForm({ workspace }: { workspace: Workspace }) {
  const queryClient = useQueryClient();

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: workspace.name },
  });

  // Switching workspaces swaps the record under this form, so reset it to the
  // new name instead of leaving the previous workspace's value in the field.
  const { reset } = form;
  useEffect(() => {
    reset({ name: workspace.name });
  }, [reset, workspace.id, workspace.name]);

  const mutation = useMutation({
    mutationFn: (values: Values) =>
      updateOrganization(workspace.id, { name: values.name }),
    onSuccess: async (updated) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.organizations,
      });
      reset({ name: updated.name });
      toast.success("Workspace updated.");
    },
  });

  // useWatch rather than form.watch: it subscribes without breaking
  // memoization, so the save button reacts to typing safely.
  const currentName = useWatch({ control: form.control, name: "name" });
  const isUnchanged = (currentName ?? "").trim() === workspace.name;

  return (
    <>
      {mutation.isError ? (
        <Alert variant="destructive" className="mb-5">
          <AlertTitle>We couldn’t save that</AlertTitle>
          <AlertDescription>
            {getAPIErrorMessage(mutation.error)}
          </AlertDescription>
        </Alert>
      ) : null}

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
                <FormLabel>Workspace name</FormLabel>
                <FormControl>
                  <Input
                    className="max-w-md"
                    disabled={mutation.isPending}
                    {...field}
                  />
                </FormControl>
                <FormDescription>
                  Shown in the workspace switcher and across the app.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button
            type="submit"
            disabled={mutation.isPending || isUnchanged}
          >
            {mutation.isPending ? (
              <LoaderCircle aria-hidden="true" className="animate-spin" />
            ) : null}
            Save changes
          </Button>
        </form>
      </Form>
    </>
  );
}
