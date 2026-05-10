import { useRef, useState } from "react";
import { Database, Upload, FileText, Trash2, RefreshCw, AlertTriangle, X } from "lucide-react";
import type { UseRagCorpus } from "./hooks/useRagCorpus";

interface Props {
  corpus: UseRagCorpus;
  onClose?: () => void;
}

export function RagSourcesPanel({ corpus, onClose }: Props) {
  const [text, setText] = useState("");
  const [sourceName, setSourceName] = useState("pasted");
  const fileRef = useRef<HTMLInputElement>(null);
  const { sources, busy, refresh, uploadFiles, ingestText, deleteSource, resetAll } = corpus;

  return (
    <div className="flex flex-col h-full bg-panel/40">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Database className="w-4 h-4 text-accent2" /> Documents
          <span className="text-xs text-muted">({sources.length})</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={refresh}
            className="p-1.5 text-muted hover:text-text rounded"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={resetAll}
            disabled={busy || sources.length === 0}
            className="p-1.5 text-muted hover:text-accent disabled:opacity-30"
            title="Wipe entire corpus"
          >
            <AlertTriangle className="w-3.5 h-3.5" />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 text-muted hover:text-text rounded lg:hidden"
              title="Close"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        <section className="bg-panel border border-border rounded-md p-3">
          <div className="flex items-center gap-2 mb-2 text-xs font-semibold">
            <Upload className="w-3.5 h-3.5 text-accent2" /> Upload files
          </div>
          <p className="text-[11px] text-muted mb-2">
            PDF, DOCX, MD, TXT, code, JSON, CSV — anything decodable. Add as many as you like.
          </p>
          <input
            ref={fileRef}
            type="file"
            multiple
            onChange={(e) => {
              uploadFiles(e.target.files);
              if (fileRef.current) fileRef.current.value = "";
            }}
            disabled={busy}
            className="block w-full text-xs text-muted file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-accent file:text-white file:cursor-pointer hover:file:bg-accent/90 disabled:opacity-50"
          />
        </section>

        <section className="bg-panel border border-border rounded-md p-3">
          <div className="flex items-center gap-2 mb-2 text-xs font-semibold">
            <FileText className="w-3.5 h-3.5 text-accent2" /> Paste text
          </div>
          <input
            type="text"
            value={sourceName}
            onChange={(e) => setSourceName(e.target.value)}
            placeholder="Source label"
            className="w-full mb-2 bg-panel2 border border-border rounded px-2 py-1.5 text-xs focus:outline-none focus:border-accent2"
          />
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste any text…"
            rows={5}
            className="w-full bg-panel2 border border-border rounded px-2 py-1.5 text-xs font-mono resize-y focus:outline-none focus:border-accent2"
          />
          <div className="flex justify-between items-center mt-2">
            <span className="text-[10px] text-muted">{text.length.toLocaleString()} chars</span>
            <button
              onClick={async () => {
                await ingestText(text, sourceName);
                setText("");
              }}
              disabled={busy || !text.trim()}
              className="px-3 py-1 bg-accent text-white rounded text-xs font-medium disabled:opacity-30 disabled:cursor-not-allowed hover:bg-accent/90"
            >
              Ingest
            </button>
          </div>
        </section>

        <section>
          <div className="flex items-center justify-between mb-2 px-1">
            <div className="text-xs font-semibold text-muted">Sources</div>
          </div>
          {sources.length === 0 ? (
            <div className="text-xs text-muted py-4 text-center bg-panel border border-border rounded">
              No sources yet.
            </div>
          ) : (
            <ul className="space-y-1">
              {sources.map((s) => (
                <li
                  key={s}
                  className="flex items-center gap-2 px-2 py-1.5 text-xs rounded bg-panel border border-border group"
                  title={s}
                >
                  <FileText className="w-3.5 h-3.5 text-muted shrink-0" />
                  <span className="font-mono truncate flex-1">{s}</span>
                  <button
                    onClick={() => deleteSource(s)}
                    disabled={busy}
                    className="text-muted hover:text-accent opacity-0 group-hover:opacity-100 disabled:opacity-30"
                    title="Remove"
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
  );
}
