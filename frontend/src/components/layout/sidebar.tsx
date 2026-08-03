"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  FileText,
  LayoutDashboard,
  MessagesSquare,
  Settings,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Renders the item as unavailable. Used for areas not built yet. */
  comingSoon?: boolean;
  match?: (pathname: string) => boolean;
}

/**
 * Labels use product language throughout. Some hrefs still point at the
 * routes as they exist today; they move alongside the pages themselves.
 */
export const navItems: NavItem[] = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
    match: (pathname) => pathname === "/dashboard",
  },
  {
    label: "Knowledge",
    href: "/dashboard/knowledge-bases",
    icon: BookOpen,
  },
  {
    label: "Documents",
    href: "/dashboard/documents",
    icon: FileText,
  },
  {
    label: "Ask AI",
    href: "/dashboard/chat",
    icon: Sparkles,
  },
  {
    label: "Chat threads",
    href: "/dashboard/conversations",
    icon: MessagesSquare,
    comingSoon: true,
  },
  {
    label: "Settings",
    href: "/dashboard/settings",
    icon: Settings,
    comingSoon: true,
  },
];

export function ProductMark({ className }: { className?: string }) {
  return (
    <Link
      href="/dashboard"
      className={cn(
        "flex h-16 items-center gap-2.5 px-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
    >
      <span className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <Sparkles aria-hidden="true" className="size-4" />
      </span>
      <span className="text-[15px] font-semibold tracking-tight text-foreground">
        SupportMind
      </span>
    </Link>
  );
}

interface SidebarProps {
  items?: NavItem[];
  /** Called after navigating, so the mobile drawer can close itself. */
  onNavigate?: () => void;
  className?: string;
}

export function Sidebar({
  items = navItems,
  onNavigate,
  className,
}: SidebarProps) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Main"
      className={cn("flex flex-col gap-0.5 px-3", className)}
    >
      {items.map((item) => {
        const Icon = item.icon;

        if (item.comingSoon) {
          return (
            <span
              key={item.href}
              aria-disabled="true"
              className="flex h-9 cursor-not-allowed items-center gap-3 rounded-md px-3 text-sm font-medium text-foreground-subtle/70"
            >
              <Icon aria-hidden="true" className="size-[18px]" />
              <span>{item.label}</span>
              <span className="ml-auto text-[10px] font-medium uppercase tracking-wide">
                Soon
              </span>
            </span>
          );
        }

        const isActive = item.match
          ? item.match(pathname)
          : pathname === item.href || pathname.startsWith(`${item.href}/`);

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "flex h-9 items-center gap-3 rounded-md px-3 text-sm font-medium text-foreground-muted transition-colors",
              "hover:bg-surface-hover hover:text-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              isActive && "bg-surface-hover text-foreground",
            )}
          >
            <Icon aria-hidden="true" className="size-[18px]" />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
