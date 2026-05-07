import { useEffect, useState } from "react";
import {
  MessageSquare, Brain, Zap, ListChecks, FolderCode,
  BarChart3, KeyRound, Plus, Trash2, Cpu, Wifi, GitBranch, GraduationCap,
} from "lucide-react";
import clsx from "clsx";
import { useStore } from "../store";
import { api } from "../api";
import type { Session, Mode } from "../types";
import { Pagination, paginate } from "./Pagination";

const VIEWS = [
  { id: "chat", icon: MessageSquare, label: "Chat" },
  { id: "codebase", icon: GitBranch, label: "Codebase" },
  { id: "training", icon: GraduationCap, label: "Training" },
  { id: "files", icon: FolderCode, label: "Coder" },
  { id: "memory", icon: Brain, label: "Memory" },
  { id: "macros", icon: Zap, label: "Macros" },
  { id: "tasks", icon: ListChecks, label: "Tasks" },
  { id: "stats", icon: BarChart3, label: "Stats" },
  { id: "vault", icon: KeyRound, label: "Vault" },
] as const;

const MODES: { id: Mode; label: string }[] = [
  { id: "ultron", label: "Ultron" },
  { id: "chat", label: "Chat" },
  { id: "coder", label: "Coder" },
];

export function Sidebar() {
  const view = useStore((s) => s.view);
  const setView = useStore((s) => s.setView);
  const mode = useStore((s) => s.mode);
  const setMode = useStore((s) => s.setMode);
  const sessionId = useStore((s) => s.sessionId);
  const setSessionId = useStore((s) => s.setSessionId);

  const [sessions, setSessions] = useState<Session[]>([]);
  const [model, setModel] = useState<string>("");
  const [sessPage, setSessPage] = useState(1);

  const refresh = () => api.listSessions().then(setSessions);

  useEffect(() => {
    refresh();
    api.health().then((h) => setModel(h.model));
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, []);

  const handleNew = async () => {
    const s = await api.newSession();
    setSessionId(s.id);
    refresh();
    setView("chat");
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    await api.deleteSession(id);
    if (sessionId === id) {
      const remaining = await api.listSessions();
      setSessionId(remaining[0]?.id ?? null);
    }
    refresh();
  };

  return (
    <aside className="w-64 bg-panel border-r border-border flex flex-col">
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Cpu className="w-5 h-5 text-accent" />
          <h1 className="text-xl font-bold tracking-widest brand-text">ULTRON</h1>
        </div>
        <div className="mt-2 flex gap-1">
          <span className="tool-pill text-[10px] px-2 py-0.5 rounded-full">{model}</span>
          <span className="tool-pill text-[10px] px-2 py-0.5 rounded-full flex items-center gap-1">
            <Wifi className="w-3 h-3" /> offline
          </span>
        </div>
      </div>

      <div className="px-3 pt-3">
        <div className="text-[10px] uppercase tracking-wider text-muted mb-2 font-semibold px-1">Mode</div>
        <div className="grid grid-cols-3 gap-1 mb-3">
          {MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={clsx(
                "px-2 py-1.5 rounded-md text-xs font-medium transition-all border",
                mode === m.id
                  ? "bg-accent text-white border-accent glow"
                  : "bg-panel2 border-border hover:border-muted text-muted",
              )}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-3">
        <div className="grid grid-cols-1 gap-0.5 mb-3">
          {VIEWS.map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              onClick={() => setView(id as any)}
              className={clsx(
                "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors",
                view === id
                  ? "bg-panel2 text-accent2"
                  : "text-muted hover:text-text hover:bg-panel2/50",
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {view === "chat" && (
        <>
          <div className="px-3 mt-2">
            <button
              onClick={handleNew}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-accent hover:bg-accent/90 text-white rounded-md text-sm font-medium glow transition-all"
            >
              <Plus className="w-4 h-4" /> New chat
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-2 mt-3">
            <div className="text-[10px] uppercase tracking-wider text-muted mb-1 px-2 font-semibold">
              Recent ({sessions.length})
            </div>
            {paginate(sessions, sessPage).map((s) => (
              <button
                key={s.id}
                onClick={() => {
                  setSessionId(s.id);
                  setView("chat");
                }}
                className={clsx(
                  "group w-full flex items-center justify-between px-3 py-2 rounded-md text-sm text-left transition-colors mb-0.5",
                  sessionId === s.id
                    ? "bg-panel2 text-text"
                    : "text-muted hover:bg-panel2/50 hover:text-text",
                )}
              >
                <span className="truncate flex-1">{s.title}</span>
                <span
                  onClick={(e) => handleDelete(s.id, e)}
                  className="opacity-0 group-hover:opacity-100 hover:text-accent ml-1"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </span>
              </button>
            ))}
            <div className="px-2">
              <Pagination page={sessPage} total={sessions.length} onChange={setSessPage} />
            </div>
          </div>
        </>
      )}

      <div className="border-t border-border p-3">
        <div className="text-[10px] text-muted">v3.0.0 · 100% local</div>
      </div>
    </aside>
  );
}
