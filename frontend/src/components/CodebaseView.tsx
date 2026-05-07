import { useEffect, useState } from "react";
import { GitBranch, Upload, FolderInput, Trash2, Search, Lightbulb, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { api } from "../api";
import clsx from "clsx";

interface Repo { repo: string; chunks: number; files: number; }
interface Hit {
  path: string;
  symbol: string;
  score: number;
  content: string;
}

export function CodebaseView() {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [activeRepo, setActiveRepo] = useState("");
  const [name, setName] = useState("");
  const [pathInput, setPathInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [busyMsg, setBusyMsg] = useState("");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [explanation, setExplanation] = useState<string | null>(null);

  const refresh = () => api.codebases().then(setRepos);
  useEffect(() => { refresh(); }, []);

  const handleZip = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!name.trim()) { alert("Pick a name first"); return; }
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); setBusyMsg(`Indexing ${file.name}…`);
    try {
      const res = await api.ingestCodebaseZip(name, file);
      setBusyMsg(`✓ indexed ${res.files} files / ${res.chunks} chunks`);
      setName("");
      refresh();
    } catch (e: any) { alert(e.message); }
    setBusy(false);
    setTimeout(() => setBusyMsg(""), 3000);
  };

  const handlePath = async () => {
    if (!name.trim() || !pathInput.trim()) return;
    setBusy(true); setBusyMsg(`Indexing ${pathInput}…`);
    try {
      const res = await api.ingestCodebasePath(name, pathInput);
      if (res.error) {
        alert(res.error);
      } else {
        setBusyMsg(`✓ indexed ${res.files} files / ${res.chunks} chunks`);
        setName(""); setPathInput("");
        refresh();
      }
    } catch (e: any) { alert(e.message); }
    setBusy(false);
    setTimeout(() => setBusyMsg(""), 3000);
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setBusy(true); setBusyMsg("Searching…");
    setExplanation(null);
    setHits(await api.searchCodebase(query, activeRepo));
    setBusy(false); setBusyMsg("");
  };

  const handleExplain = async () => {
    if (!query.trim()) return;
    setBusy(true); setBusyMsg("Reading code & explaining…");
    setExplanation(null);
    const r = await api.explainCodebase(query, activeRepo);
    setExplanation(r.explanation);
    setBusy(false); setBusyMsg("");
  };

  return (
    <div className="flex flex-col h-full">
      <header className="px-6 py-3 border-b border-border bg-panel flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-accent2" />
          <h2 className="font-semibold">Codebase RAG</h2>
        </div>
        {busyMsg && <span className="text-xs text-muted flex items-center gap-2">
          {busy && <Loader2 className="w-3 h-3 animate-spin" />}
          {busyMsg}
        </span>}
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          <section className="bg-panel2 border border-border rounded-md p-4">
            <h3 className="text-sm uppercase tracking-wider text-muted font-semibold mb-3">
              Add a Codebase
            </h3>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Repo name (e.g. vintunastore)"
              className="w-full bg-panel border border-border rounded-md px-3 py-2 text-sm mb-3 focus:outline-none focus:border-accent2"
            />
            <div className="grid md:grid-cols-2 gap-3">
              <label className="cursor-pointer flex items-center justify-center gap-2 bg-panel border border-dashed border-border rounded-md px-4 py-6 hover:border-accent2 transition-colors">
                <Upload className="w-5 h-5 text-accent2" />
                <span className="text-sm">Upload a .zip</span>
                <input type="file" accept=".zip" className="hidden" onChange={handleZip} disabled={busy} />
              </label>
              <div className="bg-panel border border-border rounded-md px-3 py-3 flex flex-col gap-2">
                <div className="flex items-center gap-2 text-sm">
                  <FolderInput className="w-4 h-4 text-accent2" />
                  Index a local path
                </div>
                <input
                  value={pathInput}
                  onChange={(e) => setPathInput(e.target.value)}
                  placeholder="/home/.../my-project"
                  className="bg-panel2 border border-border rounded-md px-2 py-1.5 text-xs font-mono focus:outline-none focus:border-accent2"
                />
                <button
                  onClick={handlePath}
                  disabled={busy || !name.trim() || !pathInput.trim()}
                  className="bg-accent text-white text-sm rounded-md py-1.5 hover:bg-accent/90 disabled:opacity-50"
                >
                  Index path
                </button>
              </div>
            </div>
          </section>

          {repos.length > 0 && (
            <section>
              <h3 className="text-sm uppercase tracking-wider text-muted font-semibold mb-3">
                Indexed Codebases
              </h3>
              <div className="space-y-2">
                {repos.map((r) => (
                  <div
                    key={r.repo}
                    onClick={() => setActiveRepo(activeRepo === r.repo ? "" : r.repo)}
                    className={clsx(
                      "group cursor-pointer flex items-center justify-between px-3 py-2 rounded border bg-panel2 transition-colors",
                      activeRepo === r.repo
                        ? "border-accent2"
                        : "border-border hover:border-muted",
                    )}
                  >
                    <div>
                      <div className="font-mono">{r.repo}</div>
                      <div className="text-xs text-muted">
                        {r.files} files · {r.chunks} chunks
                      </div>
                    </div>
                    <button
                      onClick={async (e) => {
                        e.stopPropagation();
                        if (confirm(`Delete index for ${r.repo}?`)) {
                          await api.deleteCodebase(r.repo);
                          if (activeRepo === r.repo) setActiveRepo("");
                          refresh();
                        }
                      }}
                      className="opacity-0 group-hover:opacity-100 text-muted hover:text-accent"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="bg-panel2 border border-border rounded-md p-4">
            <h3 className="text-sm uppercase tracking-wider text-muted font-semibold mb-3">
              Ask the Codebase
              {activeRepo && (
                <span className="ml-2 text-accent2 normal-case font-mono">@ {activeRepo}</span>
              )}
            </h3>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="how do I create an order?  ·  where is auth handled?  ·  how does the cart flow work?"
              rows={2}
              className="w-full bg-panel border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent2 mb-3 resize-none"
            />
            <div className="flex gap-2">
              <button
                onClick={handleSearch}
                disabled={busy || !query.trim()}
                className="px-4 py-2 bg-panel border border-border rounded-md text-sm flex items-center gap-2 hover:border-accent2 disabled:opacity-50"
              >
                <Search className="w-4 h-4" /> Find code
              </button>
              <button
                onClick={handleExplain}
                disabled={busy || !query.trim()}
                className="px-4 py-2 bg-accent text-white rounded-md text-sm flex items-center gap-2 disabled:opacity-50"
              >
                <Lightbulb className="w-4 h-4" /> Explain how
              </button>
            </div>
          </section>

          {explanation && (
            <section className="bg-panel2 border border-accent2/30 rounded-md p-4">
              <h3 className="text-sm uppercase tracking-wider text-accent2 font-semibold mb-3">
                ✦ How To
              </h3>
              <div className="prose prose-invert max-w-none prose-pre:bg-bg prose-pre:border prose-pre:border-border prose-code:text-accent2">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ inline, className, children, ...props }: any) {
                      const m = /language-(\w+)/.exec(className || "");
                      return !inline && m ? (
                        <SyntaxHighlighter language={m[1]} style={oneDark as any} PreTag="div">
                          {String(children).replace(/\n$/, "")}
                        </SyntaxHighlighter>
                      ) : <code className={className} {...props}>{children}</code>;
                    },
                  }}
                >
                  {explanation}
                </ReactMarkdown>
              </div>
            </section>
          )}

          {hits.length > 0 && (
            <section>
              <h3 className="text-sm uppercase tracking-wider text-muted font-semibold mb-3">
                Code Matches
              </h3>
              <div className="space-y-3">
                {hits.map((h, i) => (
                  <div key={i} className="bg-panel2 border border-border rounded-md overflow-hidden">
                    <div className="px-3 py-2 bg-bg border-b border-border flex items-center justify-between">
                      <div className="text-sm">
                        <span className="font-mono text-accent2">{h.path}</span>
                        {h.symbol && <span className="text-muted ml-2">· {h.symbol}</span>}
                      </div>
                      <span className="text-xs text-muted font-mono">{h.score.toFixed(3)}</span>
                    </div>
                    <pre className="text-xs p-3 overflow-x-auto font-mono whitespace-pre-wrap break-words">
                      {h.content}
                    </pre>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
