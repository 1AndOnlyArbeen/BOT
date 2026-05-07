import { useEffect, useState } from "react";
import { Zap, Play, Trash2, Plus } from "lucide-react";
import { api } from "../api";
import { useStore } from "../store";
import type { Macro } from "../types";

export function MacrosView() {
  const setView = useStore((s) => s.setView);
  const [macros, setMacros] = useState<Macro[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [description, setDescription] = useState("");

  const refresh = () => api.listMacros().then(setMacros);
  useEffect(() => { refresh(); }, []);

  const handleSave = async () => {
    if (!name.trim() || !prompt.trim()) return;
    await api.saveMacro(name, prompt, description);
    setName(""); setPrompt(""); setDescription("");
    setShowForm(false);
    refresh();
  };

  const handleRun = async (m: Macro) => {
    const macro = await api.runMacro(m.name);
    sessionStorage.setItem("macro_prompt", macro.prompt);
    setView("chat");
    setTimeout(() => {
      const evt = new CustomEvent("ultron-run-macro", { detail: macro.prompt });
      window.dispatchEvent(evt);
    }, 200);
  };

  return (
    <div className="flex flex-col h-full">
      <header className="px-6 py-3 border-b border-border bg-panel flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-accent2" />
          <h2 className="font-semibold">Macros</h2>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-1.5 bg-accent text-white rounded-md text-sm flex items-center gap-1"
        >
          <Plus className="w-4 h-4" /> New
        </button>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto">
          {showForm && (
            <div className="bg-panel2 border border-border rounded-md p-4 mb-6 space-y-3">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Macro name (e.g. morning_brief)"
                className="w-full bg-panel border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent2"
              />
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What does this do?"
                className="w-full bg-panel border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent2"
              />
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="The full prompt to run..."
                rows={4}
                className="w-full bg-panel border border-border rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:border-accent2"
              />
              <div className="flex gap-2">
                <button onClick={handleSave} className="px-4 py-2 bg-accent text-white rounded-md text-sm">
                  Save
                </button>
                <button onClick={() => setShowForm(false)} className="px-4 py-2 bg-panel border border-border rounded-md text-sm">
                  Cancel
                </button>
              </div>
            </div>
          )}

          {macros.length === 0 && (
            <div className="text-muted text-center py-12">
              No macros yet. Save common workflows like <code className="text-accent2">morning_brief</code> or <code className="text-accent2">standup_notes</code>.
            </div>
          )}

          <div className="grid gap-3">
            {macros.map((m) => (
              <div key={m.name} className="bg-panel2 border border-border rounded-md p-4 group">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-accent2 font-semibold">{m.name}</div>
                    {m.description && <div className="text-sm text-muted mt-1">{m.description}</div>}
                    <div className="text-xs text-muted mt-2 font-mono truncate">{m.prompt}</div>
                    <div className="text-xs text-muted mt-2">▶ {m.runs} runs</div>
                  </div>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => handleRun(m)}
                      className="p-2 bg-accent text-white rounded hover:bg-accent/90"
                      title="Run"
                    >
                      <Play className="w-4 h-4" />
                    </button>
                    <button
                      onClick={async () => { await api.deleteMacro(m.name); refresh(); }}
                      className="p-2 text-muted hover:text-accent"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
