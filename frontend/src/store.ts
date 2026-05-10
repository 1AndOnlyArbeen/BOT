import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Mode } from "./types";

type SessionByMode = Record<Mode, number | null>;

interface State {
  mode: Mode;
  sessionByMode: SessionByMode;
  view: "chat" | "memory" | "files" | "stats" | "codebase" | "training" | "rag";
  setMode: (m: Mode) => void;
  setSessionId: (id: number | null) => void;
  setView: (v: State["view"]) => void;
}

export const useStore = create<State>()(
  persist(
    (set) => ({
      mode: "chat",
      sessionByMode: { chat: null, coder: null, rag: null },
      view: "chat",
      setMode: (m) => set({ mode: m }),
      setSessionId: (id) =>
        set((s) => ({
          sessionByMode: { ...s.sessionByMode, [s.mode]: id },
        })),
      setView: (v) => set({ view: v }),
    }),
    {
      name: "ultron-ui",
      version: 2,
      migrate: (persisted: any, fromVersion) => {
        if (fromVersion < 2) {
          const validModes = ["chat", "coder", "rag"];
          const validViews = ["chat", "memory", "files", "stats", "codebase", "training", "rag"];
          return {
            mode: validModes.includes(persisted?.mode) ? persisted.mode : "chat",
            sessionByMode: { chat: null, coder: null, rag: null },
            view: validViews.includes(persisted?.view) ? persisted.view : "chat",
          };
        }
        return persisted;
      },
      partialize: (s) => ({
        mode: s.mode,
        sessionByMode: s.sessionByMode,
        view: s.view,
      }),
    },
  ),
);

export const useSessionId = (): number | null =>
  useStore((s) => s.sessionByMode[s.mode] ?? null);
