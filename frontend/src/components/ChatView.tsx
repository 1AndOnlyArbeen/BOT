import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Send, Volume2, VolumeX, Wand2, Zap, Square, RefreshCw, Copy, Check } from "lucide-react";
import clsx from "clsx";
import { useStore, useSessionId } from "../store";
import { api } from "../api";
import type { Message, StreamEvent, PlanStep } from "../types";
import { VoiceRecorder } from "./VoiceRecorder";

interface PlanState {
  steps: PlanStep[];
  current?: number;
  results: Record<number, { status: string; result: string }>;
}

interface ToolCall {
  name: string;
  args: string;
}

export function ChatView() {
  const sessionId = useSessionId();
  const mode = useStore((s) => s.mode);
  const voiceOut = useStore((s) => s.voiceOut);
  const setVoiceOut = useStore((s) => s.setVoiceOut);
  const usePlanner = useStore((s) => s.usePlanner);
  const setUsePlanner = useStore((s) => s.setUsePlanner);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [plan, setPlan] = useState<PlanState | null>(null);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [routerInfo, setRouterInfo] = useState<string>("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (sessionId) {
      api.listMessages(sessionId).then(setMessages);
      setStreamingText("");
      setPlan(null);
      setToolCalls([]);
    }
  }, [sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streamingText, plan]);

  const handleStop = () => {
    abortRef.current?.abort();
    abortRef.current = null;
  };

  const handleRegenerate = async () => {
    if (isStreaming || messages.length < 2) return;
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    const trimmed = messages.slice(0, -1);
    setMessages(trimmed);
    handleSend(lastUser.content, true);
  };

  const handleSend = async (text?: string, isRegen = false) => {
    const msg = (text ?? input).trim();
    if (!msg || !sessionId || isStreaming) return;

    if (!isRegen) {
      setInput("");
      setMessages((m) => [...m, { role: "user", content: msg }]);
    }
    setStreamingText("");
    setPlan(null);
    setToolCalls([]);
    setRouterInfo("");
    setIsStreaming(true);

    const ac = new AbortController();
    abortRef.current = ac;

    let final = "";
    try {
      await api.streamChat(sessionId, msg, mode, usePlanner, (e: StreamEvent) => {
        switch (e.type) {
          case "router":
            setRouterInfo(`${e.data.categories.join(", ") || "default"} · ${e.data.tool_count} tools`);
            break;
          case "plan":
            setPlan({ steps: e.data.steps, results: {} });
            break;
          case "step_start":
            setPlan((p) => p && { ...p, current: e.data.index });
            break;
          case "step_end":
            setPlan((p) =>
              p && {
                ...p,
                results: { ...p.results, [e.data.index]: { status: e.data.status, result: e.data.result } },
              },
            );
            break;
          case "tool_call":
            setToolCalls((t) => [...t, e.data]);
            break;
          case "token":
            setStreamingText(e.data);
            break;
          case "final":
            final = e.data;
            setStreamingText(e.data);
            break;
          case "plan_done":
            final = e.data.summary || final;
            setStreamingText(e.data.summary || final);
            break;
          case "error":
            final = `⚠️ ${e.data}`;
            setStreamingText(final);
            break;
        }
      }, ac.signal);
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
      if (voiceOut) api.speak(final).catch(() => {});
    }
    api.listSessions(mode);
  };

  const handleVoice = async (blob: Blob) => {
    try {
      const r = await api.stt(blob);
      if (r.text) {
        handleSend(r.text);
      } else if (r.error) {
        setRouterInfo(`🎙 stt error: ${r.error}`);
      } else if (r.bytes < 4000) {
        setRouterInfo("🎙 mic captured almost no audio — check permission / input device");
      } else {
        setRouterInfo("🎙 no speech detected — try speaking louder / longer");
      }
    } catch (e: any) {
      setRouterInfo(`🎙 stt failed: ${e.message ?? e}`);
      console.error(e);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-panel">
        <div className="flex items-center gap-3">
          <h2 className="font-semibold capitalize">{mode}</h2>
          {routerInfo && (
            <span className="text-xs text-muted bg-panel2 px-2 py-1 rounded font-mono">
              🧭 {routerInfo}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setUsePlanner(!usePlanner)}
            title="Plan-then-execute"
            className={clsx(
              "p-2 rounded transition-colors",
              usePlanner ? "text-accent2 bg-panel2" : "text-muted hover:text-text",
            )}
          >
            <Wand2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setVoiceOut(!voiceOut)}
            className={clsx(
              "p-2 rounded transition-colors",
              voiceOut ? "text-accent2 bg-panel2" : "text-muted hover:text-text",
            )}
          >
            {voiceOut ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>
        </div>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4">
        <div className="max-w-3xl mx-auto">
          {messages.length === 0 && !isStreaming && (
            <div className="text-center py-20 text-muted">
              <h1 className="text-4xl font-bold tracking-widest mb-3 brand-text">ULTRON ONLINE</h1>
              <p>Voice or type. I plan, search, code, and control your laptop.</p>
            </div>
          )}

          {messages.map((m, i) => (
            <MessageBubble key={i} message={m} />
          ))}

          {isStreaming && (
            <div className="my-4">
              {plan && <PlanCard plan={plan} />}
              {toolCalls.length > 0 && (
                <details className="mb-3 bg-panel2 border border-border rounded-md px-3 py-2">
                  <summary className="text-xs text-muted cursor-pointer">
                    🔧 {toolCalls.length} tool call{toolCalls.length > 1 ? "s" : ""}
                  </summary>
                  <div className="mt-2 space-y-1">
                    {toolCalls.map((tc, i) => (
                      <div key={i} className="text-xs font-mono text-accent2 truncate">
                        {tc.name}({tc.args})
                      </div>
                    ))}
                  </div>
                </details>
              )}
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center text-sm">
                  🦾
                </div>
                <div className="flex-1 prose prose-invert max-w-none">
                  {streamingText ? (
                    <Markdown text={streamingText} />
                  ) : (
                    <div className="flex gap-1.5 mt-2">
                      <span className="typing-dot w-2 h-2 bg-accent rounded-full" />
                      <span className="typing-dot w-2 h-2 bg-accent rounded-full" />
                      <span className="typing-dot w-2 h-2 bg-accent rounded-full" />
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-border bg-panel p-4">
        <div className="max-w-3xl mx-auto">
          {!isStreaming && messages.length >= 2 && (
            <div className="flex justify-center mb-2">
              <button
                onClick={handleRegenerate}
                className="px-3 py-1 text-xs text-muted hover:text-accent2 bg-panel2 border border-border rounded-md flex items-center gap-1.5"
              >
                <RefreshCw className="w-3 h-3" /> Regenerate
              </button>
            </div>
          )}
          <div className="flex gap-2 items-end">
            <VoiceRecorder onAudio={handleVoice} disabled={isStreaming} />
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder={mode === "ultron" ? "Tell Ultron what to do…" : "Message Ultron…"}
              rows={1}
              className="flex-1 bg-panel2 border border-border rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:border-accent2 placeholder:text-muted"
              style={{ minHeight: "44px", maxHeight: "200px" }}
            />
            {isStreaming ? (
              <button
                onClick={handleStop}
                className="p-3 bg-accent hover:bg-accent/90 text-white rounded-xl glow transition-all"
                title="Stop"
              >
                <Square className="w-5 h-5" />
              </button>
            ) : (
              <button
                onClick={() => handleSend()}
                disabled={!input.trim()}
                className="p-3 bg-accent hover:bg-accent/90 disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-xl glow transition-all"
              >
                <Send className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="group flex items-start gap-3 my-4">
      <div
        className={clsx(
          "w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0",
          message.role === "user" ? "bg-panel2" : "bg-accent/20",
        )}
      >
        {message.role === "user" ? "🧑" : "🦾"}
      </div>
      <div className="flex-1 min-w-0 relative">
        {message.role === "user" ? (
          <div className="message-bubble-user rounded-xl px-4 py-2.5 inline-block">
            {message.content}
          </div>
        ) : (
          <>
            <Markdown text={message.content} />
            <button
              onClick={handleCopy}
              className="absolute -top-1 right-0 opacity-0 group-hover:opacity-100 transition-opacity p-1 text-muted hover:text-accent2"
              title="Copy"
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function PlanCard({ plan }: { plan: PlanState }) {
  return (
    <div className="bg-panel2 border border-border rounded-md px-4 py-3 mb-3">
      <div className="flex items-center gap-2 text-xs text-accent2 mb-2 font-semibold">
        <Zap className="w-3.5 h-3.5" /> EXECUTION PLAN
      </div>
      <div className="space-y-1.5">
        {plan.steps.map((s) => {
          const r = plan.results[s.index];
          const running = plan.current === s.index && !r;
          return (
            <div key={s.index} className="flex items-start gap-2 text-sm">
              <span className="text-muted font-mono mt-0.5">{s.index}.</span>
              <span
                className={clsx(
                  "shrink-0 w-2 h-2 rounded-full mt-1.5",
                  r?.status === "ok" && "bg-accent2",
                  r?.status === "failed" && "bg-accent",
                  running && "bg-accent2 animate-pulse",
                  !r && !running && "bg-muted/40",
                )}
              />
              <div className="flex-1">
                <div className={clsx(running && "text-accent2")}>{s.goal}</div>
                {r && (
                  <div className="text-xs text-muted font-mono mt-0.5 truncate">{r.result}</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Markdown({ text }: { text: string }) {
  return (
    <div className="prose prose-invert max-w-none prose-pre:bg-panel2 prose-pre:border prose-pre:border-border prose-code:text-accent2 prose-code:bg-panel2 prose-code:rounded prose-code:px-1.5 prose-code:py-0.5 prose-code:text-sm">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || "");
            return !inline && match ? (
              <SyntaxHighlighter
                language={match[1]}
                style={oneDark as any}
                PreTag="div"
                customStyle={{ borderRadius: "8px", fontSize: "0.85rem" }}
                {...props}
              >
                {String(children).replace(/\n$/, "")}
              </SyntaxHighlighter>
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
