"use client";

import * as React from "react";
import { DatabaseZap } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { SidebarNav, type SidebarNavItem } from "@/components/layout/sidebar-nav";
import {
  TopBar,
  type CurrentUserSummary,
  type OrganizationOption,
} from "@/components/layout/top-bar";
import { cn } from "@/lib/utils";

interface AppShellProps {
  children: React.ReactNode;
  organizations?: OrganizationOption[];
  selectedOrganizationId?: string | null;
  onOrganizationChange?: (organizationId: string) => void;
  user?: CurrentUserSummary | null;
  onLogout?: () => void;
  navItems?: SidebarNavItem[];
  environmentLabel?: string;
  contentClassName?: string;
}

function ProductMark() {
  return (
    <div className="flex h-16 items-center gap-3 border-b border-zinc-200 px-5">
      <span className="flex size-8 items-center justify-center rounded-md bg-zinc-900 text-white">
        <DatabaseZap aria-hidden="true" className="size-[18px]" />
      </span>
      <div className="min-w-0 leading-tight">
        <span className="block truncate text-sm font-semibold text-zinc-950">
          AI Support Agent
        </span>
        <span className="block text-xs text-zinc-500">Knowledge workspace</span>
      </div>
    </div>
  );
}

function SidebarContents({
  navItems,
  onNavigate,
}: {
  navItems?: SidebarNavItem[];
  onNavigate?: () => void;
}) {
  return (
    <>
      <ProductMark />
      <div className="flex-1 overflow-y-auto px-3 py-5">
        <SidebarNav items={navItems} onNavigate={onNavigate} />
      </div>
      <div className="border-t border-zinc-200 px-5 py-4">
        <p className="text-xs leading-5 text-zinc-500">
          Grounded answers from your indexed support knowledge.
        </p>
      </div>
    </>
  );
}

export function AppShell({
  children,
  organizations,
  selectedOrganizationId,
  onOrganizationChange,
  user,
  onLogout,
  navItems,
  environmentLabel,
  contentClassName,
}: AppShellProps) {
  const [navigationOpen, setNavigationOpen] = React.useState(false);

  return (
    <div className="min-h-dvh bg-zinc-50 text-zinc-950">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-zinc-200 bg-white lg:flex">
        <SidebarContents navItems={navItems} />
      </aside>

      <Dialog open={navigationOpen} onOpenChange={setNavigationOpen}>
        <DialogContent
          showClose
          className="left-0 top-0 flex h-dvh max-h-none w-[min(20rem,calc(100%-3rem))] max-w-none translate-x-0 translate-y-0 flex-col gap-0 rounded-none border-y-0 border-l-0 p-0 lg:hidden"
        >
          <DialogTitle className="sr-only">Dashboard navigation</DialogTitle>
          <DialogDescription className="sr-only">
            Navigate between product areas.
          </DialogDescription>
          <SidebarContents
            navItems={navItems}
            onNavigate={() => setNavigationOpen(false)}
          />
        </DialogContent>
      </Dialog>

      <div className="min-w-0 lg:pl-64">
        <TopBar
          organizations={organizations}
          selectedOrganizationId={selectedOrganizationId}
          onOrganizationChange={onOrganizationChange}
          user={user}
          onLogout={onLogout}
          onOpenNavigation={() => setNavigationOpen(true)}
          environmentLabel={environmentLabel}
        />
        <main
          id="main-content"
          className={cn(
            "mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8",
            contentClassName,
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
