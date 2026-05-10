import type { CitationHit } from "./types";

export function RagCitations({ hits }: { hits: CitationHit[] }) {
  if (hits.length === 0) return null;
  return (
    <div className="mb-3 bg-panel2 border border-border rounded-md px-3 py-2">
      <div className="text-xs text-muted mb-1.5">
        📎 Cited {hits.length} chunk{hits.length === 1 ? "" : "s"}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {hits.map((h) => (
          <span
            key={`${h.index}-${h.label}`}
            className="text-[11px] font-mono bg-panel border border-border px-2 py-0.5 rounded text-accent2"
            title={h.matches ? `matched ${h.matches} query variant${h.matches === 1 ? "" : "s"}` : undefined}
          >
            [{h.index}] {h.label}
          </span>
        ))}
      </div>
    </div>
  );
}
