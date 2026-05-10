import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../../api";
import type { Message, Session, StreamEvent } from "../../../types";
import { CitationHit, INITIAL_STAGES, Stages } from "../types";

const RAG_MODE = "rag" as const;

function parseHits(content: string): CitationHit[] {
  const hits: CitationHit[] = [];
  const re = /\[(\d+)\]\s*\(([^)]+)\)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(content)) !== null) {
    hits.push({ index: Number(m[1]), label: m[2].trim() });
  }
  return hits;
}

export interface UseRagChat {
  sessions: Session[];
  sessionId: number | null;
  setSessionId: (id: number | null) => void;
  messages: Message[];
  input: string;
  setInput: (v: string) => void;
  isStreaming: boolean;
  streamingText: string;
  hits: CitationHit[];
  stages: Stages;
  newChat: () => Promise<void>;
  deleteChat: (id: number) => Promise<void>;
  send: () => Promise<void>;
  stop: () => void;
}

export function useRagChat(): UseRagChat {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [hits, setHits] = useState<CitationHit[]>([]);
  const [stages, setStages] = useState<Stages>(INITIAL_STAGES);
  const abortRef = useRef<AbortController | null>(null);

  const refreshSessions = useCallback(async () => {
    const list = await api.listSessions(RAG_MODE);
    setSessions(list);
    return list;
  }, []);

  useEffect(() => {
    (async () => {
      const list = await refreshSessions();
      if (list.length > 0) {
        setSessionId(list[0].id);
      } else {
        const s = await api.newSession("RAG chat", RAG_MODE);
        setSessionId(s.id);
        refreshSessions();
      }
    })();
  }, [refreshSessions]);

  useEffect(() => {
    if (sessionId !== null) {
      api.listMessages(sessionId).then(setMessages);
      setStreamingText("");
      setHits([]);
      setStages(INITIAL_STAGES);
    }
  }, [sessionId]);

  const newChat = useCallback(async () => {
    const s = await api.newSession("RAG chat", RAG_MODE);
    setSessionId(s.id);
    refreshSessions();
  }, [refreshSessions]);

  const deleteChat = useCallback(
    async (id: number) => {
      if (!confirm("Delete this RAG chat?")) return;
      await api.deleteSession(id);
      const list = await refreshSessions();
      if (sessionId === id) setSessionId(list[0]?.id ?? null);
    },
    [refreshSessions, sessionId],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const send = useCallback(async () => {
    const msg = input.trim();
    if (!msg || sessionId === null || isStreaming) return;

    setInput("");
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setStreamingText("");
    setHits([]);
    setStages(INITIAL_STAGES);
    setIsStreaming(true);

    const ac = new AbortController();
    abortRef.current = ac;

    let final = "";
    try {
      await api.streamChat(
        sessionId,
        msg,
        RAG_MODE,
        false,
        (e: StreamEvent) => {
          switch (e.type) {
            case "rag_stage":
              setStages((prev) => ({
                ...prev,
                [e.data.name]: { status: e.data.status, data: e.data },
              }));
              break;
            case "tool_result":
              if (e.data.name === "rag_search") {
                setHits(parseHits(e.data.content));
              }
              break;
            case "token":
              setStreamingText(e.data);
              break;
            case "final":
              final = e.data;
              setStreamingText(e.data);
              break;
            case "error":
              final = `⚠️ ${e.data}`;
              setStreamingText(final);
              break;
          }
        },
        ac.signal,
      );
    } catch (err: any) {
      if (err.name === "AbortError") {
        final = streamingText || "(stopped)";
      } else {
        final = `⚠️ ${err.message}`;
        setStreamingText(final);
      }
    }

    abortRef.current = null;
    setIsStreaming(false);
    if (final) {
      setMessages((m) => [...m, { role: "assistant", content: final }]);
      setStreamingText("");
    }
    refreshSessions();
  }, [input, isStreaming, refreshSessions, sessionId, streamingText]);

  return {
    sessions,
    sessionId,
    setSessionId,
    messages,
    input,
    setInput,
    isStreaming,
    streamingText,
    hits,
    stages,
    newChat,
    deleteChat,
    send,
    stop,
  };
}
