import { useState } from "react";
import { ChevronDown, ChevronRight, Brain, Sparkles, Search, ListOrdered, Layers, Lightbulb, MessagesSquare } from "lucide-react";
import clsx from "clsx";
import type { RagStageName } from "../../types";
import type { Stages } from "./types";
import { STAGE_LABEL, STAGE_ORDER } from "./types";

const STAGE_ICON: Record<RagStageName, typeof Brain> = {
  contextualize: MessagesSquare,
  analyze: Brain,
  expand: Sparkles,
  retrieve: Search,
  rerank: ListOrdered,
  assemble: Layers,
  reason: Lightbulb,
};

interface Props {
  stages: Stages;
  isStreaming: boolean;
}

export function RagReasoningTrace({ stages, isStreaming }: Props) {
  const [expanded, setExpanded] = useState(false);
  const visibleStages = STAGE_ORDER.filter((n) => stages[n].status !== "pending");
  if (visibleStages.length === 0) return null;

  const doneCount = visibleStages.filter((n) => stages[n].status === "done").length;
  const total = visibleStages.length;
  const headerLabel = isStreaming
    ? `Reasoning · ${doneCount}/${total} stages`
    : `Reasoning · ${total} stages complete`;

  return (
    <div className="mb-3 bg-panel2 border border-border rounded-md overflow-hidden">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-panel/50"
      >
        <span className="flex items-center gap-2 text-accent2 font-medium">
          {expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          🧠 {headerLabel}
        </span>
        <span className="flex gap-1">
          {visibleStages.map((name) => (
            <span
              key={name}
              className={clsx(
                "w-1.5 h-1.5 rounded-full",
                stages[name].status === "done" && "bg-accent2",
                stages[name].status === "running" && "bg-accent animate-pulse",
              )}
              title={`${STAGE_LABEL[name]}: ${stages[name].status}`}
            />
          ))}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-border px-3 py-2 space-y-2">
          {visibleStages.map((name) => {
            const stage = stages[name];
            const Icon = STAGE_ICON[name];
            return (
              <div key={name} className="flex items-start gap-2 text-xs">
                <Icon
                  className={clsx(
                    "w-3.5 h-3.5 mt-0.5 shrink-0",
                    stage.status === "running" ? "text-accent animate-pulse" : "text-accent2",
                  )}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{STAGE_LABEL[name]}</span>
                    <span className="text-muted">{stage.data?.summary ?? ""}</span>
                  </div>
                  <StageDetail name={name} stages={stages} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function StageDetail({ name, stages }: { name: RagStageName; stages: Stages }) {
  const data = stages[name].data;
  if (!data) return null;

  if (
    name === "contextualize" &&
    data.rewritten &&
    data.original &&
    data.rewritten !== data.original
  ) {
    return (
      <div className="mt-1 text-[11px] font-mono space-y-0.5">
        <div className="text-muted truncate" title={data.original}>
          <span className="text-muted/70">orig:</span> {data.original}
        </div>
        <div className="text-accent2 truncate" title={data.rewritten}>
          <span className="text-muted/70">→ </span>
          {data.rewritten}
        </div>
      </div>
    );
  }

  if (name === "expand" && data.variants && data.variants.length > 0) {
    return (
      <ul className="mt-1 space-y-0.5 text-muted">
        {data.variants.map((v, i) => (
          <li key={i} className="font-mono text-[11px] truncate" title={v}>
            · {v}
          </li>
        ))}
      </ul>
    );
  }

  if (name === "retrieve" && data.sources && data.sources.length > 0) {
    return (
      <div className="mt-1 flex flex-wrap gap-1">
        {data.sources.map((s) => (
          <span
            key={s}
            className="text-[10px] font-mono bg-panel border border-border px-1.5 py-0.5 rounded text-muted"
          >
            {s}
          </span>
        ))}
      </div>
    );
  }

  if (name === "rerank" && data.kept && data.kept.length > 0) {
    return (
      <ul className="mt-1 space-y-0.5">
        {data.kept.map((k) => (
          <li key={k.index} className="text-[11px] font-mono text-muted truncate">
            [{k.index}] {k.label}
            {k.matches > 1 && (
              <span className="text-accent2 ml-1">×{k.matches}</span>
            )}
          </li>
        ))}
      </ul>
    );
  }

  return null;
}
