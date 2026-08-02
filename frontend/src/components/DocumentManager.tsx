import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ingestText, listDocuments, removeDocument, uploadFile } from "../api";
import type { DocumentResponse } from "../types";

interface Props {
  token: string;
}

const STATUS_LABEL: Record<DocumentResponse["status"], string> = {
  processing: "processing...",
  ready: "ready",
  failed: "failed",
};

export function DocumentManager({ token }: Props) {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [textName, setTextName] = useState("");
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

  async function handleTextSubmit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim() || !textName.trim()) return;
    setSending(true);
    setError(null);
    try {
      await ingestText(token, text, textName);
      setText("");
      setTextName("");
      await load();
    } catch {
      setError("Unable to submit text.");
    } finally {
      setSending(false);
    }
  }

  async function handleFileSubmit(event: FormEvent) {
    event.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;
    setSending(true);
    setError(null);
    try {
      await uploadFile(token, file);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await load();
    } catch {
      setError("Unable to upload file.");
    } finally {
      setSending(false);
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
        <form className="form-row" onSubmit={handleFileSubmit}>
          <input ref={fileInputRef} type="file" accept="application/pdf" />
          <button type="submit" disabled={sending}>
            Upload PDF
          </button>
        </form>
        <form className="form-column" onSubmit={handleTextSubmit}>
          <input
            placeholder="Document name"
            value={textName}
            onChange={(event) => setTextName(event.target.value)}
          />
          <textarea
            placeholder="Paste text to ingest..."
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={3}
          />
          <button type="submit" disabled={sending}>
            Submit text
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
