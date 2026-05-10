import { useEffect, useRef } from "react";
import { Send, Square, BookOpen } from "lucide-react";
import { RagBubble } from "./RagBubble";
import { RagCitations } from "./RagCitations";
import { RagMarkdown } from "./RagMarkdown";
import { RagReasoningTrace } from "./RagReasoningTrace";
import type { UseRagChat } from "./hooks/useRagChat";

interface Props {
  chat: UseRagChat;
  corpusEmpty: boolean;
  sourceCount: number;
}

export function RagChat({ chat, corpusEmpty, sourceCount }: Props) {
  const {
    messages, input, setInput, isStreaming, streamingText,
    hits, stages, send, stop, sessionId,
  } = chat;
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, streamingText, stages]);

  const tracingActive = isStreaming || stages.reason.status === "done";

  return (
    <div className="flex-1 flex flex-col min-w-0">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-6 py-4">
        <div className="max-w-3xl mx-auto">
          {messages.length === 0 && !isStreaming && (
            <div className="text-center py-12 sm:py-20 text-muted">
              <BookOpen className="w-10 h-10 text-accent2 mx-auto mb-3" />
              <h1 className="text-2xl font-semibold mb-2">Ask your documents</h1>
              <p className="text-sm">
                Every answer is grounded in the {sourceCount} indexed source
                {sourceCount === 1 ? "" : "s"}. Off-topic asks are politely declined.
              </p>
            </div>
          )}

          {messages.map((m, i) => (
            <RagBubble key={i} message={m} />
          ))}

          {tracingActive && (
            <div className="my-4">
              <RagReasoningTrace stages={stages} isStreaming={isStreaming} />
              {hits.length > 0 && <RagCitations hits={hits} />}
              {isStreaming && (
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-accent2/20 flex items-center justify-center text-sm">
                    📚
                  </div>
                  <div className="flex-1 prose prose-invert max-w-none">
                    {streamingText ? (
                      <RagMarkdown text={streamingText} />
                    ) : (
                      <div className="flex gap-1.5 mt-2">
                        <span className="typing-dot w-2 h-2 bg-accent rounded-full" />
                        <span className="typing-dot w-2 h-2 bg-accent rounded-full" />
                        <span className="typing-dot w-2 h-2 bg-accent rounded-full" />
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-border bg-panel p-3 sm:p-4">
        <div className="max-w-3xl mx-auto flex gap-2 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder={
              corpusEmpty
                ? "Upload documents first, then ask…"
                : "Ask anything from your documents…"
            }
            rows={1}
            className="flex-1 bg-panel2 border border-border rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:border-accent2 placeholder:text-muted"
            style={{ minHeight: "44px", maxHeight: "200px" }}
            disabled={sessionId === null}
          />
          {isStreaming ? (
            <button
              onClick={stop}
              className="p-3 bg-accent hover:bg-accent/90 text-white rounded-xl glow"
              title="Stop"
            >
              <Square className="w-5 h-5" />
            </button>
          ) : (
            <button
              onClick={send}
              disabled={!input.trim() || sessionId === null}
              className="p-3 bg-accent hover:bg-accent/90 disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-xl glow"
            >
              <Send className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
