import clsx from "clsx";
import { Trash2 } from "lucide-react";
import type { Session } from "../../types";

interface Props {
  sessions: Session[];
  activeId: number | null;
  onPick: (id: number) => void;
  onDelete: (id: number) => void;
}

export function RagSessionStrip({ sessions, activeId, onPick, onDelete }: Props) {
  if (sessions.length <= 1) return null;
  return (
    <div className="border-b border-border bg-panel/50 px-4 sm:px-6 py-2 overflow-x-auto">
      <div className="flex gap-2 items-center">
        {sessions.map((s) => (
          <div
            key={s.id}
            className={clsx(
              "group flex items-center gap-1 pl-3 pr-2 py-1 rounded text-xs cursor-pointer border whitespace-nowrap",
              activeId === s.id
                ? "bg-panel2 text-text border-border"
                : "text-muted hover:text-text border-transparent",
            )}
            onClick={() => onPick(s.id)}
          >
            <span className="truncate max-w-[160px]">{s.title}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(s.id);
              }}
              className="opacity-0 group-hover:opacity-100 hover:text-accent"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
