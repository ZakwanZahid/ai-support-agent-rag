import { Check, Sparkles } from "lucide-react";
import Link from "next/link";

const highlights = [
  "Answers drawn from documents you uploaded",
  "Every reply shows the passages behind it",
  "Separate workspaces for separate teams",
];

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="grid min-h-dvh bg-surface lg:grid-cols-2">
      {/* Explanation panel; hidden on small screens so the form gets the space. */}
      <section className="hidden bg-primary px-12 py-14 text-primary-foreground lg:flex lg:flex-col lg:justify-between">
        <Link href="/" className="flex w-fit items-center gap-2.5">
          <span className="flex size-7 items-center justify-center rounded-md bg-primary-foreground text-primary">
            <Sparkles aria-hidden="true" className="size-4" />
          </span>
          <span className="text-[15px] font-semibold tracking-tight">
            SupportMind
          </span>
        </Link>

        <div className="max-w-md pb-6">
          <h1 className="text-4xl font-semibold leading-tight tracking-[-0.03em]">
            Turn your support docs into an AI assistant.
          </h1>
          <p className="mt-5 text-base leading-7 text-primary-foreground/70">
            Upload FAQs, policies, and product documentation, then ask questions
            and get answers with clear sources.
          </p>

          <ul className="mt-8 space-y-3">
            {highlights.map((highlight) => (
              <li key={highlight} className="flex items-start gap-3 text-sm">
                <Check
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0 text-primary-foreground/70"
                />
                <span className="text-primary-foreground/90">{highlight}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-primary-foreground/50">
          Answers are grounded in your documents, not the open web.
        </p>
      </section>

      <section className="flex min-h-dvh items-center justify-center px-5 py-10 sm:px-8">
        <div className="w-full max-w-md">{children}</div>
      </section>
    </main>
  );
}
