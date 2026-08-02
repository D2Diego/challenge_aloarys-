import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ingestText, listDocuments, removeDocument, uploadFile } from "../api";
import type { DocumentResponse } from "../types";

interface Props {
  token: string;
}

type IngestionMode = "pdf" | "text";

const STATUS_LABEL: Record<DocumentResponse["status"], string> = {
  processing: "processing...",
  ready: "ready",
  failed: "failed",
};

export function DocumentManager({ token }: Props) {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [ingestionMode, setIngestionMode] = useState<IngestionMode>("pdf");
  const [documentName, setDocumentName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const data = await listDocuments(token);
      setDocuments(data.documents);
    } catch {
      setError("Unable to load documents.");
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const hasPendingDocument = documents.some(
      (document) => document.status === "processing",
    );
    if (!hasPendingDocument) return;
    const interval = setInterval(load, 2000);
    return () => clearInterval(interval);
  }, [documents, load]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const finalName = documentName.trim();
    if (!finalName) return;
    if (ingestionMode === "pdf" && !file) return;
    if (ingestionMode === "text" && !text.trim()) return;

    setSending(true);
    setError(null);
    try {
      if (ingestionMode === "pdf") {
        await uploadFile(token, file!, finalName);
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
      } else {
        await ingestText(token, text, finalName);
      }
      setText("");
      setDocumentName("");
      await load();
    } catch {
      setError(
        ingestionMode === "pdf"
          ? "Unable to upload PDF."
          : "Unable to submit text.",
      );
    } finally {
      setSending(false);
    }
  }

  function selectMode(mode: IngestionMode) {
    setIngestionMode(mode);
    setError(null);
    if (mode === "pdf") {
      setText("");
    } else {
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleRemove(id: string) {
    try {
      await removeDocument(token, id);
      await load();
    } catch {
      setError("Unable to remove document.");
    }
  }

  return (
    <div className="documents">
      <div className="card">
        <h2>Ingest document</h2>
        <div className="ingestion-toggle" role="group" aria-label="Document type">
          <button
            type="button"
            className={ingestionMode === "pdf" ? "active-ingestion-mode" : ""}
            aria-pressed={ingestionMode === "pdf"}
            disabled={sending}
            onClick={() => selectMode("pdf")}
          >
            PDF
          </button>
          <button
            type="button"
            className={ingestionMode === "text" ? "active-ingestion-mode" : ""}
            aria-pressed={ingestionMode === "text"}
            disabled={sending}
            onClick={() => selectMode("text")}
          >
            Text
          </button>
        </div>
        <form className="form-column ingestion-form" onSubmit={handleSubmit}>
          <label>
            Document name
            <input
              placeholder="Example: Warranty policy"
              value={documentName}
              required
              onChange={(event) => setDocumentName(event.target.value)}
            />
          </label>
          {ingestionMode === "pdf" ? (
            <label>
              PDF file
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                required
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </label>
          ) : (
            <label>
              Document text
              <textarea
                placeholder="Paste text to ingest..."
                value={text}
                required
                onChange={(event) => setText(event.target.value)}
                rows={6}
              />
            </label>
          )}
          <button type="submit" disabled={sending}>
            {sending
              ? "Sending..."
              : ingestionMode === "pdf"
                ? "Upload PDF"
                : "Submit text"}
          </button>
        </form>
        {error && <p className="error">{error}</p>}
      </div>

      <div className="card">
        <h2>Documents ({documents.length})</h2>
        <ul className="document-list">
          {documents.map((document) => (
            <li key={document.id} className={`status-${document.status}`}>
              <div>
                <strong>{document.name}</strong>
                <span className="badge">{STATUS_LABEL[document.status]}</span>
                {document.total_chunks !== null && (
                  <span className="detail"> · {document.total_chunks} chunk(s)</span>
                )}
                {document.error && <p className="document-error">{document.error}</p>}
              </div>
              <button onClick={() => handleRemove(document.id)}>Remove</button>
            </li>
          ))}
          {documents.length === 0 && <p className="empty">No documents yet.</p>}
        </ul>
      </div>
    </div>
  );
}
