import { Sparkles } from "lucide-react";
import Link from "next/link";

/**
 * Brand mark for the auth pages, shown only below the lg breakpoint where the
 * explanation panel is hidden and the form would otherwise have no context.
 */
export function AuthBrandMark() {
  return (
    <Link href="/" className="mb-8 flex w-fit items-center gap-2.5 lg:hidden">
      <span className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <Sparkles aria-hidden="true" className="size-4" />
      </span>
      <span className="text-[15px] font-semibold tracking-tight text-foreground">
        SupportMind
      </span>
    </Link>
  );
}
