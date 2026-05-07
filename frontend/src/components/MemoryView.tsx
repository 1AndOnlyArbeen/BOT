import { useEffect, useMemo, useRef, useState } from "react";
import { Brain, Trash2, Plus, Search, FileUp, FileText } from "lucide-react";
import { api } from "../api";
import type { Memory } from "../types";
import { Pagination, paginate } from "./Pagination";

export function MemoryView() {
  const [facts, setFacts] = useState<Memory[]>([]);
  const [entities, setEntities] = useState<any[]>([]);
  const [triples, setTriples] = useState<any[]>([]);
  const [episodes, setEpisodes] = useState<any[]>([]);
  const [tab, setTab] = useState<"facts" | "kg" | "episodes">("facts");
  const [newFact, setNewFact] = useState("");
  const [bulkText, setBulkText] = useState("");
  const [bulkLabel, setBulkLabel] = useState("");
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [factsPage, setFactsPage] = useState(1);
  const [entPage, setEntPage] = useState(1);
  const [tripPage, setTripPage] = useState(1);
  const [epPage, setEpPage] = useState(1);

  const refresh = () => {
    api.facts().then(setFacts);
    api.kgEntities().then(setEntities);
    api.kgTriples().then(setTriples);
  };

  useEffect(() => {
    refresh();
  }, []);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return facts;
    return facts.filter((f) => f.text.toLowerCase().includes(q));
  }, [facts, filter]);

  useEffect(() => {
    setFactsPage(1);
  }, [filter, facts.length]);

  const handleAdd = async () => {
    if (!newFact.trim()) return;
    await api.addFact(newFact);
    setNewFact("");
    refresh();
  };

  const handleBulkSave = async () => {
    if (!bulkText.trim()) return;
    setBusy(true);
    setStatus("");
    try {
      const r = await api.addFactBulk(bulkText, bulkLabel);
      setStatus(`Saved ${r.saved} entr${r.saved === 1 ? "y" : "ies"} (${r.chunks} chunk${r.chunks === 1 ? "" : "s"}).`);
      setBulkText("");
      setBulkLabel("");
      refresh();
    } catch (e: any) {
      setStatus(`Error: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setStatus("");
    try {
      const r = await api.uploadFactFile(file, bulkLabel);
      setStatus(`Uploaded ${r.filename}: saved ${r.saved} entr${r.saved === 1 ? "y" : "ies"} (${r.chunks} chunk${r.chunks === 1 ? "" : "s"}).`);
      setBulkLabel("");
      refresh();
    } catch (err: any) {
      setStatus(`Error: ${err.message}`);
    } finally {
      setBusy(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (text: string) => {
    await api.deleteFact(text);
    refresh();
  };

  const handleSearchEpisodes = async () => {
    if (!search.trim()) return;
    setEpPage(1);
    setEpisodes(await api.episodicSearch(search));
  };

  const factsPaged = paginate(filtered, factsPage);
  const entitiesPaged = paginate(entities, entPage);
  const triplesPaged = paginate(triples, tripPage);
  const episodesPaged = paginate(episodes, epPage);

  return (
    <div className="flex flex-col h-full">
      <header className="px-6 py-3 border-b border-border bg-panel">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-accent2" />
          <h2 className="font-semibold">Memory</h2>
        </div>
      </header>

      <div className="px-6 py-2 border-b border-border flex gap-2">
        {(["facts", "kg", "episodes"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 rounded text-sm capitalize ${
              tab === t ? "bg-panel2 text-accent2" : "text-muted hover:text-text"
            }`}
          >
            {t === "kg" ? "Knowledge Graph" : t}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {tab === "facts" && (
          <div className="max-w-3xl mx-auto">
            {/* Quick add */}
            <div className="flex gap-2 mb-4">
              <input
                value={newFact}
                onChange={(e) => setNewFact(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                placeholder="Teach me a one-line fact..."
                className="flex-1 bg-panel2 border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent2"
              />
              <button
                onClick={handleAdd}
                className="px-4 bg-accent text-white rounded-md flex items-center gap-1 hover:bg-accent/90"
              >
                <Plus className="w-4 h-4" /> Add
              </button>
            </div>

            {/* Bulk text + file upload */}
            <details className="mb-4 bg-panel2 border border-border rounded-md" open>
              <summary className="px-3 py-2 cursor-pointer text-sm font-medium flex items-center gap-2">
                <FileText className="w-4 h-4 text-accent2" />
                Add long text or upload a file
              </summary>
              <div className="p-3 border-t border-border space-y-2">
                <input
                  value={bulkLabel}
                  onChange={(e) => setBulkLabel(e.target.value)}
                  placeholder="Optional label (e.g. project-notes, meeting-2026-05-01)"
                  className="w-full bg-panel border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent2"
                />
                <textarea
                  value={bulkText}
                  onChange={(e) => setBulkText(e.target.value)}
                  placeholder="Paste any amount of text here — long notes, transcripts, docs. Will be saved as one or more memory entries."
                  rows={8}
                  className="w-full bg-panel border border-border rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:border-accent2 resize-y"
                />
                <div className="flex flex-wrap gap-2 items-center">
                  <button
                    onClick={handleBulkSave}
                    disabled={busy || !bulkText.trim()}
                    className="px-4 py-2 bg-accent text-white rounded-md text-sm flex items-center gap-1 hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Plus className="w-4 h-4" /> Save text
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".txt,.md,.markdown,.log,.json,.csv,.tsv,.yaml,.yml,.py,.js,.ts,.tsx,.jsx,.html,.css,.sh,.sql,.xml,.toml,.ini,.conf,text/*,application/json"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={busy}
                    className="px-4 py-2 bg-panel border border-border rounded-md text-sm flex items-center gap-1 hover:border-accent2 disabled:opacity-50"
                  >
                    <FileUp className="w-4 h-4" /> Upload file
                  </button>
                  <span className="text-xs text-muted">UTF-8 text up to 5 MB</span>
                </div>
                {status && (
                  <div className="text-xs text-accent2 pt-1">{status}</div>
                )}
              </div>
            </details>

            {/* Filter + count */}
            <div className="flex items-center gap-2 mb-3">
              <input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter facts..."
                className="flex-1 bg-panel2 border border-border rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-accent2"
              />
              <div className="text-sm text-muted whitespace-nowrap">
                {filtered.length} / {facts.length}
              </div>
            </div>

            {/* List */}
            <div className="space-y-2">
              {factsPaged.map((f, i) => (
                <div
                  key={i}
                  className="group flex items-start gap-3 bg-panel2 border-l-2 border-accent2 rounded px-3 py-2"
                >
                  <span className="flex-1 text-sm whitespace-pre-wrap break-words">{f.text}</span>
                  <button
                    onClick={() => handleDelete(f.text)}
                    className="opacity-0 group-hover:opacity-100 text-muted hover:text-accent shrink-0"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
              {filtered.length === 0 && (
                <div className="text-muted text-sm">No facts yet. Add one above.</div>
              )}
            </div>
            <Pagination page={factsPage} total={filtered.length} onChange={setFactsPage} />
          </div>
        )}

        {tab === "kg" && (
          <div className="max-w-3xl mx-auto">
            <h3 className="text-sm uppercase tracking-wider text-muted mb-2">
              Entities ({entities.length})
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-2">
              {entitiesPaged.map((e, i) => (
                <div key={i} className="bg-panel2 border border-border rounded px-3 py-2 text-sm">
                  <div className="font-mono">{e.name}</div>
                  <div className="text-xs text-muted">{e.mentions} mention(s)</div>
                </div>
              ))}
            </div>
            <Pagination page={entPage} total={entities.length} onChange={setEntPage} />

            <h3 className="text-sm uppercase tracking-wider text-muted mt-6 mb-2">
              Triples ({triples.length})
            </h3>
            <div className="space-y-1 font-mono text-xs">
              {triplesPaged.map((t, i) => (
                <div key={i} className="bg-panel2 px-2 py-1 rounded">
                  <span className="text-accent2">{t.s}</span>
                  <span className="text-muted"> — {t.p} — </span>
                  <span className="text-text">{t.o}</span>
                </div>
              ))}
            </div>
            <Pagination page={tripPage} total={triples.length} onChange={setTripPage} />
          </div>
        )}

        {tab === "episodes" && (
          <div className="max-w-3xl mx-auto">
            <div className="flex gap-2 mb-4">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearchEpisodes()}
                placeholder="Search past conversations..."
                className="flex-1 bg-panel2 border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent2"
              />
              <button
                onClick={handleSearchEpisodes}
                className="px-4 bg-accent text-white rounded-md flex items-center gap-1"
              >
                <Search className="w-4 h-4" /> Search
              </button>
            </div>
            <div className="space-y-3">
              {episodesPaged.map((e, i) => (
                <div key={i} className="bg-panel2 border border-border rounded p-3 text-sm whitespace-pre-wrap">
                  {e.text}
                </div>
              ))}
              {episodes.length === 0 && search && (
                <div className="text-muted text-sm">No matching past conversations.</div>
              )}
            </div>
            <Pagination page={epPage} total={episodes.length} onChange={setEpPage} />
          </div>
        )}
      </div>
    </div>
  );
}
