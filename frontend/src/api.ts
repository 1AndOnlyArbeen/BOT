import type {
  Session, Message, Memory, Macro, Task,
  FileNode, AuditEntry, ToolInfo, StreamEvent, Mode,
} from "./types";

const API = "/api";

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export const api = {
  health: () => j<{ ok: boolean; model: string }>("/health"),

  listSessions: (mode?: Mode) =>
    j<Session[]>(mode ? `/chat/sessions?mode=${mode}` : "/chat/sessions"),
  newSession: (title = "New chat", mode: Mode = "chat") =>
    j<{ id: number; title: string; mode: Mode }>("/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ title, mode }),
    }),
  deleteSession: (id: number) =>
    j<{ ok: boolean }>(`/chat/sessions/${id}`, { method: "DELETE" }),
  renameSession: (id: number, title: string) =>
    j<{ ok: boolean }>(`/chat/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  listMessages: (id: number) => j<Message[]>(`/chat/sessions/${id}/messages`),

  async streamChat(
    session_id: number,
    message: string,
    mode: Mode,
    use_planner: boolean,
    onEvent: (e: StreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    const r = await fetch(`${API}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id, message, mode, use_planner }),
      signal,
    });
    if (!r.ok || !r.body) throw new Error(`stream failed: ${r.status}`);
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() ?? "";
      for (const p of parts) {
        const line = p.trim();
        if (!line.startsWith("data: ")) continue;
        try {
          onEvent(JSON.parse(line.slice(6)) as StreamEvent);
        } catch {}
      }
    }
  },

  facts: () => j<Memory[]>("/memory/facts"),
  addFact: (text: string) =>
    j<{ saved: number }>("/memory/facts", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  addFactBulk: (text: string, label = "") =>
    j<{ saved: number; chunks: number }>("/memory/facts/text", {
      method: "POST",
      body: JSON.stringify({ text, label }),
    }),
  uploadFactFile: async (file: File, label = "") => {
    const fd = new FormData();
    fd.append("file", file);
    if (label) fd.append("label", label);
    const r = await fetch(`${API}/memory/facts/upload`, { method: "POST", body: fd });
    if (!r.ok) throw new Error(`upload failed: ${r.status}`);
    return r.json() as Promise<{ saved: number; chunks: number; filename: string }>;
  },
  deleteFact: (text: string) =>
    j<{ ok: boolean }>(`/memory/facts?text=${encodeURIComponent(text)}`, {
      method: "DELETE",
    }),

  episodicSearch: (query: string) =>
    j<any[]>("/memory/episodic/search", {
      method: "POST",
      body: JSON.stringify({ query, k: 5 }),
    }),
  episodicStats: () => j<{ count: number }>("/memory/episodic/stats"),
  kgEntities: () => j<any[]>("/memory/kg/entities"),
  kgTriples: () => j<any[]>("/memory/kg/triples"),

  listMacros: () => j<Macro[]>("/macros/"),
  saveMacro: (name: string, prompt: string, description = "") =>
    j<Macro>("/macros/", {
      method: "POST",
      body: JSON.stringify({ name, prompt, description }),
    }),
  deleteMacro: (name: string) =>
    j<{ ok: boolean }>(`/macros/${encodeURIComponent(name)}`, { method: "DELETE" }),
  runMacro: (name: string) =>
    j<Macro>(`/macros/${encodeURIComponent(name)}/run`, { method: "POST" }),

  tasks: (status = "open") => j<Task[]>(`/calendar/tasks?status=${status}`),
  addTask: (title: string, due = "", project = "", priority = "") =>
    j<{ id: number }>("/calendar/tasks", {
      method: "POST",
      body: JSON.stringify({ title, due, project, priority }),
    }),
  patchTask: (id: number, status: string) =>
    j<{ ok: boolean }>(`/calendar/tasks/${id}?status=${status}`, { method: "PATCH" }),
  deleteTask: (id: number) =>
    j<{ ok: boolean }>(`/calendar/tasks/${id}`, { method: "DELETE" }),

  filesTree: () => j<FileNode[]>("/files/tree"),
  readFile: (path: string) =>
    j<{ path: string; content: string }>(`/files/read?path=${encodeURIComponent(path)}`),
  writeFile: (path: string, content: string) =>
    j<{ ok: boolean }>("/files/write", {
      method: "PUT",
      body: JSON.stringify({ path, content }),
    }),
  uploadDocs: async (files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    const r = await fetch(`${API}/files/upload-docs`, { method: "POST", body: fd });
    if (!r.ok) throw new Error("upload failed");
    return r.json() as Promise<{ chunks: number; files: string[] }>;
  },
  listSources: () => j<string[]>("/files/sources"),

  stats: () => j<any>("/stats/"),
  audit: (limit = 100) => j<AuditEntry[]>(`/stats/audit?limit=${limit}`),
  auditByTool: () => j<any>("/stats/audit/by-tool"),

  systemInfo: () => j<any>("/system/info"),
  toolCatalogue: () =>
    j<{ chat: ToolInfo[]; coder: ToolInfo[]; ultron: ToolInfo[] }>("/system/tools"),

  speak: (text: string) =>
    j<{ ok: boolean }>("/voice/speak", { method: "POST", body: JSON.stringify({ text }) }),
  installPiper: () => j<{ message: string }>("/voice/install-piper", { method: "POST" }),
  async stt(blob: Blob): Promise<{ text: string; bytes: number; error?: string }> {
    const fd = new FormData();
    fd.append("audio", blob, "audio.webm");
    const r = await fetch(`${API}/voice/stt`, { method: "POST", body: fd });
    if (!r.ok) throw new Error("stt failed");
    return r.json();
  },

  vault: () => j<any[]>("/vault/"),
  setCred: (name: string, value: string, kind = "secret") =>
    j<{ ok: boolean }>("/vault/", {
      method: "POST",
      body: JSON.stringify({ name, value, kind }),
    }),
  deleteCred: (name: string) =>
    j<{ ok: boolean }>(`/vault/${encodeURIComponent(name)}`, { method: "DELETE" }),

  codebases: () => j<any[]>("/codebase/"),
  codebaseFiles: (repo: string) =>
    j<string[]>(`/codebase/files?repo=${encodeURIComponent(repo)}`),
  ingestCodebaseZip: async (repo: string, file: File) => {
    const fd = new FormData();
    fd.append("repo", repo);
    fd.append("file", file);
    const r = await fetch(`${API}/codebase/ingest-zip`, { method: "POST", body: fd });
    if (!r.ok) throw new Error("upload failed");
    return r.json();
  },
  ingestCodebasePath: (repo: string, path: string) =>
    j<any>("/codebase/ingest-path", {
      method: "POST",
      body: JSON.stringify({ repo, path }),
    }),
  searchCodebase: (query: string, repo = "") =>
    j<any[]>("/codebase/search", {
      method: "POST",
      body: JSON.stringify({ query, repo, k: 8 }),
    }),
  explainCodebase: (action: string, repo = "") =>
    j<{ explanation: string }>("/codebase/explain", {
      method: "POST",
      body: JSON.stringify({ action, repo }),
    }),
  deleteCodebase: (repo: string) =>
    j<{ ok: boolean }>(`/codebase/${encodeURIComponent(repo)}`, { method: "DELETE" }),

  ragSources: () => j<string[]>("/rag/sources"),
  ragUpload: async (files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    const r = await fetch(`${API}/rag/upload`, { method: "POST", body: fd });
    if (!r.ok) throw new Error(`upload failed: ${r.status}`);
    return r.json() as Promise<{ chunks: number; files: string[] }>;
  },
  ragText: (text: string, source = "pasted") =>
    j<{ chunks: number; source: string }>("/rag/text", {
      method: "POST",
      body: JSON.stringify({ text, source }),
    }),
  ragDeleteSource: (name: string) =>
    j<{ ok: boolean; deleted: number }>(
      `/rag/source?name=${encodeURIComponent(name)}`,
      { method: "DELETE" },
    ),
  ragReset: () => j<{ ok: boolean }>("/rag/sources", { method: "DELETE" }),

  seedLibrary: () =>
    j<{ saved: number; topics: Record<string, number> }>("/training/seed", { method: "POST" }),
  libraryEntries: () => j<any[]>("/training/library"),
  learnTopic: (topic: string, doc_url = "") =>
    j<{ message: string }>("/training/learn", {
      method: "POST",
      body: JSON.stringify({ topic, doc_url }),
    }),
};
