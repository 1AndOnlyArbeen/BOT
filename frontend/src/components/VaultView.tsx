import { useEffect, useState } from "react";
import { KeyRound, Plus, Trash2, Eye, EyeOff } from "lucide-react";
import { api } from "../api";

export function VaultView() {
  const [creds, setCreds] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const [kind, setKind] = useState("api_key");
  const [revealValue, setRevealValue] = useState(false);

  const refresh = () => api.vault().then(setCreds);
  useEffect(() => { refresh(); }, []);

  const handleSave = async () => {
    if (!name.trim() || !value.trim()) return;
    try {
      await api.setCred(name, value, kind);
      setName(""); setValue("");
      setShowForm(false);
      refresh();
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <header className="px-6 py-3 border-b border-border bg-panel flex items-center justify-between">
        <div className="flex items-center gap-2">
          <KeyRound className="w-5 h-5 text-accent2" />
          <h2 className="font-semibold">Credential Vault</h2>
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
          <div className="text-xs text-muted mb-4">
            Stored in OS keyring (libsecret/Keychain). Values are NEVER returned by the API — only metadata.
          </div>

          {showForm && (
            <div className="bg-panel2 border border-border rounded-md p-4 mb-6 space-y-3">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Name (e.g. github_token)"
                className="w-full bg-panel border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent2"
              />
              <select
                value={kind}
                onChange={(e) => setKind(e.target.value)}
                className="w-full bg-panel border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-accent2"
              >
                <option value="api_key">API Key</option>
                <option value="password">Password</option>
                <option value="token">Token</option>
                <option value="secret">Secret</option>
              </select>
              <div className="relative">
                <input
                  type={revealValue ? "text" : "password"}
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  placeholder="Value"
                  className="w-full bg-panel border border-border rounded-md px-3 py-2 pr-10 text-sm font-mono focus:outline-none focus:border-accent2"
                />
                <button
                  onClick={() => setRevealValue(!revealValue)}
                  className="absolute right-2 top-2.5 text-muted hover:text-text"
                >
                  {revealValue ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <button onClick={handleSave} className="w-full px-4 py-2 bg-accent text-white rounded-md text-sm">
                Save to keyring
              </button>
            </div>
          )}

          <div className="space-y-2">
            {creds.map((c) => (
              <div key={c.name} className="flex items-center justify-between bg-panel2 border border-border rounded-md p-3">
                <div>
                  <div className="font-mono text-sm">{c.name}</div>
                  <div className="text-xs text-muted">{c.kind}</div>
                </div>
                <button
                  onClick={async () => { await api.deleteCred(c.name); refresh(); }}
                  className="text-muted hover:text-accent"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            {creds.length === 0 && <div className="text-muted text-sm">No credentials stored.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
