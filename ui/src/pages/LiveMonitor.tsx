import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  Shield,
  TrendingUp,
  Package,
  ChevronRight,
} from 'lucide-react';
import { useHealth, useAnomalies, useEvidence } from '../api/hooks.ts';
import type { Anomaly, EvidencePacket } from '../api/types.ts';
import Card from '../components/ui/Card.tsx';
import ClassificationBadge from '../components/ui/ClassificationBadge.tsx';
import ScoreBar from '../components/ui/ScoreBar.tsx';
import WalletAddress from '../components/ui/WalletAddress.tsx';
import Skeleton from '../components/ui/Skeleton.tsx';
import { formatRelativeTime, formatNumber } from '../lib/formatters.ts';

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
      className="bg-bg-secondary border border-border-subtle rounded-lg p-4 hover:border-border-default transition-colors duration-200"
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
// Inline progress bar for evidence table
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

// ---------------------------------------------------------------------------
// Classification filter options
// ---------------------------------------------------------------------------

const FILTER_OPTIONS = [
  { value: '', label: 'All Classifications' },
  { value: 'INSIDER', label: 'Insider' },
  { value: 'OSINT_EDGE', label: 'OSINT Edge' },
  { value: 'FAST_REACTOR', label: 'Fast Reactor' },
  { value: 'SPECULATOR', label: 'Speculator' },
] as const;

// ---------------------------------------------------------------------------
// LiveMonitor page
// ---------------------------------------------------------------------------

export default function LiveMonitor() {
  const navigate = useNavigate();
  const [classFilter, setClassFilter] = useState('');

  const { data: health, loading: healthLoading } = useHealth();
  const { data: anomalies, loading: anomaliesLoading } = useAnomalies({
    limit: 20,
    classification: classFilter || undefined,
  });
  const { data: evidence, loading: evidenceLoading } = useEvidence({ limit: 15 });

  const stats = health?.stats;

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

      {/* ---- Two-Column: Anomaly Feed + Evidence Packets ---- */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* ---- Anomaly Feed ---- */}
        <Card title="RECENT ANOMALIES">
          {/* Filter */}
          <div className="mb-4">
            <select
              value={classFilter}
              onChange={(e) => setClassFilter(e.target.value)}
              className="bg-bg-tertiary border border-border-subtle rounded px-3 py-1.5 font-mono text-xs text-text-primary focus:outline-none focus:border-accent transition-colors cursor-pointer"
            >
              {FILTER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Anomaly rows */}
          <div className="space-y-0 -mx-5">
            {anomaliesLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="px-5 py-3 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              ))
            ) : !anomalies?.items?.length ? (
              <div className="px-5 py-10 text-center text-text-tertiary font-mono text-sm">
                No anomalies detected
              </div>
            ) : (
              anomalies.items.map((anomaly: Anomaly, idx: number) => (
                <div
                  key={anomaly.event_id}
                  onClick={() => navigate(`/case/${anomaly.event_id}`)}
                  className={`px-5 py-3 cursor-pointer hover:bg-bg-hover transition-colors ${
                    idx % 2 === 0 ? 'bg-bg-primary' : ''
                  }`}
                >
                  {/* Top row: badge + market + timestamp */}
                  <div className="flex items-center gap-3 mb-2">
                    <ClassificationBadge classification={anomaly.classification} size="sm" />
                    <span
                      className="font-mono text-sm text-text-primary truncate flex-1"
                      title={anomaly.market_name ?? ''}
                    >
                      {anomaly.market_name
                        ? anomaly.market_name.length > 40
                          ? anomaly.market_name.slice(0, 40) + '...'
                          : anomaly.market_name
                        : 'Unknown Market'}
                    </span>
                    <span className="font-mono text-xs text-text-tertiary whitespace-nowrap">
                      {formatRelativeTime(anomaly.timestamp)}
                    </span>
                    <ChevronRight size={14} className="text-text-tertiary shrink-0" />
                  </div>
                  {/* Bottom row: scores */}
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 pl-1">
                    <ScoreBar label="BSS" score={anomaly.bss_score} />
                    <ScoreBar label="PES" score={anomaly.pes_score} />
                  </div>
                  {anomaly.z_score != null && (
                    <div className="mt-1 pl-1 font-mono text-[11px] text-text-tertiary">
                      z-score: {anomaly.z_score.toFixed(2)}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </Card>

        {/* ---- Evidence Packets ---- */}
        <Card title="EVIDENCE PACKETS">
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
                        {ep.case_id.slice(0, 8)}
                      </td>
                      <td
                        className="px-3 py-2.5 font-mono text-xs text-text-secondary truncate max-w-[180px]"
                        title={ep.market_name ?? ''}
                      >
                        {ep.market_name
                          ? ep.market_name.length > 25
                            ? ep.market_name.slice(0, 25) + '...'
                            : ep.market_name
                          : '—'}
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
    </div>
  );
}
