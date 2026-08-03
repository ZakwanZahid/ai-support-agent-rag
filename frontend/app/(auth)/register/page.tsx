"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { AuthBrandMark } from "@/components/marketing/auth-brand-mark";
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
import { useAuth } from "@/lib/auth/auth-context";
import { resolvePostAuthDestination } from "@/lib/auth/post-auth-route";

const registerSchema = z.object({
  full_name: z.string().trim().max(255).optional(),
  email: z.string().trim().email("Enter a valid email address."),
  password: z
    .string()
    .min(8, "Use at least 8 characters.")
    .max(128, "Use no more than 128 characters."),
});

type RegisterValues = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const { signUp } = useAuth();

  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { full_name: "", email: "", password: "" },
  });

  const registerMutation = useMutation({
    mutationFn: (values: RegisterValues) =>
      signUp({ ...values, full_name: values.full_name || null }),
    onSuccess: () => {
      toast.success("Account created.");
      router.replace(resolvePostAuthDestination());
    },
  });

  return (
    <div>
      <AuthBrandMark />

      <div className="mb-7">
        <h2 className="text-3xl font-semibold tracking-[-0.03em] text-foreground">
          Create your AI support workspace.
        </h2>
        <p className="mt-3 text-sm leading-6 text-foreground-muted">
          We&rsquo;ll walk you through setting it up once you&rsquo;re in.
        </p>
      </div>

      {registerMutation.isError ? (
        <Alert variant="destructive" className="mb-5">
          <AlertTitle>Account creation failed</AlertTitle>
          <AlertDescription>
            {getAPIErrorMessage(registerMutation.error)}
          </AlertDescription>
        </Alert>
      ) : null}

      <Form {...form}>
        <form
          className="space-y-5"
          onSubmit={form.handleSubmit((values) =>
            registerMutation.mutate(values),
          )}
          noValidate
        >
          <FormField
            control={form.control}
            name="full_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Full name</FormLabel>
                <FormControl>
                  <Input
                    autoComplete="name"
                    placeholder="Alex Morgan"
                    disabled={registerMutation.isPending}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
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
                    disabled={registerMutation.isPending}
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
                    autoComplete="new-password"
                    placeholder="At least 8 characters"
                    disabled={registerMutation.isPending}
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
            disabled={registerMutation.isPending}
          >
            {registerMutation.isPending ? (
              <LoaderCircle aria-hidden="true" className="animate-spin" />
            ) : null}
            Create account
          </Button>
        </form>
      </Form>

      <p className="mt-6 text-center text-sm text-foreground-muted">
        Already have an account?{" "}
        <Link
          href="/login"
          className="font-medium text-foreground underline-offset-4 hover:underline"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
