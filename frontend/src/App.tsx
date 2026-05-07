import { useEffect } from "react";
import { Sidebar } from "./components/Sidebar";
import { ChatView } from "./components/ChatView";
import { MemoryView } from "./components/MemoryView";
import { MacrosView } from "./components/MacrosView";
import { TasksView } from "./components/TasksView";
import { CoderView } from "./components/CoderView";
import { StatsView } from "./components/StatsView";
import { VaultView } from "./components/VaultView";
import { CodebaseView } from "./components/CodebaseView";
import { TrainingView } from "./components/TrainingView";
import { useStore } from "./store";
import { api } from "./api";

export default function App() {
  const view = useStore((s) => s.view);
  const setSessionId = useStore((s) => s.setSessionId);
  const sessionId = useStore((s) => s.sessionId);

  useEffect(() => {
    if (sessionId === null) {
      api.listSessions().then(async (sessions) => {
        if (sessions.length > 0) {
          setSessionId(sessions[0].id);
        } else {
          const ns = await api.newSession("New chat");
          setSessionId(ns.id);
        }
      });
    }
  }, [sessionId, setSessionId]);

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
      </main>
    </div>
  );
}
