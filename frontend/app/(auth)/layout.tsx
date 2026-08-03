import { BookOpenCheck } from "lucide-react";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="grid min-h-dvh bg-white lg:grid-cols-[minmax(0,1fr)_minmax(28rem,0.8fr)]">
      <section className="hidden border-r border-border bg-primary px-12 py-14 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-3 text-sm font-semibold">
          <span className="flex size-9 items-center justify-center rounded-md bg-white text-foreground">
            <BookOpenCheck aria-hidden="true" className="size-5" />
          </span>
          AI Support Agent RAG
        </div>
        <div className="max-w-xl pb-10">
          <p className="mb-5 text-sm font-medium text-foreground-subtle">
            Grounded support, built for inspection
          </p>
          <h1 className="text-4xl font-semibold leading-tight tracking-[-0.035em]">
            Turn your support knowledge into answers people can verify.
          </h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-foreground-subtle">
            Organize source documents, index them for retrieval, and answer
            questions with citations back to the exact evidence.
          </p>
        </div>
        <p className="text-xs text-foreground-subtle">
          Multi-tenant RAG workspace · Frontend v1
        </p>
      </section>
      <section className="flex min-h-dvh items-center justify-center px-5 py-10 sm:px-8">
        <div className="w-full max-w-md">{children}</div>
      </section>
    </main>
  );
}
