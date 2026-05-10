import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Send, Square, RefreshCw, Copy, Check } from "lucide-react";
import clsx from "clsx";
import { useStore, useSessionId } from "../store";
import { api } from "../api";
import type { Message, StreamEvent } from "../types";

export function ChatView() {
  const sessionId = useSessionId();
  const mode = useStore((s) => s.mode);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [status, setStatus] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (sessionId) {
      api.listMessages(sessionId).then(setMessages);
      setStreamingText("");
      setStatus("");
    }
  }, [sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streamingText]);

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
    setStatus("starting…");
    setIsStreaming(true);

    const ac = new AbortController();
    abortRef.current = ac;

    let final = "";
    try {
      await api.streamChat(sessionId, msg, mode, false, (e: StreamEvent) => {
        switch (e.type) {
          case "router":
            setStatus(
              e.data.categories.length
                ? `routed → ${e.data.categories.join(", ")}`
                : "routing…",
            );
            break;
          case "cli_stage":
            setStatus(`${e.data.name}: ${e.data.summary}`);
            break;
          case "rag_stage":
            setStatus(`${e.data.name}: ${e.data.summary}`);
            break;
          case "tool_call":
            setStatus(`calling ${e.data.name}…`);
            break;
          case "tool_result":
            setStatus(`${e.data.name} → done`);
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
    setStatus("");
    if (final) {
      setMessages((m) => [...m, { role: "assistant", content: final }]);
      setStreamingText("");
    }
    api.listSessions(mode);
  };

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-panel">
        <h2 className="font-semibold capitalize">{mode}</h2>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-6 py-4">
        <div className="max-w-3xl mx-auto">
          {messages.length === 0 && !isStreaming && (
            <div className="text-center py-20 text-muted">
              <h1 className="text-4xl font-bold tracking-widest mb-3 brand-text">ULTRON ONLINE</h1>
              <p>Type a message to get started, boss.</p>
            </div>
          )}

          {messages.map((m, i) => (
            <MessageBubble key={i} message={m} />
          ))}

          {isStreaming && (
            <div className="flex items-start gap-3 my-4">
              <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center text-sm">
                🦾
              </div>
              <div className="flex-1 min-w-0">
                {!streamingText && (
                  <div className="not-prose flex flex-col gap-1.5 mt-2">
                    <div className="flex items-center gap-2 text-sm text-accent2">
                      <span className="flex gap-1.5">
                        <span className="typing-dot w-2 h-2 bg-accent rounded-full" />
                        <span className="typing-dot w-2 h-2 bg-accent rounded-full" />
                        <span className="typing-dot w-2 h-2 bg-accent rounded-full" />
                      </span>
                      <span className="font-medium">Thinking…</span>
                    </div>
                    {status && (
                      <div className="text-xs text-muted font-mono pl-1 truncate">
                        {status}
                      </div>
                    )}
                  </div>
                )}
                {streamingText && (
                  <div className="prose prose-invert max-w-none">
                    {status && (
                      <div className="not-prose flex items-center gap-2 mb-2 text-xs text-muted">
                        <span className="flex gap-1">
                          <span className="typing-dot w-1.5 h-1.5 bg-accent rounded-full" />
                          <span className="typing-dot w-1.5 h-1.5 bg-accent rounded-full" />
                          <span className="typing-dot w-1.5 h-1.5 bg-accent rounded-full" />
                        </span>
                        <span className="font-mono truncate">{status}</span>
                      </div>
                    )}
                    <Markdown text={streamingText} />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-border bg-panel p-3 sm:p-4">
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
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Message Ultron…"
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
