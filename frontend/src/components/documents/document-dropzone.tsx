"use client";

import { FileText, LoaderCircle, Upload, X } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Extensions the ingestion pipeline can extract text from. */
const ACCEPTED_EXTENSIONS = [".pdf", ".txt", ".md", ".docx"] as const;
const ACCEPT_ATTRIBUTE = ACCEPTED_EXTENSIONS.join(",");

function hasSupportedExtension(fileName: string): boolean {
  const lower = fileName.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((extension) => lower.endsWith(extension));
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface DocumentDropzoneProps {
  onFileSelected: (file: File) => void;
  selectedFile?: File | null;
  onClear?: () => void;
  isUploading?: boolean;
  disabled?: boolean;
  className?: string;
}

export function DocumentDropzone({
  onFileSelected,
  selectedFile,
  onClear,
  isUploading = false,
  disabled = false,
  className,
}: DocumentDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [rejectionMessage, setRejectionMessage] = useState<string | null>(null);

  const accept = (file: File | undefined) => {
    if (!file) return;
    if (!hasSupportedExtension(file.name)) {
      setRejectionMessage(
        `${file.name} isn’t a supported file type. Use PDF, TXT, Markdown, or DOCX.`,
      );
      return;
    }
    setRejectionMessage(null);
    onFileSelected(file);
  };

  if (selectedFile) {
    return (
      <div
        className={cn(
          "flex items-center gap-3 rounded-lg border border-border bg-surface p-4",
          className,
        )}
      >
        <span className="flex size-9 shrink-0 items-center justify-center rounded-md border border-border bg-surface-subtle text-foreground-muted">
          {isUploading ? (
            <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
          ) : (
            <FileText aria-hidden="true" className="size-4" />
          )}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">
            {selectedFile.name}
          </p>
          <p className="text-xs text-foreground-subtle">
            {isUploading ? "Uploading…" : formatSize(selectedFile.size)}
          </p>
        </div>
        {onClear && !isUploading ? (
          <Button
            aria-label="Remove file"
            onClick={onClear}
            size="icon"
            variant="ghost"
          >
            <X aria-hidden="true" />
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <div className={className}>
      <div
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setIsDraggingOver(true);
        }}
        onDragLeave={() => setIsDraggingOver(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDraggingOver(false);
          if (disabled) return;
          accept(event.dataTransfer.files?.[0]);
        }}
        className={cn(
          "flex flex-col items-center justify-center rounded-lg border border-dashed px-5 py-10 text-center transition-colors",
          isDraggingOver
            ? "border-primary bg-surface-hover"
            : "border-border-strong bg-surface",
          disabled && "opacity-60",
        )}
      >
        <span className="mb-3 flex size-10 items-center justify-center rounded-md border border-border bg-surface-subtle text-foreground-muted">
          <Upload aria-hidden="true" className="size-5" />
        </span>
        <p className="text-sm font-medium text-foreground">
          Drag and drop a file here
        </p>
        <p className="mt-1 text-xs text-foreground-subtle">
          PDF, TXT, Markdown, or DOCX
        </p>
        <Button
          className="mt-4"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          size="sm"
          variant="secondary"
        >
          Browse files
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT_ATTRIBUTE}
          className="sr-only"
          disabled={disabled}
          onChange={(event) => {
            accept(event.target.files?.[0]);
            // Allow picking the same file again after a failure.
            event.target.value = "";
          }}
        />
      </div>

      {rejectionMessage ? (
        <p role="alert" className="mt-2 text-xs leading-5 text-danger">
          {rejectionMessage}
        </p>
      ) : null}
    </div>
  );
}
