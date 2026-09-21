import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

const PAGE_SIZES = [10, 20, 50, 100];

/**
 * Reusable pagination controls. Backend returns the total via the
 * X-Total-Count response header; pass it as `total`.
 */
export default function Pagination({ page, pageSize, total, onPageChange, onPageSizeChange }) {
  const totalPages = Math.max(1, Math.ceil((total || 0) / pageSize));

  const goTo = (p) => {
    const next = Math.min(Math.max(1, p), totalPages);
    if (next !== page) onPageChange(next);
  };

  // Compact page-number window around the current page
  const pages = [];
  const start = Math.max(1, Math.min(page - 2, totalPages - 4));
  const end = Math.min(totalPages, start + 4);
  for (let p = start; p <= end; p++) pages.push(p);

  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 py-4">
      <p className="text-sm text-slate-500" data-testid="pagination-info">
        Showing {from}–{to} of {total || 0}
      </p>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => goTo(page - 1)}
          data-testid="pagination-prev"
        >
          <ChevronLeft className="w-4 h-4" />
        </Button>

        {pages.map((p) => (
          <Button
            key={p}
            variant={p === page ? 'default' : 'outline'}
            size="sm"
            onClick={() => goTo(p)}
            data-testid={`pagination-page-${p}`}
          >
            {p}
          </Button>
        ))}

        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => goTo(page + 1)}
          data-testid="pagination-next"
        >
          <ChevronRight className="w-4 h-4" />
        </Button>

        <Select
          value={String(pageSize)}
          onValueChange={(v) => onPageSizeChange(parseInt(v, 10))}
        >
          <SelectTrigger className="w-20" data-testid="pagination-size">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZES.map((s) => (
              <SelectItem key={s} value={String(s)}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
