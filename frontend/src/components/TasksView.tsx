import { useEffect, useState } from "react";
import { ListChecks, Check, Trash2, Plus } from "lucide-react";
import clsx from "clsx";
import { api } from "../api";
import type { Task } from "../types";

export function TasksView() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState<"open" | "done" | "all">("open");
  const [title, setTitle] = useState("");
  const [due, setDue] = useState("");

  const refresh = () => api.tasks(filter).then(setTasks);
  useEffect(() => { refresh(); }, [filter]);

  const handleAdd = async () => {
    if (!title.trim()) return;
    await api.addTask(title, due);
    setTitle(""); setDue("");
    refresh();
  };

  const fmtDue = (d: number | null) =>
    d ? new Date(d * 1000).toLocaleString() : "—";

  return (
    <div className="flex flex-col h-full">
      <header className="px-6 py-3 border-b border-border bg-panel">
        <div className="flex items-center gap-2">
          <ListChecks className="w-5 h-5 text-accent2" />
          <h2 className="font-semibold">Tasks</h2>
        </div>
      </header>

      <div className="px-6 py-3 border-b border-border flex gap-2">
        {(["open", "done", "all"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={clsx(
              "px-3 py-1.5 rounded text-sm capitalize",
              filter === f ? "bg-panel2 text-accent2" : "text-muted hover:text-text",
            )}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto">
          <div className="bg-panel2 border border-border rounded-md p-3 mb-6 flex gap-2">
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              placeholder="New task..."
              className="flex-1 bg-panel border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent2"
            />
            <input
              value={due}
              onChange={(e) => setDue(e.target.value)}
              placeholder="due (e.g. 'tomorrow', '15:00')"
              className="w-44 bg-panel border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent2"
            />
            <button onClick={handleAdd} className="px-4 bg-accent text-white rounded-md flex items-center gap-1">
              <Plus className="w-4 h-4" /> Add
            </button>
          </div>

          <div className="space-y-2">
            {tasks.map((t) => (
              <div key={t.id} className="group flex items-center gap-3 bg-panel2 border border-border rounded-md p-3">
                <button
                  onClick={async () => { await api.patchTask(t.id, t.status === "open" ? "done" : "open"); refresh(); }}
                  className={clsx(
                    "w-5 h-5 rounded border flex items-center justify-center transition-colors",
                    t.status === "done"
                      ? "bg-accent2 border-accent2 text-bg"
                      : "border-muted hover:border-accent2",
                  )}
                >
                  {t.status === "done" && <Check className="w-3 h-3" />}
                </button>
                <div className="flex-1 min-w-0">
                  <div className={clsx("text-sm", t.status === "done" && "line-through text-muted")}>
                    {t.title}
                  </div>
                  <div className="text-xs text-muted mt-0.5">
                    {fmtDue(t.due)} {t.priority && `• ${t.priority}`} {t.project && `• #${t.project}`}
                  </div>
                </div>
                <button
                  onClick={async () => { await api.deleteTask(t.id); refresh(); }}
                  className="opacity-0 group-hover:opacity-100 text-muted hover:text-accent"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            {tasks.length === 0 && <div className="text-muted text-sm text-center py-8">No {filter} tasks.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
