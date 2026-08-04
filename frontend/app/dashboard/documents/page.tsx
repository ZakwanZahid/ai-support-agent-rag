"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { PageHeader } from "@/components/common/page-header";
import { DocumentMobileCard } from "@/components/documents/document-mobile-card";
import { DocumentTable } from "@/components/documents/document-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useDocuments } from "@/hooks/use-documents";
import { useWorkspace } from "@/hooks/use-workspace";
import { listKnowledgeBases } from "@/lib/api/knowledge-bases";
import { queryKeys } from "@/lib/query-keys";
import {
  hasDocumentFailed,
  isDocumentInProgress,
  isDocumentReady,
} from "@/lib/terminology";
import { cn } from "@/lib/utils";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "ready", label: "Ready" },
  { key: "processing", label: "Processing" },
  { key: "failed", label: "Failed" },
] as const;

type FilterKey = (typeof FILTERS)[number]["key"];

export default function DocumentsPage() {
  const { activeWorkspace } = useWorkspace();
  const workspaceId = activeWorkspace?.id ?? null;

  const [filter, setFilter] = useState<FilterKey>("all");
  const [search, setSearch] = useState("");

  const {
    documents,
    isLoading,
    isError,
    refetch,
    prepare,
    preparingDocumentId,
  } = useDocuments({ workspaceId });

  const knowledgeSpacesQuery = useQuery({
    queryKey: queryKeys.knowledgeBases(workspaceId),
    queryFn: () => listKnowledgeBases(workspaceId!),
    enabled: Boolean(workspaceId),
  });

  const knowledgeSpaceNames = useMemo(
    () =>
      new Map(
        (knowledgeSpacesQuery.data ?? []).map((space) => [space.id, space.name]),
      ),
    [knowledgeSpacesQuery.data],
  );

  const visibleDocuments = useMemo(() => {
    const term = search.trim().toLowerCase();

    return documents.filter((document) => {
      const matchesFilter =
        filter === "all" ||
        (filter === "ready" && isDocumentReady(document.status)) ||
        (filter === "processing" && isDocumentInProgress(document.status)) ||
        (filter === "failed" && hasDocumentFailed(document.status));

      if (!matchesFilter) return false;
      if (!term) return true;

      // Search covers the knowledge space name too, since that is often how
      // people remember where a document lives.
      const spaceName =
        knowledgeSpaceNames.get(document.knowledge_base_id) ?? "";
      return (
        document.title.toLowerCase().includes(term) ||
        spaceName.toLowerCase().includes(term)
      );
    });
  }, [documents, filter, knowledgeSpaceNames, search]);

  const counts = useMemo(
    () => ({
      all: documents.length,
      ready: documents.filter((d) => isDocumentReady(d.status)).length,
      processing: documents.filter((d) => isDocumentInProgress(d.status)).length,
      failed: documents.filter((d) => hasDocumentFailed(d.status)).length,
    }),
    [documents],
  );

  return (
    <div className="space-y-7">
      <PageHeader
        title="Documents"
        description="Everything your assistant can draw on, across all knowledge spaces."
        actions={
          <Button asChild variant="secondary">
            <Link href="/dashboard/knowledge">Add knowledge</Link>
          </Button>
        }
      />

      {isLoading ? (
        <LoadingSkeleton rows={4} />
      ) : isError ? (
        <ErrorState
          title="We couldn’t load your documents"
          onRetry={() => void refetch()}
        />
      ) : documents.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No documents uploaded yet"
          description="Add PDFs, FAQs, policies, or product docs to prepare your assistant."
          action={
            <Button asChild>
              <Link href="/dashboard/knowledge">Upload document</Link>
            </Button>
          }
        />
      ) : (
        <>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div
              role="group"
              aria-label="Filter by status"
              className="flex flex-wrap gap-1.5"
            >
              {FILTERS.map(({ key, label }) => (
                <button
                  key={key}
                  type="button"
                  aria-pressed={filter === key}
                  onClick={() => setFilter(key)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    filter === key
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-surface text-foreground-muted hover:bg-surface-hover",
                  )}
                >
                  {label}
                  <span className="ml-1.5 opacity-70">{counts[key]}</span>
                </button>
              ))}
            </div>

            <div className="relative sm:w-64">
              <Search
                aria-hidden="true"
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-foreground-subtle"
              />
              <Input
                type="search"
                aria-label="Search documents"
                placeholder="Search documents"
                className="pl-9"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
          </div>

          {visibleDocuments.length === 0 ? (
            <EmptyState
              compact
              icon={Search}
              title="No matching documents"
              description="Try a different search term or filter."
              action={
                <Button
                  variant="secondary"
                  onClick={() => {
                    setSearch("");
                    setFilter("all");
                  }}
                >
                  Clear filters
                </Button>
              }
            />
          ) : (
            <>
              {/*
                Table only from xl. The fixed sidebar takes 240px, so at
                1024 the content column is ~736px and the five columns would
                have to scroll sideways. Cards read better than that.
              */}
              <div className="hidden xl:block">
                <DocumentTable
                  documents={visibleDocuments}
                  knowledgeSpaceNames={knowledgeSpaceNames}
                  onPrepare={prepare}
                  preparingDocumentId={preparingDocumentId}
                />
              </div>

              <ul className="grid gap-3 xl:hidden">
                {visibleDocuments.map((document) => (
                  <DocumentMobileCard
                    key={document.id}
                    document={document}
                    knowledgeSpaceName={knowledgeSpaceNames.get(
                      document.knowledge_base_id,
                    )}
                    onPrepare={prepare}
                    isSubmitting={preparingDocumentId === document.id}
                  />
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </div>
  );
}
