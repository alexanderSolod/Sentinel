import { useState, useEffect } from 'react';
import Select from '../components/ui/Select.tsx';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  Shield,
  TrendingUp,
  Package,
  ChevronRight,
  ChevronLeft,
  Download,
  Info,
} from 'lucide-react';
import { useHealth, useIndex, useEvidence } from '../api/hooks.ts';
import type { SentinelCase, EvidencePacket } from '../api/types.ts';
import Card from '../components/ui/Card.tsx';
import ClassificationBadge from '../components/ui/ClassificationBadge.tsx';
import StatusBadge from '../components/ui/StatusBadge.tsx';
import WalletAddress from '../components/ui/WalletAddress.tsx';
import Skeleton from '../components/ui/Skeleton.tsx';
import { formatRelativeTime, formatNumber, scoreColor } from '../lib/formatters.ts';
import { SCORE_DEFINITIONS } from '../lib/scoreDefinitions.ts';
import Tooltip from '../components/ui/Tooltip.tsx';

// ---------------------------------------------------------------------------
// KPI metric card
// ---------------------------------------------------------------------------

interface MetricCardProps {
  label: string;
  value: number | undefined;
  icon: React.ReactNode;
  loading: boolean;
  delay?: number;
}

function MetricCard({ label, value, icon, loading, delay = 0 }: MetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: [0.16, 1, 0.3, 1] }}
      className="bg-bg-secondary border-b border-border-subtle rounded-lg p-4 hover:bg-bg-tertiary transition-colors duration-200"
    >
      <div className="flex items-center justify-between mb-3">
        <span className="overline">{label}</span>
        <span className="text-text-tertiary">{icon}</span>
      </div>
      {loading ? (
        <Skeleton className="h-9 w-20" />
      ) : (
        <span className="font-display text-3xl font-bold text-accent">
          {formatNumber(value ?? 0)}
        </span>
      )}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Inline bars
// ---------------------------------------------------------------------------

