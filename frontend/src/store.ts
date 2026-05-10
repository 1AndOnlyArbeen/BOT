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
      partialize: (s) => ({
        mode: s.mode,
        sessionByMode: s.sessionByMode,
        view: s.view,
      }),
    },
  ),
);

export const useSessionId = (): number | null =>
  useStore((s) => s.sessionByMode[s.mode]);
