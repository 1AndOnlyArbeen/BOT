import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Mode } from "./types";

type SessionByMode = Record<Mode, number | null>;

interface State {
  mode: Mode;
  sessionByMode: SessionByMode;
  view: "chat" | "memory" | "macros" | "tasks" | "files" | "stats" | "vault" | "codebase" | "training" | "rag";
  voiceOut: boolean;
  usePlanner: boolean;
  setMode: (m: Mode) => void;
  setSessionId: (id: number | null) => void;
  setView: (v: State["view"]) => void;
  setVoiceOut: (v: boolean) => void;
  setUsePlanner: (v: boolean) => void;
}

export const useStore = create<State>()(
  persist(
    (set) => ({
      mode: "ultron",
      sessionByMode: { ultron: null, chat: null, coder: null },
      view: "chat",
      voiceOut: false,
      usePlanner: true,
      setMode: (m) => set({ mode: m }),
      setSessionId: (id) =>
        set((s) => ({
          sessionByMode: { ...s.sessionByMode, [s.mode]: id },
        })),
      setView: (v) => set({ view: v }),
      setVoiceOut: (v) => set({ voiceOut: v }),
      setUsePlanner: (v) => set({ usePlanner: v }),
    }),
    {
      name: "ultron-ui",
      partialize: (s) => ({
        mode: s.mode,
        sessionByMode: s.sessionByMode,
        view: s.view,
        voiceOut: s.voiceOut,
        usePlanner: s.usePlanner,
      }),
    },
  ),
);

export const useSessionId = (): number | null =>
  useStore((s) => s.sessionByMode[s.mode]);