function InlineBar({ value }: { value: number | null | undefined }) {
  const v = value ?? 0;
  const pct = Math.min(100, v * 100);
  const color =
    v > 0.7 ? 'bg-threat-critical' : v > 0.4 ? 'bg-threat-medium' : 'bg-threat-low';

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-border-subtle overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-mono text-xs text-text-secondary w-8 text-right">
        {v.toFixed(2)}
      </span>
    </div>
  );
}

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
// Filter options
// ---------------------------------------------------------------------------

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
    'case_id', 'market_name', 'classification', 'bss_score',
    'pes_score', 'consensus_score', 'status', 'created_at',
  ];
  const rows = items.map((c) => [
    c.case_id,
    `"${(c.market_name ?? '').replace(/"/g, '""')}"`,
    c.classification, c.bss_score ?? '', c.pes_score ?? '',
    c.consensus_score ?? '', c.status, c.created_at,
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
// Page constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 50;

// ---------------------------------------------------------------------------
// LiveMonitor page
// ---------------------------------------------------------------------------

export default function LiveMonitor() {
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

  const POLL_MS = 5000;

  const { data: health, loading: healthLoading } = useHealth({ refreshInterval: POLL_MS });
  const { data: casesPage, loading: casesLoading } = useIndex({
    classification: classFilter || undefined,
    status: statusFilter || undefined,
    search: debouncedSearch || undefined,
    limit: PAGE_SIZE,
    offset,
    refreshInterval: POLL_MS,
  });
  const { data: evidence, loading: evidenceLoading } = useEvidence({ limit: 15, refreshInterval: POLL_MS });

  const stats = health?.stats;
  const items = casesPage?.items ?? [];
  const total = casesPage?.total ?? 0;
  const showingStart = total === 0 ? 0 : offset + 1;
  const showingEnd = Math.min(offset + PAGE_SIZE, total);
  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  return (
    <div className="space-y-6">
      {/* ---- Page Title ---- */}
      <div>
        <p className="overline mb-1">// LIVE MONITOR</p>
        <h1 className="font-display text-2xl font-bold text-text-primary">
          Live Monitor
        </h1>
      </div>

      {/* ---- KPI Row ---- */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <MetricCard
          label="ACTIVE ANOMALIES"
          value={stats?.total_anomalies}
          icon={<Activity size={18} />}
          loading={healthLoading}
          delay={0}
        />
        <MetricCard
          label="INSIDER CASES"
          value={stats?.cases_by_classification?.INSIDER}
          icon={<Shield size={18} />}
          loading={healthLoading}
          delay={0.05}
        />
        <MetricCard
          label="UNDER REVIEW"
          value={stats?.cases_by_status?.UNDER_REVIEW}
          icon={<AlertTriangle size={18} />}
          loading={healthLoading}
          delay={0.1}
        />
        <MetricCard
          label="EVIDENCE PACKETS"
          value={stats?.total_evidence_packets}
          icon={<Package size={18} />}
          loading={healthLoading}
          delay={0.15}
        />
        <MetricCard
          label="TOTAL CASES"
          value={stats?.total_cases}
          icon={<TrendingUp size={18} />}
          loading={healthLoading}
          delay={0.2}
        />
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
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search markets, wallets..."
            className="w-full bg-bg-tertiary border border-border-subtle rounded px-3 py-1.5 font-mono text-xs text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent transition-colors"
          />
        </div>
        <button
          onClick={() => items.length > 0 && exportCsv(items)}
          disabled={items.length === 0}
          className="flex items-center gap-1.5 bg-bg-tertiary border border-border-subtle rounded px-3 py-1.5 font-mono text-xs text-text-secondary hover:text-accent hover:border-accent transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          <Download size={14} />
          Export CSV
        </button>
      </motion.div>

      {/* ---- Cases Table ---- */}
      <Card title="SENTINEL INDEX">
        <div className="overflow-x-auto -mx-5 -mt-1">
          <table className="w-full min-w-[900px]">
            <thead>
              <tr className="bg-bg-tertiary sticky top-0 z-10">
                <th className="overline text-left px-5 py-2.5">Case ID</th>
                <th className="overline text-left px-3 py-2.5">Market</th>
                <th className="overline text-left px-3 py-2.5">Classification</th>
                <th className="overline text-left px-3 py-2.5">
                  <span className="inline-flex items-center gap-1">
                    BSS
                    <Tooltip content={SCORE_DEFINITIONS.BSS.long} position="bottom">
                      <Info size={11} className="text-text-tertiary cursor-help" />
                    </Tooltip>
                  </span>
                </th>
                <th className="overline text-left px-3 py-2.5">
                  <span className="inline-flex items-center gap-1">
                    PES
                    <Tooltip content={SCORE_DEFINITIONS.PES.long} position="bottom">
                      <Info size={11} className="text-text-tertiary cursor-help" />
                    </Tooltip>
                  </span>
                </th>
                <th className="overline text-left px-3 py-2.5">
                  <span className="inline-flex items-center gap-1">
                    Consensus
                    <Tooltip content={SCORE_DEFINITIONS.CONSENSUS.long} position="bottom">
                      <Info size={11} className="text-text-tertiary cursor-help" />
                    </Tooltip>
                  </span>
                </th>
                <th className="overline text-left px-3 py-2.5">Status</th>
                <th className="overline text-left px-3 py-2.5">Created</th>
              </tr>
            </thead>
            <tbody>
              {casesLoading ? (
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
                      {c.case_id.slice(0, 12)}
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-text-secondary max-w-[220px]">
                      {c.market_name && c.market_name.length > 30 ? (
                        <Tooltip content={c.market_name} position="bottom">
                          <span className="truncate block max-w-[220px] cursor-help">
                            {c.market_name.slice(0, 30) + '...'}
                          </span>
                        </Tooltip>
                      ) : (
                        <span>{c.market_name ?? '—'}</span>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <ClassificationBadge classification={c.classification} size="sm" />
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

      {/* ---- Evidence Packets ---- */}
      <Card title="EVIDENCE PACKETS">
        <p className="font-mono text-xs text-text-tertiary mb-4 leading-relaxed" style={{ textTransform: 'none' }}>
          Per-wallet forensic evidence linking flagged trades to cases. Each packet captures the
          wallet's risk profile, the temporal gap between trade and public news (gap score),
          and an overall correlation score combining wallet behavior, cluster analysis, and OSINT timing.
        </p>
        <div className="overflow-x-auto -mx-5">
          <table className="w-full min-w-[600px]">
            <thead>
              <tr className="bg-bg-tertiary sticky top-0 z-10">
                <th className="overline text-left px-5 py-2">Case ID</th>
                <th className="overline text-left px-3 py-2">Market</th>
                <th className="overline text-left px-3 py-2">Wallet</th>
                <th className="overline text-left px-3 py-2">Gap Score</th>
                <th className="overline text-left px-3 py-2">Wallet Risk</th>
                <th className="overline text-left px-3 py-2">Correlation</th>
              </tr>
            </thead>
            <tbody>
              {evidenceLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 6 }).map((__, j) => (
                      <td key={j} className="px-5 py-2.5">
                        <Skeleton className="h-3 w-full" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : !evidence?.items?.length ? (
                <tr>
                  <td colSpan={6} className="px-5 py-10 text-center text-text-tertiary font-mono text-sm">
                    No evidence packets available
                  </td>
                </tr>
              ) : (
                evidence.items.map((ep: EvidencePacket, idx: number) => (
                  <tr
                    key={ep.case_id + '-' + idx}
                    className={`hover:bg-bg-hover transition-colors ${
                      idx % 2 === 0 ? 'bg-bg-primary' : ''
                    }`}
                  >
                    <td className="px-5 py-2.5 font-mono text-xs text-accent">
                      {ep.case_id.slice(0, 12)}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-xs text-text-secondary max-w-[180px]">
                      {ep.market_name && ep.market_name.length > 25 ? (
                        <Tooltip content={ep.market_name} position="bottom">
                          <span className="truncate block max-w-[180px] cursor-help">
                            {ep.market_name.slice(0, 25) + '...'}
                          </span>
                        </Tooltip>
                      ) : (
                        <span>{ep.market_name ?? '—'}</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      <WalletAddress address={ep.wallet_address} />
                    </td>
                    <td className="px-3 py-2.5">
                      <InlineBar value={ep.temporal_gap_score} />
                    </td>
                    <td className="px-3 py-2.5">
                      <InlineBar value={ep.wallet_risk_score} />
                    </td>
                    <td className="px-3 py-2.5">
                      <InlineBar value={ep.correlation_score} />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
