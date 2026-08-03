"use client";

import { ChevronDown, LogOut, Menu, UserRound } from "lucide-react";

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

export interface OrganizationOption {
  id: string;
  name: string;
}

export interface CurrentUserSummary {
  name?: string | null;
  email: string;
}

interface TopBarProps {
  organizations?: OrganizationOption[];
  selectedOrganizationId?: string | null;
  onOrganizationChange?: (organizationId: string) => void;
  user?: CurrentUserSummary | null;
  onLogout?: () => void;
  onOpenNavigation?: () => void;
  environmentLabel?: string;
  className?: string;
}

function getUserLabel(user?: CurrentUserSummary | null) {
  return user?.name?.trim() || user?.email || "Account";
}

export function TopBar({
  organizations = [],
  selectedOrganizationId,
  onOrganizationChange,
  user,
  onLogout,
  onOpenNavigation,
  environmentLabel = "Development",
  className,
}: TopBarProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-zinc-200 bg-white px-4 sm:px-6 lg:px-8",
        className,
      )}
    >
      <Button
        aria-label="Open navigation"
        className="-ml-2 lg:hidden"
        onClick={onOpenNavigation}
        size="icon"
        variant="ghost"
      >
        <Menu aria-hidden="true" />
      </Button>

      <div className="min-w-0 flex-1">
        <label htmlFor="organization-switcher" className="sr-only">
          Active organization
        </label>
        <div className="relative max-w-64">
          <select
            id="organization-switcher"
            value={selectedOrganizationId ?? ""}
            onChange={(event) => onOrganizationChange?.(event.target.value)}
            disabled={organizations.length === 0 || !onOrganizationChange}
            className="h-9 w-full appearance-none truncate rounded-md border border-zinc-200 bg-white py-1 pl-3 pr-8 text-sm font-medium text-zinc-800 outline-none transition-colors focus-visible:border-zinc-400 focus-visible:ring-2 focus-visible:ring-zinc-950/10 disabled:cursor-not-allowed disabled:bg-zinc-50 disabled:text-zinc-500"
          >
            {organizations.length === 0 ? (
              <option value="">No organization</option>
            ) : null}
            {organizations.map((organization) => (
              <option key={organization.id} value={organization.id}>
                {organization.name}
              </option>
            ))}
          </select>
          <ChevronDown
            aria-hidden="true"
            className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-zinc-500"
          />
        </div>
      </div>

      {environmentLabel ? (
        <span className="hidden items-center gap-1.5 text-xs font-medium text-zinc-500 sm:flex">
          <span className="size-1.5 rounded-full bg-emerald-500" />
          {environmentLabel}
        </span>
      ) : null}

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            aria-label="Open account menu"
            className="max-w-48 px-2 sm:px-3"
            variant="ghost"
          >
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-zinc-100 text-zinc-700">
              <UserRound aria-hidden="true" className="size-4" />
            </span>
            <span className="hidden min-w-0 truncate sm:block">
              {getUserLabel(user)}
            </span>
            <ChevronDown aria-hidden="true" className="hidden size-4 sm:block" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="normal-case tracking-normal">
            <span className="block truncate text-sm text-zinc-900">
              {getUserLabel(user)}
            </span>
            {user?.email && user.name ? (
              <span className="mt-0.5 block truncate font-normal text-zinc-500">
                {user.email}
              </span>
            ) : null}
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={onLogout} disabled={!onLogout}>
            <LogOut aria-hidden="true" />
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
