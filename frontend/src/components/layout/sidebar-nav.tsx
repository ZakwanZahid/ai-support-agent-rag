"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  FileText,
  LayoutDashboard,
  MessageSquareText,
  Settings,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

export interface SidebarNavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  disabled?: boolean;
  match?: (pathname: string) => boolean;
}

export const defaultSidebarItems: SidebarNavItem[] = [
  {
    title: "Overview",
    href: "/dashboard",
    icon: LayoutDashboard,
    match: (pathname) => pathname === "/dashboard",
  },
  {
    title: "Knowledge Bases",
    href: "/dashboard/knowledge-bases",
    icon: BookOpen,
  },
  {
    title: "Documents",
    href: "/dashboard/documents",
    icon: FileText,
  },
  {
    title: "Chat",
    href: "/dashboard/chat",
    icon: MessageSquareText,
    match: (pathname) =>
      pathname.startsWith("/dashboard/chat") ||
      pathname.startsWith("/dashboard/conversations"),
  },
  {
    title: "Settings",
    href: "/dashboard/settings",
    icon: Settings,
    disabled: true,
  },
];

interface SidebarNavProps {
  items?: SidebarNavItem[];
  onNavigate?: () => void;
  className?: string;
}

export function SidebarNav({
  items = defaultSidebarItems,
  onNavigate,
  className,
}: SidebarNavProps) {
  const pathname = usePathname();

  return (
    <nav aria-label="Dashboard navigation" className={cn("space-y-1", className)}>
      {items.map((item) => {
        const isActive = item.match
          ? item.match(pathname)
          : pathname === item.href || pathname.startsWith(`${item.href}/`);
        const Icon = item.icon;

        if (item.disabled) {
          return (
            <div
              key={item.href}
              aria-disabled="true"
              className="flex h-10 cursor-not-allowed items-center gap-3 rounded-md px-3 text-sm font-medium text-zinc-400"
            >
              <Icon aria-hidden="true" className="size-[18px]" />
              <span>{item.title}</span>
              <span className="ml-auto text-[10px] font-semibold uppercase tracking-wide">
                Later
              </span>
            </div>
          );
        }

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-100 hover:text-zinc-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-950",
              isActive && "bg-zinc-100 text-zinc-950",
            )}
          >
            <Icon aria-hidden="true" className="size-[18px]" />
            <span>{item.title}</span>
          </Link>
        );
      })}
    </nav>
  );
}
