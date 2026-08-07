/**
 * The single translation layer between backend vocabulary and product language.
 *
 * The API models this domain as organizations, knowledge bases, ingestion and
 * indexing. Users think in workspaces, knowledge spaces, and "is my assistant
 * ready yet". Every user-facing string that describes a backend concept should
 * come from this module, so the mapping stays consistent and is changed in one
 * place rather than re-invented per component.
 */

/** Document lifecycle states as stored by the API. */
export const DOCUMENT_STATUSES = [
  "pending",
  "processing",
  "processed",
  "indexed",
  "failed",
] as const;

export type DocumentStatus = (typeof DOCUMENT_STATUSES)[number];

export type StatusTone = "neutral" | "info" | "warning" | "success" | "danger";

interface DocumentStatusDescriptor {
  /** What the user sees. Never the raw status. */
  label: string;
  tone: StatusTone;
  /** Plain-language explanation of what is happening, for tooltips and detail views. */
  description: string;
  /** True while the backend is still working and the UI should keep polling. */
  isTransient: boolean;
}

const DOCUMENT_STATUS_DESCRIPTORS: Record<
  DocumentStatus,
  DocumentStatusDescriptor
> = {
  pending: {
    label: "Uploaded",
    tone: "neutral",
    description: "Stored and waiting to be prepared.",
    isTransient: false,
  },
  processing: {
    label: "Processing",
    tone: "warning",
    description: "Reading the file and splitting it into passages.",
    isTransient: true,
  },
  processed: {
    label: "Extracted",
    tone: "info",
    description: "Text extracted. Preparing it for chat.",
    isTransient: true,
  },
  indexed: {
    label: "Ready",
    tone: "success",
    description: "Your assistant can answer questions from this document.",
    isTransient: false,
  },
  failed: {
    label: "Failed",
    tone: "danger",
    description: "Something went wrong. You can try preparing it again.",
    isTransient: false,
  },
};

const FALLBACK_DESCRIPTOR: DocumentStatusDescriptor = {
  label: "Unknown",
  tone: "neutral",
  description: "This document is in an unrecognized state.",
  isTransient: false,
};

function normalize(status: string | null | undefined): string {
  return status?.toLowerCase().trim() ?? "";
}

export function isDocumentStatus(
  status: string | null | undefined,
): status is DocumentStatus {
  return (DOCUMENT_STATUSES as readonly string[]).includes(normalize(status));
}

export function describeDocumentStatus(
  status: string | null | undefined,
): DocumentStatusDescriptor {
  const normalized = normalize(status);
  return isDocumentStatus(normalized)
    ? DOCUMENT_STATUS_DESCRIPTORS[normalized]
    : FALLBACK_DESCRIPTOR;
}

export function documentStatusLabel(status: string | null | undefined): string {
  return describeDocumentStatus(status).label;
}

/** A document is usable in chat only once it has been indexed. */
export function isDocumentReady(status: string | null | undefined): boolean {
  return normalize(status) === "indexed";
}

/** Whether the UI should keep polling this document for status changes. */
export function isDocumentInProgress(
  status: string | null | undefined,
): boolean {
  return describeDocumentStatus(status).isTransient;
}

export function hasDocumentFailed(status: string | null | undefined): boolean {
  return normalize(status) === "failed";
}

/**
 * The progress timeline shown while a document is being prepared.
 *
 * `failed` is deliberately absent: it is not a stage users move through, it is
 * an exit from the sequence, and the timeline renders it as an interruption at
 * whichever step was last reached.
 */
export const DOCUMENT_PREPARATION_STAGES = [
  "pending",
  "processing",
  "processed",
  "indexed",
] as const satisfies readonly DocumentStatus[];

export type DocumentPreparationStage =
  (typeof DOCUMENT_PREPARATION_STAGES)[number];

/**
 * How far along the timeline a status sits. Returns -1 for statuses that are
 * not part of the sequence, such as `failed`.
 */
export function preparationStageIndex(
  status: string | null | undefined,
): number {
  const normalized = normalize(status);
  return (DOCUMENT_PREPARATION_STAGES as readonly string[]).indexOf(normalized);
}

/**
 * Product vocabulary, kept here so copy stays consistent and a future rename
 * is a single edit. Backend names appear only as the keys.
 */
export const TERMS = {
  organization: {
    singular: "workspace",
    plural: "workspaces",
    title: "Workspace",
  },
  knowledgeBase: {
    singular: "knowledge space",
    plural: "knowledge spaces",
    title: "Knowledge space",
  },
  document: {
    singular: "document",
    plural: "documents",
    title: "Document",
  },
  conversation: {
    singular: "chat thread",
    plural: "chat threads",
    title: "Chat thread",
  },
  citation: {
    singular: "source",
    plural: "sources",
    title: "Source",
  },
} as const;

/** The one action users see instead of separate ingest and index steps. */
export const PREPARE_ACTION_LABEL = "Prepare for chat";

/**
 * The document filters users see, and the API statuses each one covers.
 *
 * Filtering moved to the server, which means the request has to name raw API
 * statuses. That mapping belongs here rather than in the page: this module is
 * the one place allowed to know both vocabularies, and "Processing" covering
 * two backend statuses is exactly the kind of detail a page should not carry.
 */
export const DOCUMENT_FILTERS = [
  { key: "all", label: "All", statuses: [] },
  { key: "ready", label: "Ready", statuses: ["indexed"] },
  { key: "processing", label: "Processing", statuses: ["processing", "processed"] },
  { key: "failed", label: "Failed", statuses: ["failed"] },
] as const satisfies ReadonlyArray<{
  key: string;
  label: string;
  statuses: readonly DocumentStatus[];
}>;

export type DocumentFilterKey = (typeof DOCUMENT_FILTERS)[number]["key"];

export function documentFilterStatuses(
  key: DocumentFilterKey,
): readonly DocumentStatus[] {
  return (
    DOCUMENT_FILTERS.find((filter) => filter.key === key)?.statuses ?? []
  );
}

/**
 * How many documents a filter would show, from the server's per-status counts.
 *
 * "All" sums every status rather than being sent as its own count, so one
 * grouped query on the server answers every chip.
 */
export function documentFilterCount(
  key: DocumentFilterKey,
  counts: Partial<Record<DocumentStatus, number>>,
): number {
  const statuses = documentFilterStatuses(key);
  const relevant =
    statuses.length > 0
      ? statuses
      : (Object.keys(counts) as DocumentStatus[]);
  return relevant.reduce((total, status) => total + (counts[status] ?? 0), 0);
}
