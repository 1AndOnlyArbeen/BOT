import clsx from "clsx";
import type { Message } from "../../types";
import { RagMarkdown } from "./RagMarkdown";

export function RagBubble({ message }: { message: Message }) {
  return (
    <div className="flex items-start gap-3 my-4">
      <div
        className={clsx(
          "w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0",
          message.role === "user" ? "bg-panel2" : "bg-accent2/20",
        )}
      >
        {message.role === "user" ? "🧑" : "📚"}
      </div>
      <div className="flex-1 min-w-0">
        {message.role === "user" ? (
          <div className="message-bubble-user rounded-xl px-4 py-2.5 inline-block">
            {message.content}
          </div>
        ) : (
          <RagMarkdown text={message.content} />
        )}
      </div>
    </div>
  );
}
