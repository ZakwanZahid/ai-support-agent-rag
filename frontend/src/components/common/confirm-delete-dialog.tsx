"use client";

import { LoaderCircle } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ConfirmDeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  /** What is about to be lost, in the user's words. */
  description: React.ReactNode;
  confirmLabel?: string;
  isPending?: boolean;
  onConfirm: () => void;
  /**
   * When set, the button stays disabled until the user types this exactly.
   *
   * Reserved for deletes that take other people's work with them. Asking for
   * it everywhere would train people to type past it, which is the failure
   * mode the friction exists to prevent.
   */
  confirmPhrase?: string;
}

/**
 * The confirmation step in front of anything irreversible.
 *
 * Deliberately names the thing being deleted and what goes with it, rather
 * than asking "Are you sure?" — a user who misread which row they clicked is
 * not helped by a question that repeats no detail back to them.
 */
export function ConfirmDeleteDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Delete",
  isPending = false,
  onConfirm,
  confirmPhrase,
}: ConfirmDeleteDialogProps) {
  return (
    <Dialog open={open} onOpenChange={isPending ? undefined : onOpenChange}>
      <DialogContent className="max-w-md">
        {/*
          The body is a separate component so that closing the dialog unmounts
          it. Radix drops the content when closed, which discards a half-typed
          confirmation phrase without an effect that resets it — the reset
          effect would run on every open and cascade a render.
        */}
        <ConfirmDeleteBody
          title={title}
          description={description}
          confirmLabel={confirmLabel}
          isPending={isPending}
          onCancel={() => onOpenChange(false)}
          onConfirm={onConfirm}
          confirmPhrase={confirmPhrase}
        />
      </DialogContent>
    </Dialog>
  );
}

interface ConfirmDeleteBodyProps
  extends Omit<ConfirmDeleteDialogProps, "open" | "onOpenChange"> {
  onCancel: () => void;
}

function ConfirmDeleteBody({
  title,
  description,
  confirmLabel,
  isPending,
  onCancel,
  onConfirm,
  confirmPhrase,
}: ConfirmDeleteBodyProps) {
  const [typed, setTyped] = useState("");

  const phraseRequired = Boolean(confirmPhrase);
  const phraseMatches = !phraseRequired || typed.trim() === confirmPhrase;

  return (
    <>
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription>{description}</DialogDescription>
      </DialogHeader>

      {phraseRequired ? (
        <div className="flex flex-col gap-2">
          <Label htmlFor="confirm-phrase">
            Type <span className="font-semibold">{confirmPhrase}</span> to confirm
          </Label>
          <Input
            id="confirm-phrase"
            value={typed}
            autoComplete="off"
            onChange={(event) => setTyped(event.target.value)}
          />
        </div>
      ) : null}

      <DialogFooter>
        <Button variant="secondary" disabled={isPending} onClick={onCancel}>
          Cancel
        </Button>
        <Button
          variant="destructive"
          disabled={isPending || !phraseMatches}
          onClick={onConfirm}
        >
          {isPending ? (
            <LoaderCircle aria-hidden="true" className="animate-spin" />
          ) : null}
          {confirmLabel}
        </Button>
      </DialogFooter>
    </>
  );
}
