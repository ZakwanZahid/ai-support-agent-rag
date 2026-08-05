import { describe, expect, it } from "vitest";

import {
  DOCUMENT_PREPARATION_STAGES,
  DOCUMENT_STATUSES,
  PREPARE_ACTION_LABEL,
  TERMS,
  describeDocumentStatus,
  documentStatusLabel,
  hasDocumentFailed,
  isDocumentInProgress,
  isDocumentReady,
  isDocumentStatus,
  preparationStageIndex,
} from "@/lib/terminology";

/**
 * The redesign's central rule is that backend vocabulary never reaches the
 * user. That rule is only as good as this module, so these tests assert the
 * contract itself rather than the current wording of any one label.
 */
describe("terminology", () => {
  describe("status translation", () => {
    it.each([
      ["pending", "Uploaded"],
      ["processing", "Processing"],
      ["processed", "Extracted"],
      ["indexed", "Ready"],
      ["failed", "Failed"],
    ])("translates %s to %s", (status, label) => {
      expect(documentStatusLabel(status)).toBe(label);
    });

    it("gives every known status a label, tone, and description", () => {
      for (const status of DOCUMENT_STATUSES) {
        const descriptor = describeDocumentStatus(status);
        expect(descriptor.label).toBeTruthy();
        expect(descriptor.tone).toBeTruthy();
        expect(descriptor.description).toBeTruthy();
      }
    });

    it("tolerates casing and surrounding whitespace from the API", () => {
      expect(documentStatusLabel("  INDEXED  ")).toBe("Ready");
      expect(isDocumentReady(" Indexed ")).toBe(true);
    });

    it("falls back rather than throwing on an unrecognized status", () => {
      // A new backend status should degrade to something harmless, not crash
      // a list view halfway through rendering.
      expect(documentStatusLabel("quarantined")).toBe("Unknown");
      expect(describeDocumentStatus(null).tone).toBe("neutral");
      expect(describeDocumentStatus(undefined).label).toBe("Unknown");
    });

    it("recognizes only the documented statuses", () => {
      expect(isDocumentStatus("indexed")).toBe(true);
      expect(isDocumentStatus("quarantined")).toBe(false);
      expect(isDocumentStatus(null)).toBe(false);
    });
  });

  describe("no backend vocabulary leaks into user-facing copy", () => {
    // The words the redesign exists to hide. "index" is deliberately absent
    // from this list because it appears inside "indexed", the API status we
    // are translating away from; the label assertions above already cover it.
    const forbidden = [
      "ingest",
      "embedding",
      "vector",
      "chunk",
      "organization",
      "knowledge base",
      "citation",
      "rag",
    ];

    it("keeps status labels and descriptions free of API terms", () => {
      for (const status of DOCUMENT_STATUSES) {
        const { label, description } = describeDocumentStatus(status);
        const copy = `${label} ${description}`.toLowerCase();
        for (const term of forbidden) {
          expect(copy).not.toContain(term);
        }
      }
    });

    it("maps every backend concept to a different product word", () => {
      // If a term ever maps to itself the mapping has silently stopped doing
      // anything, which is the failure mode this module exists to prevent.
      expect(TERMS.organization.singular).not.toBe("organization");
      expect(TERMS.knowledgeBase.singular).not.toBe("knowledge base");
      expect(TERMS.conversation.singular).not.toBe("conversation");
      expect(TERMS.citation.singular).not.toBe("citation");
    });

    it("offers one preparation action, not separate ingest and index steps", () => {
      const action = PREPARE_ACTION_LABEL.toLowerCase();
      expect(action).not.toContain("ingest");
      expect(action).not.toContain("index");
      expect(PREPARE_ACTION_LABEL).toBe("Prepare for chat");
    });
  });

  describe("readiness predicates", () => {
    it("treats only indexed documents as answerable", () => {
      expect(isDocumentReady("indexed")).toBe(true);
      for (const status of ["pending", "processing", "processed", "failed"]) {
        expect(isDocumentReady(status)).toBe(false);
      }
    });

    it("marks the two mid-flight statuses as in progress", () => {
      // These drive polling: getting this wrong either spins forever or stops
      // updating before the document finishes.
      expect(isDocumentInProgress("processing")).toBe(true);
      expect(isDocumentInProgress("processed")).toBe(true);
      expect(isDocumentInProgress("pending")).toBe(false);
      expect(isDocumentInProgress("indexed")).toBe(false);
      expect(isDocumentInProgress("failed")).toBe(false);
    });

    it("never reports a settled document as in progress", () => {
      expect(isDocumentInProgress("indexed")).toBe(false);
      expect(hasDocumentFailed("failed")).toBe(true);
      expect(hasDocumentFailed("indexed")).toBe(false);
    });
  });

  describe("preparation timeline", () => {
    it("runs uploaded to ready in order", () => {
      expect([...DOCUMENT_PREPARATION_STAGES]).toEqual([
        "pending",
        "processing",
        "processed",
        "indexed",
      ]);
    });

    it("excludes failed, which is an exit rather than a stage", () => {
      expect(DOCUMENT_PREPARATION_STAGES).not.toContain("failed");
      expect(preparationStageIndex("failed")).toBe(-1);
    });

    it("advances monotonically through the sequence", () => {
      const indices = DOCUMENT_PREPARATION_STAGES.map(preparationStageIndex);
      expect(indices).toEqual([0, 1, 2, 3]);
    });

    it("returns -1 for anything off the timeline", () => {
      expect(preparationStageIndex("quarantined")).toBe(-1);
      expect(preparationStageIndex(null)).toBe(-1);
    });
  });
});
