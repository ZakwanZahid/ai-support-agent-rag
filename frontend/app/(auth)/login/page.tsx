"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { getAPIErrorMessage } from "@/lib/api/client";
import { loginUser } from "@/lib/api/auth";
import { queryKeys } from "@/lib/query-keys";

const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password.").max(128),
});

type LoginValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const loginMutation = useMutation({
    mutationFn: loginUser,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.currentUser });
      toast.success("Welcome back.");
      router.replace("/dashboard");
    },
  });

  return (
    <div>
      <div className="mb-8 lg:hidden">
        <p className="text-sm font-semibold text-zinc-950">
          AI Support Agent RAG
        </p>
      </div>
      <div className="mb-7">
        <p className="text-sm font-medium text-zinc-500">Welcome back</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-[-0.035em] text-zinc-950">
          Sign in to your workspace
        </h2>
        <p className="mt-3 text-sm leading-6 text-zinc-600">
          Continue managing knowledge and grounded support conversations.
        </p>
      </div>

      {loginMutation.isError ? (
        <Alert variant="destructive" className="mb-5">
          <AlertTitle>Sign in failed</AlertTitle>
          <AlertDescription>
            {getAPIErrorMessage(loginMutation.error)}
          </AlertDescription>
        </Alert>
      ) : null}

      <Form {...form}>
        <form
          className="space-y-5"
          onSubmit={form.handleSubmit((values) => loginMutation.mutate(values))}
          noValidate
        >
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <Input
                    type="email"
                    autoComplete="email"
                    placeholder="you@company.com"
                    disabled={loginMutation.isPending}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Password</FormLabel>
                <FormControl>
                  <Input
                    type="password"
                    autoComplete="current-password"
                    disabled={loginMutation.isPending}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button
            type="submit"
            className="w-full"
            size="lg"
            disabled={loginMutation.isPending}
          >
            {loginMutation.isPending ? (
              <LoaderCircle aria-hidden="true" className="animate-spin" />
            ) : null}
            Sign in
          </Button>
        </form>
      </Form>

      <p className="mt-6 text-center text-sm text-zinc-600">
        New to the workspace?{" "}
        <Link
          href="/register"
          className="font-medium text-zinc-950 underline-offset-4 hover:underline"
        >
          Create an account
        </Link>
      </p>
      <p className="mt-8 text-center text-xs leading-5 text-zinc-500">
        MVP sessions are stored in this browser. Production deployments should
        use secure httpOnly cookies.
      </p>
    </div>
  );
}
