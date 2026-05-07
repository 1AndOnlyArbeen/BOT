import { create } from "zustand";
import type { Mode } from "./types";

interface State {
  mode: Mode;
  sessionId: number | null;
  view: "chat" | "memory" | "macros" | "tasks" | "files" | "stats" | "vault" | "codebase" | "training";
  voiceOut: boolean;
  usePlanner: boolean;
  setMode: (m: Mode) => void;
  setSessionId: (id: number | null) => void;
  setView: (v: State["view"]) => void;
  setVoiceOut: (v: boolean) => void;
  setUsePlanner: (v: boolean) => void;
}

export const useStore = create<State>((set) => ({
  mode: "ultron",
  sessionId: null,
  view: "chat",
  voiceOut: false,
  usePlanner: true,
  setMode: (m) => set({ mode: m }),
  setSessionId: (id) => set({ sessionId: id }),
  setView: (v) => set({ view: v }),
  setVoiceOut: (v) => set({ voiceOut: v }),
  setUsePlanner: (v) => set({ usePlanner: v }),
}));
