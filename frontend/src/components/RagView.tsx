import { useEffect, useRef, useState } from "react";
import { Database, Upload, FileText, Trash2, RefreshCw, AlertTriangle } from "lucide-react";
import { api } from "../api";

export function RagView() {
  const [sources, setSources] = useState<string[]>([]);
  const [text, setText] = useState("");
  const [sourceName, setSourceName] = useState("pasted");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string>("");
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = () => api.ragSources().then(setSources).catch(() => {});

  useEffect(() => {
    refresh();
  }, []);

  const flash = (msg: string) => {
    setStatus(msg);
    setTimeout(() => setStatus(""), 3000);
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setBusy(true);
    try {
      const r = await api.ragUpload(Array.from(files));
      flash(`Indexed ${r.chunks} chunk${r.chunks === 1 ? "" : "s"} from ${r.files.length} file${r.files.length === 1 ? "" : "s"}.`);
      refresh();
    } catch (e: any) {
      flash(`Upload failed: ${e.message ?? e}`);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleIngestText = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      const r = await api.ragText(text, sourceName.trim() || "pasted");
      flash(`Indexed ${r.chunks} chunk${r.chunks === 1 ? "" : "s"} under "${r.source}".`);
      setText("");
      refresh();
    } catch (e: any) {
      flash(`Ingest failed: ${e.message ?? e}`);
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteSource = async (name: string) => {
    if (!confirm(`Remove "${name}" from the corpus?`)) return;
    setBusy(true);
    try {
      const r = await api.ragDeleteSource(name);
      flash(`Removed ${r.deleted} chunk${r.deleted === 1 ? "" : "s"}.`);
      refresh();
    } finally {
      setBusy(false);
    }
  };

  const handleResetAll = async () => {
    if (!confirm("Wipe the entire RAG corpus? This can't be undone.")) return;
    setBusy(true);
    try {
      await api.ragReset();
      flash("Corpus cleared.");
      refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-panel">
        <div className="flex items-center gap-2">
          <Database className="w-5 h-5 text-accent2" />
          <h2 className="font-semibold">RAG Corpus</h2>
          <span className="text-xs text-muted">shared across chat / coder / ultron</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refresh}
            className="p-2 text-muted hover:text-text rounded transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleResetAll}
            disabled={busy || sources.length === 0}
            className="px-3 py-1.5 text-xs bg-panel2 border border-border rounded text-muted hover:text-accent hover:border-accent disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1.5"
            title="Wipe entire corpus"
          >
            <AlertTriangle className="w-3.5 h-3.5" /> Reset all
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {status && (
            <div className="bg-accent/10 border border-accent/40 rounded-md px-4 py-2 text-sm text-accent2">
              {status}
            </div>
          )}

          <section className="bg-panel border border-border rounded-md p-4">
            <div className="flex items-center gap-2 mb-3 text-sm font-semibold">
              <Upload className="w-4 h-4 text-accent2" /> Upload files
            </div>
            <p className="text-xs text-muted mb-3">
              Any file type. PDF / DOCX / MD use dedicated loaders; everything
              else is read as text (code, JSON, CSV, logs, …). Binary files
              that can't be decoded are skipped.
            </p>
            <input
              ref={fileRef}
              type="file"
              multiple
              onChange={(e) => handleFiles(e.target.files)}
              disabled={busy}
              className="block w-full text-sm text-muted file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-accent file:text-white file:cursor-pointer hover:file:bg-accent/90 disabled:opacity-50"
            />
          </section>

          <section className="bg-panel border border-border rounded-md p-4">
            <div className="flex items-center gap-2 mb-3 text-sm font-semibold">
              <FileText className="w-4 h-4 text-accent2" /> Paste text
            </div>
            <p className="text-xs text-muted mb-3">
              No size limit — chunked at {500} chars with overlap. Useful for notes,
              transcripts, copy-pasted articles, anything you can't easily save as a file.
            </p>
            <input
              type="text"
              value={sourceName}
              onChange={(e) => setSourceName(e.target.value)}
              placeholder="Source label (e.g. meeting-notes-2026-05)"
              className="w-full mb-2 bg-panel2 border border-border rounded px-3 py-2 text-sm focus:outline-none focus:border-accent2"
            />
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste any amount of text here…"
              rows={10}
              className="w-full bg-panel2 border border-border rounded px-3 py-2 text-sm font-mono resize-y focus:outline-none focus:border-accent2"
            />
            <div className="flex justify-between items-center mt-2">
              <span className="text-xs text-muted">{text.length.toLocaleString()} chars</span>
              <button
                onClick={handleIngestText}
                disabled={busy || !text.trim()}
                className="px-4 py-1.5 bg-accent text-white rounded text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed hover:bg-accent/90 glow"
              >
                Ingest text
              </button>
            </div>
          </section>

          <section className="bg-panel border border-border rounded-md p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Database className="w-4 h-4 text-accent2" /> Sources ({sources.length})
              </div>
            </div>
            {sources.length === 0 ? (
              <div className="text-xs text-muted py-4 text-center">
                No sources yet. Upload a file or paste some text above.
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {sources.map((s) => (
                  <li key={s} className="flex items-center justify-between py-2 text-sm">
                    <span className="font-mono text-text truncate flex-1" title={s}>{s}</span>
                    <button
                      onClick={() => handleDeleteSource(s)}
                      disabled={busy}
                      className="text-muted hover:text-accent ml-3 disabled:opacity-30"
                      title="Remove this source"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
