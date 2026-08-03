import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { Container } from "@/components/marketing/section";
import { Button } from "@/components/ui/button";

export function CtaSection() {
  return (
    <section className="border-y border-border bg-primary py-16 sm:py-20">
      <Container>
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-[-0.02em] text-primary-foreground sm:text-4xl">
            Point it at your documents and ask a question.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-primary-foreground/70">
            Create a workspace, upload a policy, and see a cited answer in a few
            minutes.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Button asChild size="lg" variant="secondary">
              <Link href="/register">
                Start building your assistant
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="ghost"
              className="text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground"
            >
              <Link href="/login">Sign in</Link>
            </Button>
          </div>
        </div>
      </Container>
    </section>
  );
}
