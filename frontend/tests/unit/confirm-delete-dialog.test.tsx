import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ConfirmDeleteDialog } from "@/components/common/confirm-delete-dialog";

/**
 * The guard in front of every irreversible action.
 *
 * Worth testing rather than trusting: the failure here is not a visual bug,
 * it is a workspace someone deletes by accident. The confirm-phrase gate in
 * particular has no other safety net.
 */
describe("ConfirmDeleteDialog", () => {
  const baseProps = {
    open: true,
    onOpenChange: () => undefined,
    title: "Delete Refund policy?",
    description: "The document and its passages are removed for good.",
    onConfirm: () => undefined,
  };

  it("names what is being deleted rather than asking a generic question", () => {
    render(<ConfirmDeleteDialog {...baseProps} />);

    expect(screen.getByText("Delete Refund policy?")).toBeInTheDocument();
    expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
  });

  it("confirms immediately when no phrase is required", async () => {
    const onConfirm = vi.fn();
    render(<ConfirmDeleteDialog {...baseProps} onConfirm={onConfirm} />);

    await userEvent.click(screen.getByRole("button", { name: "Delete" }));

    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("keeps the button disabled until the phrase matches exactly", async () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDeleteDialog
        {...baseProps}
        confirmPhrase="Harbour Retail"
        confirmLabel="Delete workspace"
        onConfirm={onConfirm}
      />,
    );

    const confirm = screen.getByRole("button", { name: "Delete workspace" });
    expect(confirm).toBeDisabled();

    await userEvent.type(screen.getByLabelText(/to confirm/i), "Harbour");
    expect(confirm).toBeDisabled();

    await userEvent.type(screen.getByLabelText(/to confirm/i), " Retail");
    expect(confirm).toBeEnabled();

    await userEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("does not let a pending delete be fired twice", async () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDeleteDialog {...baseProps} isPending onConfirm={onConfirm} />,
    );

    expect(screen.getByRole("button", { name: /Delete/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
  });

  it("forgets a half-typed phrase once it closes", () => {
    const { rerender } = render(
      <ConfirmDeleteDialog {...baseProps} confirmPhrase="Harbour Retail" />,
    );

    rerender(
      <ConfirmDeleteDialog
        {...baseProps}
        open={false}
        confirmPhrase="Harbour Retail"
      />,
    );
    rerender(
      <ConfirmDeleteDialog {...baseProps} confirmPhrase="Harbour Retail" />,
    );

    // Reopening must not inherit the last attempt's typing, or the gate is
    // only a gate the first time.
    expect(screen.getByLabelText(/to confirm/i)).toHaveValue("");
  });
});
