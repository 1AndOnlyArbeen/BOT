import { useEffect } from "react";
import { Sidebar } from "./components/Sidebar";
import { ChatView } from "./components/ChatView";
import { MemoryView } from "./components/MemoryView";
import { CoderView } from "./components/CoderView";
import { StatsView } from "./components/StatsView";
import { CodebaseView } from "./components/CodebaseView";
import { TrainingView } from "./components/TrainingView";
import { RagView } from "./components/RagView";
import { useStore, useSessionId } from "./store";
import { api } from "./api";

export default function App() {
  const view = useStore((s) => s.view);
  const mode = useStore((s) => s.mode);
  const setSessionId = useStore((s) => s.setSessionId);
  const sessionId = useSessionId();

  useEffect(() => {
    if (sessionId === null) {
      api.listSessions(mode).then(async (sessions) => {
        if (sessions.length > 0) {
          setSessionId(sessions[0].id);
        } else {
          const ns = await api.newSession("New chat", mode);
          setSessionId(ns.id);
        }
      });
    }
  }, [sessionId, mode, setSessionId]);

  return (
    <div className="flex h-screen bg-bg text-text">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0">
        {view === "chat" && <ChatView />}
        {view === "memory" && <MemoryView />}
        {view === "macros" && <MacrosView />}
        {view === "tasks" && <TasksView />}
        {view === "files" && <CoderView />}
        {view === "stats" && <StatsView />}
        {view === "vault" && <VaultView />}
        {view === "codebase" && <CodebaseView />}
        {view === "training" && <TrainingView />}
        {view === "rag" && <RagView />}
      </main>
    </div>
  );
}
