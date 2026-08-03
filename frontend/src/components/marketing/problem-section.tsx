import { Section, SectionHeading } from "@/components/marketing/section";

const problems = [
  {
    title: "The answer exists, but nobody can find it",
    body: "Policies live in a PDF, the exception lives in a wiki page, and the person who knew both left last year.",
  },
  {
    title: "General AI tools invent the details",
    body: "A model trained on the open web will confidently describe a refund window your company never offered.",
  },
  {
    title: "Nobody trusts an answer they can't check",
    body: "Without a link back to the source passage, every reply still has to be verified by hand.",
  },
];

export function ProblemSection() {
  return (
    <Section muted>
      <SectionHeading
        eyebrow="The problem"
        title="Support knowledge is written down. It just isn't answerable."
        description="Most teams already have the documentation they need. What they lack is a way to ask it a question and get an answer they can trust."
      />

      <div className="mt-12 grid gap-6 sm:grid-cols-3">
        {problems.map((problem) => (
          <div key={problem.title}>
            <h3 className="text-base font-semibold text-foreground">
              {problem.title}
            </h3>
            <p className="mt-2 text-sm leading-6 text-foreground-muted">
              {problem.body}
            </p>
          </div>
        ))}
      </div>
    </Section>
  );
}
