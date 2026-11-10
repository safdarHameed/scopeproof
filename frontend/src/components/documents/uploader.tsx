"use client";

import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/cn";
import { documentsApi, errorMessage } from "@/lib/api";
import { plural } from "@/lib/format";
import type { UploadResult } from "@/types/api";

const ACCEPT = ".zip,.eml,.txt,.md,.pdf";

export function UploadSummary({ result }: { result: UploadResult }) {
  const added = result.documents.length;
  return (
    <Alert
      kind={added && !result.skipped.length ? "success" : "warning"}
      title={added ? `Added ${plural(added, "document")}` : "No new documents added"}
    >
      {result.skipped.length > 0 && (
        <ul className="mt-1 space-y-0.5">
          {result.skipped.map((s) => (
            <li key={s.filename}>
              <span className="font-medium">{s.filename}</span>: {s.reason}
            </li>
          ))}
        </ul>
      )}
    </Alert>
  );
}

export function Uploader({
  projectId,
  onUploaded,
  compact = false,
}: {
  projectId: string;
  onUploaded: (result: UploadResult) => void;
  compact?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function upload(files: File[]) {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      onUploaded(await documentsApi.upload(projectId, files));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          upload(Array.from(e.dataTransfer.files));
        }}
        className={cn(
          "relative rounded-2xl border-2 border-dashed bg-white text-center transition",
          compact ? "px-6 py-6" : "px-6 py-12",
          dragging ? "border-brand-500 bg-brand-50" : "border-slate-300 hover:border-slate-400",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="sr-only"
          id={`upload-${projectId}`}
          onChange={(e) => upload(Array.from(e.target.files ?? []))}
          disabled={uploading}
        />
        <label htmlFor={`upload-${projectId}`} className="block cursor-pointer">
          {uploading ? (
            <Spinner className="mx-auto size-8 text-brand-600" />
          ) : (
            <UploadCloud className={cn("mx-auto text-slate-400", compact ? "size-7" : "size-10")} />
          )}
          <p className="mt-3 font-medium text-slate-900">
            {uploading ? "Uploading and extracting text…" : "Drop a ZIP or files here, or browse"}
          </p>
          <p className="mt-1 text-sm text-slate-500">
            ZIP with the contract and emails, or individual .eml, .pdf, .txt and .md files
          </p>
        </label>
      </div>

      {error && <Alert kind="error">{error}</Alert>}
    </div>
  );
}
