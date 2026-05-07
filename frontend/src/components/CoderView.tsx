import { useEffect, useState } from "react";
import { FolderCode, Save, RefreshCw, FileText } from "lucide-react";
import { api } from "../api";
import type { FileNode } from "../types";

export function CoderView() {
  const [tree, setTree] = useState<FileNode[]>([]);
  const [current, setCurrent] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);

  const refresh = () => api.filesTree().then(setTree);
  useEffect(() => { refresh(); }, []);

  const open = async (path: string) => {
    const f = await api.readFile(path);
    setCurrent(path);
    setContent(f.content);
  };

  const save = async () => {
    if (!current) return;
    setSaving(true);
    await api.writeFile(current, content);
    setSaving(false);
  };

  return (
    <div className="flex h-full">
      <div className="w-72 border-r border-border bg-panel overflow-y-auto">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FolderCode className="w-4 h-4 text-accent2" />
            <span className="text-sm font-semibold">workspace</span>
          </div>
          <button onClick={refresh} className="text-muted hover:text-text">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="p-2">
          {tree.length === 0 && <div className="text-xs text-muted px-2 py-3">(empty)</div>}
          {tree.map((n) => (
            <button
              key={n.path}
              onClick={() => !n.is_dir && open(n.path)}
              disabled={n.is_dir}
              className={`w-full text-left px-2 py-1 rounded text-sm flex items-center gap-1.5 hover:bg-panel2 ${
                current === n.path ? "bg-panel2 text-accent2" : "text-text"
              } ${n.is_dir ? "text-muted" : ""}`}
              style={{ paddingLeft: 8 + n.path.split("/").length * 8 + "px" }}
            >
              <FileText className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">{n.path.split("/").pop()}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        {current ? (
          <>
            <div className="px-4 py-2 bg-panel border-b border-border flex items-center justify-between">
              <span className="font-mono text-sm text-muted">{current}</span>
              <button
                onClick={save}
                disabled={saving}
                className="px-3 py-1 bg-accent text-white rounded flex items-center gap-1 text-sm disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5" />
                {saving ? "Saving..." : "Save"}
              </button>
            </div>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              spellCheck={false}
              className="flex-1 bg-bg text-text p-4 font-mono text-sm resize-none focus:outline-none"
            />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted text-sm">
            Select a file or ask Ultron to create one.
          </div>
        )}
      </div>
    </div>
  );
}
