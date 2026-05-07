import { ChevronLeft, ChevronRight } from "lucide-react";

export const PAGE_SIZE = 10;

export function paginate<T>(items: T[], page: number, size: number = PAGE_SIZE): T[] {
  const start = (page - 1) * size;
  return items.slice(start, start + size);
}

export function pageCount(total: number, size: number = PAGE_SIZE): number {
  return Math.max(1, Math.ceil(total / size));
}

interface Props {
  page: number;
  total: number;
  size?: number;
  onChange: (page: number) => void;
  className?: string;
}

export function Pagination({ page, total, size = PAGE_SIZE, onChange, className = "" }: Props) {
  const pages = pageCount(total, size);
  if (pages <= 1) return null;

  const safe = Math.min(Math.max(1, page), pages);
  const start = (safe - 1) * size + 1;
  const end = Math.min(safe * size, total);

  return (
    <div className={`flex items-center justify-between mt-3 text-xs text-muted ${className}`}>
      <span>
        {start}–{end} of {total}
      </span>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onChange(safe - 1)}
          disabled={safe <= 1}
          className="p-1 rounded hover:bg-panel2 disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label="Previous page"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="px-2 font-mono">
          {safe} / {pages}
        </span>
        <button
          onClick={() => onChange(safe + 1)}
          disabled={safe >= pages}
          className="p-1 rounded hover:bg-panel2 disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label="Next page"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
