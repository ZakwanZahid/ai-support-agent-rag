"use client";

import { useState } from "react";

import { ProductMark, Sidebar } from "@/components/layout/sidebar";
import { TopBar } from "@/components/layout/top-bar";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import type { User } from "@/types/auth";
import type { Workspace } from "@/types/workspace";

interface AppShellProps {
  children: React.ReactNode;
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  onWorkspaceSelect: (workspaceId: string) => void;
  onCreateWorkspace?: () => void;
  user: User | null;
  onSignOut: () => void;
  /** Chat needs the full viewport width; most pages read better constrained. */
  fullBleed?: boolean;
  contentClassName?: string;
}

function SidebarPanel({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      <ProductMark />
      <div className="flex-1 overflow-y-auto py-3">
        <Sidebar onNavigate={onNavigate} />
      </div>
    </>
  );
}

export function AppShell({
  children,
  workspaces,
  activeWorkspace,
  onWorkspaceSelect,
  onCreateWorkspace,
  user,
  onSignOut,
  fullBleed = false,
  contentClassName,
}: AppShellProps) {
  const [navigationOpen, setNavigationOpen] = useState(false);

  return (
    <div className="min-h-dvh bg-background">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:text-primary-foreground"
      >
        Skip to content
      </a>

      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r border-border bg-surface lg:flex">
        <SidebarPanel />
      </aside>

      {/* The sidebar becomes a drawer below the lg breakpoint. */}
      <Dialog open={navigationOpen} onOpenChange={setNavigationOpen}>
        <DialogContent
          showClose
          className="left-0 top-0 flex h-dvh max-h-none w-[min(17rem,calc(100%-3rem))] max-w-none translate-x-0 translate-y-0 flex-col gap-0 rounded-none border-y-0 border-l-0 p-0 lg:hidden"
        >
          <DialogTitle className="sr-only">Navigation</DialogTitle>
          <DialogDescription className="sr-only">
            Move between areas of the app.
          </DialogDescription>
          <SidebarPanel onNavigate={() => setNavigationOpen(false)} />
        </DialogContent>
      </Dialog>

      <div className="min-w-0 lg:pl-60">
        <TopBar
          workspaces={workspaces}
          activeWorkspace={activeWorkspace}
          onWorkspaceSelect={onWorkspaceSelect}
          onCreateWorkspace={onCreateWorkspace}
          user={user}
          onSignOut={onSignOut}
          onOpenNavigation={() => setNavigationOpen(true)}
        />

        <main
          id="main-content"
          className={cn(
            fullBleed
              ? "w-full"
              : "mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8",
            contentClassName,
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
