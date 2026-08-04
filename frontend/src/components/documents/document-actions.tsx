"use client";

import { LoaderCircle, MessagesSquare, RotateCcw, Sparkles } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  hasDocumentFailed,
  isDocumentInProgress,
  isDocumentReady,
  PREPARE_ACTION_LABEL,
} from "@/lib/terminology";
import type { KnowledgeDocument } from "@/types/document";

interface DocumentActionsProps {
  document: KnowledgeDocument;
  onPrepare: (documentId: string, force?: boolean) => void;
  /** True while this row's request is in flight. */
  isSubmitting?: boolean;
  className?: string;
}

/**
 * The single action a document offers, chosen from its status.
 *
 * Users never see separate ingest and index controls: an unprepared document
 * offers "Prepare for chat", a failed one offers a retry, and a ready one
 * offers to chat about it.
 */
export function DocumentActions({
  document,
  onPrepare,
  isSubmitting = false,
  className,
}: DocumentActionsProps) {
  const inProgress = isDocumentInProgress(document.status);
  const busy = isSubmitting || inProgress;

  if (isDocumentReady(document.status)) {
    return (
      <Button asChild size="sm" variant="secondary" className={className}>
        <Link
          href={`/dashboard/chat?knowledgeSpace=${encodeURIComponent(
            document.knowledge_base_id,
          )}`}
        >
          <MessagesSquare aria-hidden="true" />
          Ask about this
        </Link>
      </Button>
    );
  }

  if (hasDocumentFailed(document.status)) {
    return (
      <Button
        size="sm"
        variant="secondary"
        className={className}
        disabled={busy}
        onClick={() => onPrepare(document.id, true)}
      >
        {busy ? (
          <LoaderCircle aria-hidden="true" className="animate-spin" />
        ) : (
          <RotateCcw aria-hidden="true" />
        )}
        Retry
      </Button>
    );
  }

  return (
    <Button
      size="sm"
      variant={inProgress ? "secondary" : "default"}
      className={className}
      disabled={busy}
      onClick={() => onPrepare(document.id)}
    >
      {busy ? (
        <LoaderCircle aria-hidden="true" className="animate-spin" />
      ) : (
        <Sparkles aria-hidden="true" />
      )}
      {inProgress ? "Preparing…" : PREPARE_ACTION_LABEL}
    </Button>
  );
}
