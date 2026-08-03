import { Sparkles } from "lucide-react";
import Link from "next/link";

import { Container } from "@/components/marketing/section";

const footerLinks = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Features", href: "#features" },
  { label: "Use cases", href: "#use-cases" },
];

export function SiteFooter() {
  return (
    <footer className="bg-surface py-12">
      <Container>
        <div className="flex flex-col gap-8 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-sm">
            <div className="flex items-center gap-2.5">
              <span className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Sparkles aria-hidden="true" className="size-4" />
              </span>
              <span className="text-[15px] font-semibold tracking-tight text-foreground">
                SupportMind
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 text-foreground-muted">
              An AI support assistant that answers from your own documents and
              shows its sources.
            </p>
          </div>

          <nav aria-label="Footer" className="flex flex-col gap-2.5">
            {footerLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-sm text-foreground-muted transition-colors hover:text-foreground"
              >
                {link.label}
              </a>
            ))}
            <Link
              href="/login"
              className="text-sm text-foreground-muted transition-colors hover:text-foreground"
            >
              Sign in
            </Link>
          </nav>
        </div>

        <div className="mt-10 border-t border-border pt-6">
          <p className="text-xs text-foreground-subtle">
            A portfolio project demonstrating retrieval-augmented generation
            over multi-tenant document storage.
          </p>
        </div>
      </Container>
    </footer>
  );
}
