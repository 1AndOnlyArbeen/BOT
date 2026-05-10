import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../../api";

export interface UseRagCorpus {
  sources: string[];
  busy: boolean;
  status: string;
  refresh: () => Promise<void>;
  uploadFiles: (files: FileList | null) => Promise<void>;
  ingestText: (text: string, label: string) => Promise<void>;
  deleteSource: (name: string) => Promise<void>;
  resetAll: () => Promise<void>;
}

export function useRagCorpus(): UseRagCorpus {
  const [sources, setSources] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const flashTimer = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const list = await api.ragSources();
      setSources(list);
    } catch {
      /* surface nothing — sources panel just shows empty */
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const flash = useCallback((msg: string) => {
    setStatus(msg);
    if (flashTimer.current) window.clearTimeout(flashTimer.current);
    flashTimer.current = window.setTimeout(() => setStatus(""), 3000);
  }, []);

  const uploadFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;
      setBusy(true);
      try {
        const r = await api.ragUpload(Array.from(files));
        flash(
          `Indexed ${r.chunks} chunk${r.chunks === 1 ? "" : "s"} from ${r.files.length} file${r.files.length === 1 ? "" : "s"}.`,
        );
        await refresh();
      } catch (e: any) {
        flash(`Upload failed: ${e.message ?? e}`);
      } finally {
        setBusy(false);
      }
    },
    [flash, refresh],
  );

  const ingestText = useCallback(
    async (text: string, label: string) => {
      if (!text.trim()) return;
      setBusy(true);
      try {
        const r = await api.ragText(text, label.trim() || "pasted");
        flash(`Indexed ${r.chunks} chunk${r.chunks === 1 ? "" : "s"} under "${r.source}".`);
        await refresh();
      } catch (e: any) {
        flash(`Ingest failed: ${e.message ?? e}`);
      } finally {
        setBusy(false);
      }
    },
    [flash, refresh],
  );

  const deleteSource = useCallback(
    async (name: string) => {
      if (!confirm(`Remove "${name}" from the corpus?`)) return;
      setBusy(true);
      try {
        const r = await api.ragDeleteSource(name);
        flash(`Removed ${r.deleted} chunk${r.deleted === 1 ? "" : "s"}.`);
        await refresh();
      } finally {
        setBusy(false);
      }
    },
    [flash, refresh],
  );

  const resetAll = useCallback(async () => {
    if (!confirm("Wipe the entire RAG corpus? This can't be undone.")) return;
    setBusy(true);
    try {
      await api.ragReset();
      flash("Corpus cleared.");
      await refresh();
    } finally {
      setBusy(false);
    }
  }, [flash, refresh]);

  return { sources, busy, status, refresh, uploadFiles, ingestText, deleteSource, resetAll };
}
