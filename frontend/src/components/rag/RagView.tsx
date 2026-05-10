import { useState } from "react";
import { BookOpen, Plus, AlertTriangle, Database } from "lucide-react";
import clsx from "clsx";
import { useRagChat } from "./hooks/useRagChat";
import { useRagCorpus } from "./hooks/useRagCorpus";
import { RagChat } from "./RagChat";
import { RagSessionStrip } from "./RagSessionStrip";
import { RagSourcesPanel } from "./RagSourcesPanel";

export function RagView() {
  const chat = useRagChat();
  const corpus = useRagCorpus();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const corpusEmpty = corpus.sources.length === 0;

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between gap-3 px-4 sm:px-6 py-3 border-b border-border bg-panel shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <BookOpen className="w-5 h-5 text-accent2 shrink-0" />
          <div className="min-w-0">
            <h2 className="font-semibold leading-tight">RAG</h2>
            <p className="text-xs text-muted truncate hidden sm:block">
              Upload documents, then ask — staged retrieval, multi-query, MMR diversity, citation-grounded answers.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setDrawerOpen(true)}
            className="lg:hidden px-3 py-1.5 text-xs bg-panel2 border border-border rounded text-muted hover:text-text flex items-center gap-1.5"
          >
            <Database className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Documents</span>
            <span className="font-mono">({corpus.sources.length})</span>
          </button>
          <button
            onClick={chat.newChat}
            className="px-3 py-1.5 text-xs bg-accent text-white rounded glow flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> <span className="hidden sm:inline">New chat</span>
          </button>
        </div>
      </header>

      <RagSessionStrip
        sessions={chat.sessions}
        activeId={chat.sessionId}
        onPick={chat.setSessionId}
        onDelete={chat.deleteChat}
      />

      {corpus.status && (
        <div className="mx-4 sm:mx-6 mt-3 bg-accent/10 border border-accent/40 rounded-md px-3 py-2 text-xs text-accent2">
          {corpus.status}
        </div>
      )}

      {corpusEmpty && (
        <div className="mx-4 sm:mx-6 mt-3 bg-panel2 border border-border rounded-md px-4 py-3 text-sm flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-accent mt-0.5 shrink-0" />
          <div className="flex-1">
            <div className="font-medium">Your RAG corpus is empty</div>
            <p className="text-xs text-muted mt-1">
              Open the <button className="underline text-accent2" onClick={() => setDrawerOpen(true)}>Documents</button> panel
              and upload a file or paste text to start.
            </p>
          </div>
        </div>
      )}

      <div className="flex-1 flex min-h-0">
        <RagChat chat={chat} corpusEmpty={corpusEmpty} sourceCount={corpus.sources.length} />

        <aside className="hidden lg:flex w-80 xl:w-96 border-l border-border shrink-0">
          <RagSourcesPanel corpus={corpus} />
        </aside>
      </div>

      {/* Mobile/tablet drawer for the documents panel */}
      <div
        className={clsx(
          "lg:hidden fixed inset-0 z-40 transition-opacity",
          drawerOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none",
        )}
      >
        <div
          className="absolute inset-0 bg-black/50"
          onClick={() => setDrawerOpen(false)}
        />
        <aside
          className={clsx(
            "absolute top-0 right-0 h-full w-[88vw] max-w-md bg-bg border-l border-border shadow-2xl transition-transform",
            drawerOpen ? "translate-x-0" : "translate-x-full",
          )}
        >
          <RagSourcesPanel corpus={corpus} onClose={() => setDrawerOpen(false)} />
        </aside>
      </div>
    </div>
  );
}
