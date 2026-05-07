import { useEffect, useState } from "react";
import { GraduationCap, Sparkles, Loader2, BookOpen, Trash2 } from "lucide-react";
import { api } from "../api";

interface Entry { request: string; language: string; ts: number; }

export function TrainingView() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [busy, setBusy] = useState(false);
  const [topic, setTopic] = useState("");
  const [docUrl, setDocUrl] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const refresh = () => api.libraryEntries().then(setEntries);
  useEffect(() => { refresh(); }, []);

  const handleSeed = async () => {
    setBusy(true); setMsg(null);
    try {
      const r = await api.seedLibrary();
      setMsg(`✓ seeded ${r.saved} stack patterns: ${Object.entries(r.topics).map(([k,v]) => `${k} (${v})`).join(", ")}`);
      refresh();
    } catch (e: any) { setMsg(`⚠️ ${e.message}`); }
    setBusy(false);
  };

  const handleLearn = async () => {
    if (!topic.trim()) return;
    setBusy(true); setMsg(null);
    try {
      const r = await api.learnTopic(topic, docUrl);
      setMsg(r.message);
      setTopic(""); setDocUrl("");
      refresh();
    } catch (e: any) { setMsg(`⚠️ ${e.message}`); }
    setBusy(false);
  };

  const filtered = filter
    ? entries.filter((e) =>
        e.request.toLowerCase().includes(filter.toLowerCase()) ||
        e.language.toLowerCase().includes(filter.toLowerCase()),
      )
    : entries;

  return (
    <div className="flex flex-col h-full">
      <header className="px-6 py-3 border-b border-border bg-panel flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GraduationCap className="w-5 h-5 text-accent2" />
          <h2 className="font-semibold">Training</h2>
        </div>
        {busy && <Loader2 className="w-4 h-4 animate-spin text-accent2" />}
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          <section className="bg-panel2 border border-border rounded-md p-5">
            <div className="flex items-start gap-3 mb-3">
              <Sparkles className="w-5 h-5 text-accent2 mt-1" />
              <div>
                <h3 className="font-semibold">One-click stack pack</h3>
                <p className="text-sm text-muted mt-1">
                  Seed the code library with curated patterns: Express, React, MongoDB, Postgres, SQLite, Tailwind, Django, FastAPI, Docker, Kubernetes, JWT auth, testing, websockets, caching, GitHub Actions, and more.
                </p>
              </div>
            </div>
            <button
              onClick={handleSeed}
              disabled={busy}
              className="w-full py-2.5 bg-accent text-white rounded-md hover:bg-accent/90 disabled:opacity-50 font-medium"
            >
              {busy ? "Seeding…" : "Seed all patterns"}
            </button>
          </section>

          <section className="bg-panel2 border border-border rounded-md p-5">
            <div className="flex items-start gap-3 mb-3">
              <BookOpen className="w-5 h-5 text-accent2 mt-1" />
              <div>
                <h3 className="font-semibold">Learn a new topic</h3>
                <p className="text-sm text-muted mt-1">
                  Ultron fetches official docs, extracts working patterns, saves them to memory.
                </p>
              </div>
            </div>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. svelte, astro, graphql, htmx, prisma, redis pub-sub"
              className="w-full bg-panel border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent2 mb-2"
            />
            <input
              value={docUrl}
              onChange={(e) => setDocUrl(e.target.value)}
              placeholder="(optional) official doc URL"
              className="w-full bg-panel border border-border rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:border-accent2 mb-3"
            />
            <button
              onClick={handleLearn}
              disabled={busy || !topic.trim()}
              className="w-full py-2.5 bg-panel border border-border rounded-md hover:border-accent2 disabled:opacity-50"
            >
              Learn this topic
            </button>
          </section>

          {msg && (
            <div className="bg-panel2 border border-accent2/40 rounded-md px-4 py-3 text-sm">
              {msg}
            </div>
          )}

          <section>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm uppercase tracking-wider text-muted font-semibold">
                Code Library ({entries.length})
              </h3>
              <input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="filter…"
                className="bg-panel2 border border-border rounded-md px-3 py-1 text-sm w-44 focus:outline-none focus:border-accent2"
              />
            </div>
            <div className="space-y-1.5">
              {filtered.slice(0, 100).map((e, i) => (
                <div key={i} className="bg-panel2 border border-border rounded-md px-3 py-2 flex items-center justify-between text-sm">
                  <div className="flex-1 min-w-0">
                    <div className="truncate">{e.request}</div>
                  </div>
                  <span className="ml-2 text-xs font-mono px-2 py-0.5 bg-panel rounded text-accent2">
                    {e.language}
                  </span>
                </div>
              ))}
              {filtered.length === 0 && (
                <div className="text-muted text-sm py-8 text-center">
                  Library empty. Click "Seed all patterns" above.
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
