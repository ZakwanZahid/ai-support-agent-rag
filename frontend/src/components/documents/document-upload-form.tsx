"use client";

import { FileUp, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const fileSchema = z.custom<File>(
  (value) => typeof File !== "undefined" && value instanceof File && value.size > 0,
  "Choose a file to upload.",
);

interface DocumentUploadFormProps {
  onUpload: (file: File) => void | Promise<void>;
  disabled?: boolean;
  uploading?: boolean;
  accept?: string;
  maxSizeMb?: number;
}

interface UploadFormValues {
  file: FileList;
}

export function DocumentUploadForm({
  onUpload,
  disabled = false,
  uploading = false,
  accept = ".txt,.md,.pdf",
  maxSizeMb = 10,
}: DocumentUploadFormProps) {
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<UploadFormValues>();

  const submit = handleSubmit(async (values) => {
    const file = values.file?.[0];
    const result = fileSchema.safeParse(file);

    if (!result.success) {
      setError("file", { message: result.error.issues[0]?.message });
      return;
    }

    if (result.data.size > maxSizeMb * 1024 * 1024) {
      setError("file", {
        message: `File must be ${maxSizeMb} MB or smaller.`,
      });
      return;
    }

    try {
      await onUpload(result.data);
      reset();
    } catch {
      // The owning mutation reports the backend error. Preserve the selected
      // file so the user can retry the upload.
    }
  });

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="document-file">Document</Label>
        <Input
          id="document-file"
          type="file"
          accept={accept}
          disabled={disabled || uploading}
          aria-invalid={Boolean(errors.file)}
          aria-describedby="document-file-help document-file-error"
          {...register("file")}
        />
        <p id="document-file-help" className="text-xs leading-5 text-zinc-500">
          Supported file types: {accept.replaceAll(".", "").replaceAll(",", ", ")}.
          Maximum {maxSizeMb} MB.
        </p>
        {errors.file?.message ? (
          <p id="document-file-error" className="text-sm font-medium text-red-700">
            {errors.file.message}
          </p>
        ) : null}
      </div>
      <Button type="submit" disabled={disabled || uploading}>
        {uploading ? (
          <Loader2 aria-hidden="true" className="animate-spin" />
        ) : (
          <FileUp aria-hidden="true" />
        )}
        {uploading ? "Uploading" : "Upload document"}
      </Button>
    </form>
  );
}
