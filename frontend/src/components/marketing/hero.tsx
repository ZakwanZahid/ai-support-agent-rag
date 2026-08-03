import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { Container } from "@/components/marketing/section";
import { ProductPreview } from "@/components/marketing/product-preview";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="border-b border-border bg-surface py-16 sm:py-24">
      <Container>
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-semibold tracking-[-0.03em] text-foreground sm:text-5xl">
            Turn your support docs into an AI assistant.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-foreground-muted">
            Upload FAQs, policies, and product documentation. SupportMind
            answers questions from your knowledge base with clear citations.
          </p>

          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Button asChild size="lg">
              <Link href="/register">
                Start building your assistant
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="secondary">
              <a href="#how-it-works">View demo flow</a>
            </Button>
          </div>

          <p className="mt-5 text-sm text-foreground-subtle">
            Answers are grounded in your documents, not the open web.
          </p>
        </div>

        <ProductPreview className="mx-auto mt-14 max-w-3xl" />
      </Container>
    </section>
  );
}
