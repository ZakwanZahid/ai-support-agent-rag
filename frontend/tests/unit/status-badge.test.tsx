import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "@/components/common/status-badge";
import { DOCUMENT_STATUSES } from "@/lib/terminology";

/**
 * The terminology tests prove the mapping is correct in isolation. This proves
 * it survives the trip to the DOM: StatusBadge is where a raw API status
 * would leak to the screen if a component ever stopped asking the module.
 */
describe("StatusBadge", () => {
  it.each([
    ["pending", "Uploaded"],
    ["processing", "Processing"],
    ["processed", "Extracted"],
    ["indexed", "Ready"],
    ["failed", "Failed"],
  ])("renders %s as %s", (status, label) => {
    render(<StatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("never renders the raw API status", () => {
    for (const status of DOCUMENT_STATUSES) {
      const { container, unmount } = render(<StatusBadge status={status} />);
      // "processing" and "failed" happen to be identical in both vocabularies,
      // so only the statuses the product actually renames are asserted here.
      if (!["processing", "failed"].includes(status)) {
        expect(container.textContent?.toLowerCase()).not.toContain(status);
      }
      unmount();
    }
  });

  it("degrades to a neutral badge for an unknown status", () => {
    render(<StatusBadge status="quarantined" />);
    expect(screen.getByText("Unknown")).toBeInTheDocument();
    expect(screen.queryByText("quarantined")).not.toBeInTheDocument();
  });

  it("renders without a status rather than throwing", () => {
    // Documents arriving from a partially-loaded cache can be missing fields.
    render(<StatusBadge />);
    expect(screen.getByText("Unknown")).toBeInTheDocument();
  });
});
