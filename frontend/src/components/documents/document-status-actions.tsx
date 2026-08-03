"use client";

import { Eye, FileCog, Loader2, ScanSearch } from "lucide-react";

import { Button } from "@/components/ui/button";

export interface DocumentActionTarget {
  id: string;
  status?: string | null;
}

interface DocumentStatusActionsProps {
  document: DocumentActionTarget;
  onIngest?: (document: DocumentActionTarget) => void;
  onIndex?: (document: DocumentActionTarget) => void;
  onView?: (document: DocumentActionTarget) => void;
  busyAction?: "ingest" | "index" | null;
  canIngest?: boolean;
  canIndex?: boolean;
  compact?: boolean;
}

export function DocumentStatusActions({
  document,
  onIngest,
  onIndex,
  onView,
  busyAction,
  canIngest,
  canIndex,
  compact = false,
}: DocumentStatusActionsProps) {
  const status = document.status?.toLowerCase() ?? "pending";
  const ingestEnabled =
    canIngest ??
    ["pending", "uploaded", "failed"].includes(status);
  const indexEnabled =
    canIndex ??
    ["processed", "ingested"].includes(status);
  const iconOnly = compact;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {onView ? (
        <Button
          aria-label={iconOnly ? "View document" : undefined}
          size={iconOnly ? "icon" : "sm"}
          variant="ghost"
          onClick={() => onView(document)}
          title="View document"
        >
          <Eye aria-hidden="true" />
          {!iconOnly ? "View" : null}
        </Button>
      ) : null}
      {onIngest ? (
        <Button
          aria-label={iconOnly ? "Ingest document" : undefined}
          size={iconOnly ? "icon" : "sm"}
          variant="outline"
          onClick={() => onIngest(document)}
          disabled={!ingestEnabled || Boolean(busyAction)}
          title={
            ingestEnabled
              ? "Ingest document"
              : "Ingestion is unavailable for this status"
          }
        >
          {busyAction === "ingest" ? (
            <Loader2 aria-hidden="true" className="animate-spin" />
          ) : (
            <FileCog aria-hidden="true" />
          )}
          {!iconOnly ? (busyAction === "ingest" ? "Ingesting" : "Ingest") : null}
        </Button>
      ) : null}
      {onIndex ? (
        <Button
          aria-label={iconOnly ? "Index document" : undefined}
          size={iconOnly ? "icon" : "sm"}
          onClick={() => onIndex(document)}
          disabled={!indexEnabled || Boolean(busyAction)}
          title={
            indexEnabled
              ? "Index document"
              : "Ingest this document before indexing"
          }
        >
          {busyAction === "index" ? (
            <Loader2 aria-hidden="true" className="animate-spin" />
          ) : (
            <ScanSearch aria-hidden="true" />
          )}
          {!iconOnly ? (busyAction === "index" ? "Indexing" : "Index") : null}
        </Button>
      ) : null}
    </div>
  );
}
