"use client";

import { Check, ChevronsUpDown, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import type { Workspace } from "@/types/workspace";

interface WorkspaceSwitcherProps {
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  onSelect: (workspaceId: string) => void;
  onCreate?: () => void;
  className?: string;
}

/** Initials for the workspace tile, e.g. "Acme Support" becomes "AS". */
function workspaceInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) {
    return "W";
  }
  return words
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
}

export function WorkspaceSwitcher({
  workspaces,
  activeWorkspace,
  onSelect,
  onCreate,
  className,
}: WorkspaceSwitcherProps) {
  const hasChoice = workspaces.length > 1;

  if (!activeWorkspace) {
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className={cn(
            "h-10 max-w-[15rem] justify-start gap-2 px-2 text-left",
            className,
          )}
        >
          <span className="flex size-6 shrink-0 items-center justify-center rounded bg-primary text-[11px] font-semibold text-primary-foreground">
            {workspaceInitials(activeWorkspace.name)}
          </span>
          <span className="min-w-0 truncate text-sm font-medium text-foreground">
            {activeWorkspace.name}
          </span>
          <ChevronsUpDown
            aria-hidden="true"
            className="ml-auto size-4 shrink-0 text-foreground-subtle"
          />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuLabel className="normal-case tracking-normal text-foreground-subtle">
          {hasChoice ? "Switch workspace" : "Workspace"}
        </DropdownMenuLabel>

        {workspaces.map((workspace) => {
          const isActive = workspace.id === activeWorkspace.id;
          return (
            <DropdownMenuItem
              key={workspace.id}
              onSelect={() => onSelect(workspace.id)}
            >
              <span className="min-w-0 flex-1 truncate">{workspace.name}</span>
              {isActive ? (
                <Check aria-hidden="true" className="size-4 shrink-0" />
              ) : null}
            </DropdownMenuItem>
          );
        })}

        {onCreate ? (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={onCreate}>
              <Plus aria-hidden="true" />
              Create workspace
            </DropdownMenuItem>
          </>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
