import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Search, Download, ChevronLeft, ChevronRight } from 'lucide-react';
import { useIndex } from '../api/hooks.ts';
import type { SentinelCase } from '../api/types.ts';
import Card from '../components/ui/Card.tsx';
import Select from '../components/ui/Select.tsx';
import ClassificationBadge from '../components/ui/ClassificationBadge.tsx';
import StatusBadge from '../components/ui/StatusBadge.tsx';
import Skeleton from '../components/ui/Skeleton.tsx';
import { formatRelativeTime, scoreColor } from '../lib/formatters.ts';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 25;

const CLASS_OPTIONS = [
  { value: '', label: 'All Classifications' },
  { value: 'INSIDER', label: 'Insider' },
  { value: 'OSINT_EDGE', label: 'OSINT Edge' },
  { value: 'FAST_REACTOR', label: 'Fast Reactor' },
  { value: 'SPECULATOR', label: 'Speculator' },
] as const;

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'CONFIRMED', label: 'Confirmed' },
  { value: 'DISPUTED', label: 'Disputed' },
  { value: 'UNDER_REVIEW', label: 'Under Review' },
] as const;

// ---------------------------------------------------------------------------
// CSV export helper
// ---------------------------------------------------------------------------

function exportCsv(items: SentinelCase[]) {
  const headers = [
    'case_id',
    'market_name',
    'classification',
    'bss_score',
    'pes_score',
    'consensus_score',
    'status',
    'created_at',
  ];

  const rows = items.map((c) => [
    c.case_id,
    `"${(c.market_name ?? '').replace(/"/g, '""')}"`,
    c.classification,
    c.bss_score ?? '',
    c.pes_score ?? '',
    c.consensus_score ?? '',
    c.status,
    c.created_at,
  ]);

  const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `sentinel_index_${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Inline consensus bar
// ---------------------------------------------------------------------------

function ConsensusBar({ score }: { score: number | null | undefined }) {
  const v = score ?? 0;
  const pct = Math.min(100, v);

  return (
    <div className="flex items-center gap-2">
      <div className="w-14 h-1.5 rounded-full bg-border-subtle overflow-hidden">
        <div
          className="h-full rounded-full bg-accent transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-mono text-xs text-text-secondary w-7 text-right">
        {v}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SentinelIndex page
// ---------------------------------------------------------------------------

export default function SentinelIndex() {
  const navigate = useNavigate();

  // Filter state
  const [classFilter, setClassFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [offset, setOffset] = useState(0);

  // Debounce search input (300ms)
  useEffect(() => {
    const timeout = setTimeout(() => {
      setDebouncedSearch(searchInput);
      setOffset(0);
    }, 300);
    return () => clearTimeout(timeout);
  }, [searchInput]);

  // Reset offset when filters change
  useEffect(() => {
    setOffset(0);
  }, [classFilter, statusFilter]);

  const { data, loading } = useIndex({
    classification: classFilter || undefined,
    status: statusFilter || undefined,
    search: debouncedSearch || undefined,
    limit: PAGE_SIZE,
    offset,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const showingStart = total === 0 ? 0 : offset + 1;
  const showingEnd = Math.min(offset + PAGE_SIZE, total);
  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  return (
    <div className="space-y-6">
      {/* ---- Page Title ---- */}
      <div>
        <p className="overline mb-1">// SENTINEL INDEX</p>
        <h1 className="font-display text-2xl font-bold text-text-primary">
          Sentinel Index
        </h1>
      </div>

      {/* ---- Filter Bar ---- */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex flex-wrap items-center gap-3"
      >
        <Select
          value={classFilter}
          onChange={setClassFilter}
          options={CLASS_OPTIONS as unknown as { value: string; label: string }[]}
        />
        <Select
          value={statusFilter}
          onChange={setStatusFilter}
          options={STATUS_OPTIONS as unknown as { value: string; label: string }[]}
        />

        {/* Search input */}
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none"
          />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search markets, wallets..."
            className="w-full bg-bg-tertiary border border-border-subtle rounded pl-8 pr-3 py-1.5 font-mono text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent transition-colors"
          />
        </div>

        {/* CSV Export */}
        <button
          onClick={() => items.length > 0 && exportCsv(items)}
          disabled={items.length === 0}
          className="flex items-center gap-1.5 bg-bg-tertiary border border-border-subtle rounded px-3 py-1.5 font-mono text-xs text-text-secondary hover:text-accent hover:border-accent transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          <Download size={14} />
          Export CSV
        </button>
      </motion.div>

      {/* ---- Data Table ---- */}
      <Card>
        <div className="overflow-x-auto -mx-5 -mt-1">
          <table className="w-full min-w-[900px]">
            <thead>
              <tr className="bg-bg-tertiary sticky top-0 z-10">
                <th className="overline text-left px-5 py-2.5">Case ID</th>
                <th className="overline text-left px-3 py-2.5">Market</th>
                <th className="overline text-left px-3 py-2.5">Classification</th>
                <th className="overline text-left px-3 py-2.5">BSS</th>
                <th className="overline text-left px-3 py-2.5">PES</th>
                <th className="overline text-left px-3 py-2.5">Consensus</th>
                <th className="overline text-left px-3 py-2.5">Status</th>
                <th className="overline text-left px-3 py-2.5">Created</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 8 }).map((__, j) => (
                      <td key={j} className="px-5 py-3">
                        <Skeleton className="h-3 w-full" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : items.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-5 py-14 text-center text-text-tertiary font-mono text-sm"
                  >
                    No cases found
                  </td>
                </tr>
              ) : (
                items.map((c: SentinelCase, idx: number) => (
                  <tr
                    key={c.case_id}
                    onClick={() => navigate(`/case/${c.case_id}`)}
                    className={`cursor-pointer hover:bg-bg-hover transition-colors ${
                      idx % 2 === 0 ? 'bg-bg-primary' : ''
                    }`}
                  >
                    <td className="px-5 py-3 font-mono text-xs text-accent">
                      {c.case_id.slice(0, 8)}
                    </td>
                    <td
                      className="px-3 py-3 font-mono text-xs text-text-secondary max-w-[220px] truncate"
                      title={c.market_name ?? ''}
                    >
                      {c.market_name
                        ? c.market_name.length > 30
                          ? c.market_name.slice(0, 30) + '...'
                          : c.market_name
                        : '—'}
                    </td>
                    <td className="px-3 py-3">
                      <ClassificationBadge
                        classification={c.classification}
                        size="sm"
                      />
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className="font-mono text-sm font-semibold"
                        style={{ color: scoreColor(c.bss_score) }}
                      >
                        {c.bss_score ?? '—'}
                      </span>
                    </td>
                    <td className="px-3 py-3 font-mono text-sm text-text-secondary">
                      {c.pes_score ?? '—'}
                    </td>
                    <td className="px-3 py-3">
                      <ConsensusBar score={c.consensus_score} />
                    </td>
                    <td className="px-3 py-3">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-text-tertiary whitespace-nowrap">
                      {formatRelativeTime(c.created_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* ---- Pagination ---- */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs text-text-tertiary">
          {total > 0
            ? `Showing ${showingStart}-${showingEnd} of ${total} cases`
            : 'No results'}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            disabled={!hasPrev}
            className="flex items-center gap-1 bg-bg-tertiary border border-border-subtle rounded px-3 py-1.5 font-mono text-xs text-text-secondary hover:text-accent hover:border-accent transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
          >
            <ChevronLeft size={14} />
            Prev
          </button>
          <button
            onClick={() => setOffset(offset + PAGE_SIZE)}
            disabled={!hasNext}
            className="flex items-center gap-1 bg-bg-tertiary border border-border-subtle rounded px-3 py-1.5 font-mono text-xs text-text-secondary hover:text-accent hover:border-accent transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
          >
            Next
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
