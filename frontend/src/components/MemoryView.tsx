import { useEffect, useState } from "react";
import { Brain, Trash2, Plus, Search } from "lucide-react";
import { api } from "../api";
import type { Memory } from "../types";

export function MemoryView() {
  const [facts, setFacts] = useState<Memory[]>([]);
  const [entities, setEntities] = useState<any[]>([]);
  const [triples, setTriples] = useState<any[]>([]);
  const [episodes, setEpisodes] = useState<any[]>([]);
  const [tab, setTab] = useState<"facts" | "kg" | "episodes">("facts");
  const [newFact, setNewFact] = useState("");
  const [search, setSearch] = useState("");

  const refresh = () => {
    api.facts().then(setFacts);
    api.kgEntities().then(setEntities);
    api.kgTriples().then(setTriples);
  };

  useEffect(() => { refresh(); }, []);

  const handleAdd = async () => {
    if (!newFact.trim()) return;
    await api.addFact(newFact);
    setNewFact("");
    refresh();
  };

  const handleDelete = async (text: string) => {
    await api.deleteFact(text);
    refresh();
  };

  const handleSearchEpisodes = async () => {
    if (!search.trim()) return;
    setEpisodes(await api.episodicSearch(search));
  };

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
            <div className="flex gap-2 mb-4">
              <input
                value={newFact}
                onChange={(e) => setNewFact(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                placeholder="Teach me a fact about you..."
                className="flex-1 bg-panel2 border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent2"
              />
              <button
                onClick={handleAdd}
                className="px-4 bg-accent text-white rounded-md flex items-center gap-1 hover:bg-accent/90"
              >
                <Plus className="w-4 h-4" /> Add
              </button>
            </div>
            <div className="text-sm text-muted mb-3">{facts.length} learned facts</div>
            <div className="space-y-2">
              {facts.map((f, i) => (
                <div
                  key={i}
                  className="group flex items-start gap-3 bg-panel2 border-l-2 border-accent2 rounded px-3 py-2"
                >
                  <span className="flex-1 text-sm">{f.text}</span>
                  <button
                    onClick={() => handleDelete(f.text)}
                    className="opacity-0 group-hover:opacity-100 text-muted hover:text-accent"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === "kg" && (
          <div className="max-w-3xl mx-auto">
            <h3 className="text-sm uppercase tracking-wider text-muted mb-2">Top Entities</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-6">
              {entities.slice(0, 18).map((e, i) => (
                <div key={i} className="bg-panel2 border border-border rounded px-3 py-2 text-sm">
                  <div className="font-mono">{e.name}</div>
                  <div className="text-xs text-muted">{e.mentions} mention(s)</div>
                </div>
              ))}
            </div>
            <h3 className="text-sm uppercase tracking-wider text-muted mb-2">Recent Triples</h3>
            <div className="space-y-1 font-mono text-xs">
              {triples.map((t, i) => (
                <div key={i} className="bg-panel2 px-2 py-1 rounded">
                  <span className="text-accent2">{t.s}</span>
                  <span className="text-muted"> — {t.p} — </span>
                  <span className="text-text">{t.o}</span>
                </div>
              ))}
            </div>
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
              {episodes.map((e, i) => (
                <div key={i} className="bg-panel2 border border-border rounded p-3 text-sm whitespace-pre-wrap">
                  {e.text}
                </div>
              ))}
              {episodes.length === 0 && search && (
                <div className="text-muted text-sm">No matching past conversations.</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
