import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface SettingsSectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
}

export function SettingsSection({
  title,
  description,
  children,
}: SettingsSectionProps) {
  return (
    <Card>
      <CardHeader>
        <h2 className="text-base font-semibold text-foreground">{title}</h2>
        {description ? (
          <p className="text-sm leading-6 text-foreground-muted">
            {description}
          </p>
        ) : null}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

interface ComingLaterProps {
  title: string;
  description: string;
  /** What the section will let people do, so the placeholder still informs. */
  planned: string[];
}

/**
 * A placeholder that says what is missing and what it will do, rather than an
 * empty panel that reads as broken.
 */
export function ComingLater({ title, description, planned }: ComingLaterProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2.5">
          <h2 className="text-base font-semibold text-foreground">{title}</h2>
          <span className="rounded-full border border-border bg-surface-subtle px-2 py-0.5 text-[11px] font-medium text-foreground-subtle">
            Coming later
          </span>
        </div>
        <p className="text-sm leading-6 text-foreground-muted">{description}</p>
      </CardHeader>
      <CardContent>
        <ul className="space-y-1.5">
          {planned.map((item) => (
            <li
              key={item}
              className="flex items-start gap-2.5 text-sm leading-6 text-foreground-subtle"
            >
              <span
                aria-hidden="true"
                className="mt-2.5 size-1 shrink-0 rounded-full bg-border-strong"
              />
              {item}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
