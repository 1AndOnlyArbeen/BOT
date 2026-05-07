import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import { api } from "../api";
import { Pagination, paginate } from "./Pagination";

export function StatsView() {
  const [overview, setOverview] = useState<any>(null);
  const [audit, setAudit] = useState<any[]>([]);
  const [page, setPage] = useState(1);

  useEffect(() => {
    api.stats().then(setOverview);
    api.audit(200).then(setAudit);
  }, []);

  if (!overview) return <div className="p-6 text-muted">Loading…</div>;

  return (
    <div className="flex flex-col h-full">
      <header className="px-6 py-3 border-b border-border bg-panel">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-accent2" />
          <h2 className="font-semibold">Stats</h2>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
            <Card label="Sessions" value={overview.sessions} />
            <Card label="Memories" value={overview.memories} />
            <Card label="Episodes" value={overview.episodes} />
            <Card label="Entities" value={overview.entities} />
          </div>

          <h3 className="text-sm uppercase tracking-wider text-muted mb-3">Last 24h — Tool Usage</h3>
          <div className="bg-panel2 border border-border rounded-md p-4 mb-6">
            <div className="text-2xl font-bold mb-3">{overview.audit_24h.total_calls} tool calls</div>
            <div className="space-y-2">
              {overview.audit_24h.by_tool.map((t: any) => (
                <div key={t.tool} className="flex items-center justify-between text-sm">
                  <span className="font-mono text-accent2">{t.tool}</span>
                  <span className="text-muted">
                    {t.count} × · {t.avg_ms}ms avg · {t.success_rate}% ok
                  </span>
                </div>
              ))}
              {overview.audit_24h.by_tool.length === 0 && (
                <div className="text-muted text-sm">No tool calls yet.</div>
              )}
            </div>
          </div>

          <h3 className="text-sm uppercase tracking-wider text-muted mb-3">
            Recent activity ({audit.length})
          </h3>
          <div className="space-y-1 font-mono text-xs">
            {paginate(audit, page).map((a) => (
              <div key={a.id} className="bg-panel2 px-3 py-1.5 rounded flex justify-between">
                <span className="text-accent2">{a.tool}</span>
                <span className="text-muted">
                  {a.duration_ms ? `${Math.round(a.duration_ms)}ms` : ""} · {a.status}
                </span>
              </div>
            ))}
          </div>
          <Pagination page={page} total={audit.length} onChange={setPage} />
        </div>
      </div>
    </div>
  );
}

function Card({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-panel2 border border-border rounded-md p-4">
      <div className="text-xs text-muted uppercase tracking-wider">{label}</div>
      <div className="text-3xl font-bold mt-1 font-mono">{value}</div>
    </div>
  );
}
