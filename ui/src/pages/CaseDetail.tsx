import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  Clock,
  Hash,
  Trophy,
  AlertTriangle,
  Shield,
  Brain,
  ChevronDown,
  ChevronUp,
  FileText,
  Network,
  Satellite,
  Skull,
  Lightbulb,
  Scale,
} from 'lucide-react';

import { useCaseDetail } from '../api/hooks.ts';
import type { EvidenceJson } from '../api/types.ts';
import Card from '../components/ui/Card.tsx';
import ClassificationBadge from '../components/ui/ClassificationBadge.tsx';
import ScoreBar from '../components/ui/ScoreBar.tsx';
import StatusBadge from '../components/ui/StatusBadge.tsx';
import WalletAddress from '../components/ui/WalletAddress.tsx';
import Skeleton from '../components/ui/Skeleton.tsx';
import TemporalGapChart from '../components/charts/TemporalGapChart.tsx';
import ClassificationQuadrant from '../components/charts/ClassificationQuadrant.tsx';
import { formatNumber, formatPercent, formatRelativeTime } from '../lib/formatters.ts';

export default function CaseDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const { data, loading, error } = useCaseDetail(caseId);
  const [sarExpanded, setSarExpanded] = useState(false);

  // No caseId in URL -- prompt user to select one
  if (!caseId) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 py-24">
        <FileText size={48} className="text-text-tertiary" />
        <p className="font-mono text-text-secondary text-sm">
          Select a case from the{' '}
          <button
            onClick={() => navigate('/index')}
            className="text-accent underline underline-offset-2 hover:text-accent/80 transition-colors"
          >
            Sentinel Index
          </button>{' '}
          to view details.
        </p>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <Skeleton className="h-20 w-full" />
        </div>
        <div className="col-span-2">
          <Skeleton className="h-56 w-full" />
        </div>
        <Skeleton className="h-52" />
        <Skeleton className="h-52" />
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 py-24">
        <AlertTriangle size={36} className="text-threat-critical" />
        <p className="font-mono text-text-secondary text-sm">
          Failed to load case: {error}
        </p>
        <button
          onClick={() => navigate('/index')}
          className="text-accent font-mono text-xs underline underline-offset-2"
        >
          Back to index
        </button>
      </div>
    );
  }

  if (!data) return null;

  const { case: sentinelCase, anomaly, evidence_packet, osint_events } = data;
  const evidence: EvidenceJson | null = sentinelCase.evidence ?? null;

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* ------------------------------------------------------------------ */}
      {/* 1. Case Header (full width) */}
      {/* ------------------------------------------------------------------ */}
      <Card span={2} className="!p-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => navigate(-1)}
              className="text-text-tertiary hover:text-accent transition-colors shrink-0"
            >
              <ArrowLeft size={18} />
            </button>
            <ClassificationBadge classification={sentinelCase.classification} />
            <h1 className="font-display text-xl text-text-primary truncate">
              {sentinelCase.market_name ?? sentinelCase.market_id}
            </h1>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className="font-mono text-[11px] text-text-tertiary">
              {sentinelCase.case_id}
            </span>
            <StatusBadge status={sentinelCase.status} />
          </div>
        </div>

        {/* BSS / PES score bars */}
        <div className="grid grid-cols-2 gap-4 mt-4">
          <ScoreBar label="BSS" score={sentinelCase.bss_score} />
          <ScoreBar label="PES" score={sentinelCase.pes_score} />
        </div>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* 2. Temporal Gap Chart (full width, hero) */}
      {/* ------------------------------------------------------------------ */}
      <Card span={2} title="Temporal Gap Analysis">
        <TemporalGapChart
          evidence={evidence}
          classification={sentinelCase.classification}
        />
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* 3. Wallet Profile (left column) */}
      {/* ------------------------------------------------------------------ */}
      <Card title="Wallet Profile">
        {evidence_packet ? (
          <div className="space-y-4">
            <WalletAddress address={evidence_packet.wallet_address} />

            <div className="grid grid-cols-2 gap-3">
              <StatItem
                icon={<Clock size={14} />}
                label="Age"
                value={
                  evidence_packet.wallet_age_hours != null
                    ? `${evidence_packet.wallet_age_hours.toFixed(1)}h`
                    : '--'
                }
              />
              <StatItem
                icon={<Hash size={14} />}
                label="Trades"
                value={formatNumber(evidence_packet.wallet_trade_count)}
              />
              <StatItem
                icon={<Trophy size={14} />}
                label="Win Rate"
                value={
                  evidence_packet.wallet_win_rate != null
                    ? formatPercent(evidence_packet.wallet_win_rate * 100)
                    : '--'
                }
              />
              <div>
                <div className="font-mono text-[10px] text-text-tertiary mb-1">Risk Score</div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 rounded-full bg-border-subtle overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${(evidence_packet.wallet_risk_score ?? 0) * 100}%`,
                        backgroundColor: riskColor(evidence_packet.wallet_risk_score ?? 0),
                      }}
                    />
                  </div>
                  <span
                    className="font-mono text-xs font-semibold"
                    style={{ color: riskColor(evidence_packet.wallet_risk_score ?? 0) }}
                  >
                    {evidence_packet.wallet_risk_score?.toFixed(2) ?? '--'}
                  </span>
                </div>
              </div>
            </div>

            {/* Risk flags */}
            <div className="flex flex-wrap gap-2 pt-2 border-t border-border-subtle">
              {evidence_packet.is_fresh_wallet === 1 && (
                <FlagBadge color="#FF2D55" label="Fresh Wallet" />
              )}
              {evidence_packet.cluster_id && (
                <FlagBadge
                  color="#FF6B2D"
                  label={`Cluster #${evidence_packet.cluster_id} (${evidence_packet.cluster_size})`}
                />
              )}
              {!evidence_packet.is_fresh_wallet && !evidence_packet.cluster_id && (
                <span className="font-mono text-[10px] text-text-tertiary">
                  No risk flags
                </span>
              )}
            </div>
          </div>
        ) : evidence?.wallet_address ? (
          <div className="space-y-4">
            <WalletAddress address={evidence.wallet_address} />

            <div className="grid grid-cols-2 gap-3">
              <StatItem
                icon={<Clock size={14} />}
                label="Age"
                value={
                  evidence.wallet_age_days != null
                    ? `${Number(evidence.wallet_age_days)}d`
                    : '--'
                }
              />
              <StatItem
                icon={<Hash size={14} />}
                label="Trades"
                value={evidence.wallet_trades != null ? formatNumber(evidence.wallet_trades) : '--'}
              />
              <StatItem
                icon={<Trophy size={14} />}
                label="Trade Size"
                value={
                  evidence.trade_size_usd != null
                    ? `$${formatNumber(evidence.trade_size_usd)}`
                    : '--'
                }
              />
              <StatItem
                icon={<AlertTriangle size={14} />}
                label="Z-Score"
                value={
                  evidence.z_score != null
                    ? Number(evidence.z_score).toFixed(1)
                    : '--'
                }
              />
            </div>

            {/* Price impact */}
            {evidence.price_before != null && evidence.price_after != null && (
              <div className="pt-2 border-t border-border-subtle">
                <div className="font-mono text-[10px] text-text-tertiary mb-1">Price Impact</div>
                <div className="flex items-center gap-2 font-mono text-xs">
                  <span className="text-text-secondary">{Number(evidence.price_before).toFixed(2)}</span>
                  <span className="text-text-tertiary">&rarr;</span>
                  <span className="text-text-primary font-semibold">{Number(evidence.price_after).toFixed(2)}</span>
                  <span
                    className="ml-auto font-semibold"
                    style={{
                      color: Number(evidence.price_after) > Number(evidence.price_before) ? '#34D399' : '#FF2D55',
                    }}
                  >
                    {((Number(evidence.price_after) - Number(evidence.price_before)) * 100).toFixed(0)}pp
                  </span>
                </div>
              </div>
            )}

            {/* Fresh wallet flag from age */}
            {evidence.wallet_age_days != null && Number(evidence.wallet_age_days) <= 7 && (
              <div className="flex flex-wrap gap-2 pt-2 border-t border-border-subtle">
                <FlagBadge color="#FF2D55" label="Fresh Wallet" />
              </div>
            )}
          </div>
        ) : (
          <div className="text-text-tertiary font-mono text-sm">
            No wallet data available
          </div>
        )}
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* 4. AI Analysis (right column) */}
      {/* ------------------------------------------------------------------ */}
      <Card title="AI Analysis">
        <div className="space-y-4">
          {/* XAI Narrative — terminal style */}
          <div>
            <div style={{
              fontFamily: 'Courier New, monospace',
              fontSize: 10,
              letterSpacing: '0.15em',
              color: '#33ff3388',
              border: '1px solid #33ff3333',
              padding: '2px 8px',
              display: 'inline-block',
              marginBottom: 10,
            }}>┃ MAGISTRAL REASONING ENGINE ┃</div>
            <p className="terminal-text cursor" style={{ fontSize: 12, lineHeight: 1.7 }}>
              {anomaly?.xai_narrative ?? sentinelCase.xai_summary ?? (
                <span style={{ color: '#33ff3344' }}>// no output — run pipeline to generate</span>
              )}
            </p>
          </div>

          {/* RF Analysis */}
          {evidence?.rf_analysis && (
            <div className="pt-3 border-t border-border-subtle">
              <div className="flex items-center gap-2 mb-2">
                <Network size={14} className="text-threat-medium" />
                <span className="overline">Random Forest</span>
                <span
                  className="ml-auto font-mono text-xs font-semibold"
                  style={{ color: riskColor(evidence.rf_analysis.rf_score / 100) }}
                >
                  {Number(evidence.rf_analysis.rf_score).toFixed(1)}
                </span>
              </div>
              {evidence.rf_analysis.top_features && (
                <div className="flex flex-wrap gap-1.5">
                  {normalizeTopFeatures(evidence.rf_analysis.top_features)
                    .sort((a, b) => b.importance - a.importance)
                    .slice(0, 5)
                    .map((item) => (
                      <span
                        key={item.feature}
                        className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-bg-active text-text-secondary"
                      >
                        {item.feature}: {item.importance.toFixed(2)}
                      </span>
                    ))}
                </div>
              )}
            </div>
          )}

          {/* Game Theory */}
          {evidence?.game_theory_analysis && (
            <div className="pt-3 border-t border-border-subtle">
              <div className="flex items-center gap-2 mb-1">
                <Scale size={14} className="text-threat-info" />
                <span className="overline">Game Theory</span>
              </div>
              <div className="font-mono text-xs text-text-secondary">
                <span className="text-text-tertiary">Best fit: </span>
                <span className="font-semibold text-text-primary">
                  {evidence.game_theory_analysis.best_fit_type}
                </span>
                <span className="text-text-tertiary ml-3">Suspicion: </span>
                <span className="font-semibold" style={{
                  color: riskColor(evidence.game_theory_analysis.game_theory_suspicion_score / 100),
                }}>
                  {Number(evidence.game_theory_analysis.game_theory_suspicion_score).toFixed(1)}
                </span>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* 5. Classification Quadrant (left column) */}
      {/* ------------------------------------------------------------------ */}
      <Card title="Classification Quadrant">
        <ClassificationQuadrant
          bss={sentinelCase.bss_score}
          pes={sentinelCase.pes_score}
        />
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* 6. OSINT Signals (right column) */}
      {/* ------------------------------------------------------------------ */}
      <Card title="OSINT Signals">
        {(() => {
          // Merge all available signal sources: evidence.osint_signals, API osint_events, fallback context
          const hasInlineSignals = evidence?.osint_signals && evidence.osint_signals.length > 0;
          const hasApiEvents = osint_events && osint_events.length > 0;

          if (hasInlineSignals) {
            return (
              <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                {evidence!.osint_signals!.map((signal, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 p-2.5 rounded-md bg-bg-tertiary border border-border-subtle"
                  >
                    <Satellite size={14} className="text-threat-high shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-bg-active text-threat-high">
                          {signal.source}
                        </span>
                        <span className="font-mono text-[10px] text-text-tertiary ml-auto shrink-0">
                          {Number(signal.hours_before_trade) > 0
                            ? `${Number(signal.hours_before_trade).toFixed(1)}h before trade`
                            : `${Math.abs(Number(signal.hours_before_trade)).toFixed(1)}h after trade`}
                        </span>
                      </div>
                      <p className="font-mono text-xs text-text-secondary leading-relaxed truncate">
                        {signal.headline}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            );
          }

          if (hasApiEvents) {
            return (
              <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                {/* Scenario context if available */}
                {evidence?.scenario && (
                  <div className="p-2.5 rounded-md bg-bg-tertiary border border-border-subtle mb-1">
                    <p className="font-mono text-xs text-text-secondary leading-relaxed">
                      {evidence.scenario}
                    </p>
                  </div>
                )}
                {osint_events.map((event) => (
                  <div
                    key={event.event_id}
                    className="flex items-start gap-3 p-2.5 rounded-md bg-bg-tertiary border border-border-subtle"
                  >
                    <Satellite size={14} className="text-threat-high shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-bg-active text-threat-high">
                          {event.source}
                        </span>
                        {event.category && (
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-bg-active text-text-tertiary">
                            {event.category}
                          </span>
                        )}
                        <span className="font-mono text-[10px] text-text-tertiary ml-auto shrink-0">
                          {formatRelativeTime(event.timestamp)}
                        </span>
                      </div>
                      <p className="font-mono text-xs text-text-secondary leading-relaxed">
                        {event.headline}
                      </p>
                      {event.source_url && (
                        <a
                          href={event.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-[10px] text-accent hover:underline mt-1 inline-block"
                        >
                          Source link
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            );
          }

          // Fallback: show news headline, scenario, or signal count
          if (evidence?.news_headline || evidence?.scenario) {
            return (
              <div className="space-y-3">
                {evidence?.news_headline && (
                  <div className="flex items-start gap-3 p-2.5 rounded-md bg-bg-tertiary border border-border-subtle">
                    <Satellite size={14} className="text-threat-critical shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-bg-active text-threat-critical">
                          NEWS
                        </span>
                        {evidence.hours_before_news != null && (
                          <span className="font-mono text-[10px] text-text-tertiary ml-auto shrink-0">
                            {Number(evidence.hours_before_news) > 0
                              ? `${Number(evidence.hours_before_news).toFixed(1)}h before trade`
                              : `${Math.abs(Number(evidence.hours_before_news)).toFixed(1)}h after trade`}
                          </span>
                        )}
                      </div>
                      <p className="font-mono text-xs text-text-secondary leading-relaxed">
                        {evidence.news_headline}
                      </p>
                    </div>
                  </div>
                )}
                {evidence?.scenario && (
                  <div className="p-2.5 rounded-md bg-bg-tertiary border border-border-subtle">
                    <div className="flex items-center gap-2 mb-1.5">
                      <Brain size={14} className="text-accent shrink-0" />
                      <span className="font-mono text-[10px] font-semibold uppercase text-text-tertiary">Scenario</span>
                    </div>
                    <p className="font-mono text-xs text-text-secondary leading-relaxed">
                      {evidence.scenario}
                    </p>
                  </div>
                )}
              </div>
            );
          }

          return (
            <div className="flex flex-col items-center justify-center py-8 text-text-tertiary">
              <Satellite size={24} className="mb-2 opacity-50" />
              <span className="font-mono text-xs">No OSINT signals found</span>
            </div>
          );
        })()}
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* 7. Fraud Triangle (left column) */}
      {/* ------------------------------------------------------------------ */}
      <Card title="Fraud Triangle">
        {anomaly?.fraud_triangle ? (
          <div className="space-y-4">
            <FraudTriangleSection
              icon={<AlertTriangle size={16} className="text-threat-critical" />}
              label="Pressure"
              text={anomaly.fraud_triangle.pressure}
            />
            <FraudTriangleSection
              icon={<Lightbulb size={16} className="text-threat-medium" />}
              label="Opportunity"
              text={anomaly.fraud_triangle.opportunity}
            />
            <FraudTriangleSection
              icon={<Skull size={16} className="text-threat-high" />}
              label="Rationalization"
              text={anomaly.fraud_triangle.rationalization}
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-text-tertiary">
            <Shield size={24} className="mb-2 opacity-50" />
            <span className="font-mono text-xs">Not available</span>
          </div>
        )}
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* 8. Voting Summary (right column) */}
      {/* ------------------------------------------------------------------ */}
      <Card title="Community Votes">
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <VoteStat
              label="Agree"
              count={sentinelCase.votes_agree}
              total={sentinelCase.vote_count}
              color="#34D399"
            />
            <VoteStat
              label="Disagree"
              count={sentinelCase.votes_disagree}
              total={sentinelCase.vote_count}
              color="#FF2D55"
            />
            <VoteStat
              label="Uncertain"
              count={sentinelCase.votes_uncertain}
              total={sentinelCase.vote_count}
              color="#FFB800"
            />
          </div>
          {sentinelCase.consensus_score != null && (
            <div className="pt-2 border-t border-border-subtle">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] text-text-tertiary">Consensus Score</span>
                <span className="font-mono text-sm font-semibold text-accent">
                  {sentinelCase.consensus_score.toFixed(1)}%
                </span>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* 9. SAR Report (full width, collapsible) */}
      {/* ------------------------------------------------------------------ */}
      {sentinelCase.sar_report && (
        <div className="col-span-2">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="bg-bg-secondary border border-border-subtle rounded-lg overflow-hidden hover:border-border-default transition-colors duration-200"
          >
            <button
              onClick={() => setSarExpanded((prev) => !prev)}
              className="w-full flex items-center justify-between p-5 text-left"
            >
              <div className="flex items-center gap-2">
                <FileText size={14} className="text-threat-critical" />
                <span className="overline">
                  {sarExpanded ? 'Hide SAR Report' : 'Show SAR Report'}
                </span>
              </div>
              {sarExpanded ? (
                <ChevronUp size={16} className="text-text-tertiary" />
              ) : (
                <ChevronDown size={16} className="text-text-tertiary" />
              )}
            </button>

            <AnimatePresence initial={false}>
              {sarExpanded && (
                <motion.div
                  key="sar-content"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                  className="overflow-hidden"
                >
                  <div className="px-5 pb-5 border-t border-border-subtle">
                    <pre className="mt-4 font-mono text-xs text-text-secondary leading-relaxed whitespace-pre-wrap break-words bg-bg-tertiary rounded-md p-4 border border-border-subtle max-h-[500px] overflow-y-auto">
                      {sentinelCase.sar_report}
                    </pre>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-text-tertiary">{icon}</span>
        <span className="font-mono text-[10px] text-text-tertiary">{label}</span>
      </div>
      <span className="font-mono text-sm font-semibold text-text-primary">{value}</span>
    </div>
  );
}

function FlagBadge({ color, label }: { color: string; label: string }) {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[10px] font-semibold"
      style={{ color, backgroundColor: `${color}0F` }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}

function FraudTriangleSection({
  icon,
  label,
  text,
}: {
  icon: React.ReactNode;
  label: string;
  text: string;
}) {
  return (
    <div className="flex gap-3">
      <div className="shrink-0 mt-0.5">{icon}</div>
      <div>
        <div className="font-mono text-xs font-semibold text-text-primary mb-1">{label}</div>
        <p className="font-mono text-xs text-text-secondary leading-relaxed">{text}</p>
      </div>
    </div>
  );
}

function VoteStat({
  label,
  count,
  total,
  color,
}: {
  label: string;
  count: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="text-center">
      <div className="font-mono text-lg font-bold" style={{ color }}>
        {count}
      </div>
      <div className="font-mono text-[10px] text-text-tertiary">{label}</div>
      <div className="mt-1 h-1 rounded-full bg-border-subtle overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function riskColor(score: number): string {
  if (score > 0.7) return '#FF2D55';
  if (score > 0.4) return '#FFB800';
  return '#34D399';
}

/** Normalize top_features from either array [{feature,importance}] or Record<string,number> */
function normalizeTopFeatures(
  raw: Array<{ feature: string; importance: number }> | Record<string, number>,
): Array<{ feature: string; importance: number }> {
  if (Array.isArray(raw)) {
    return raw.map((item) => ({
      feature: String(item.feature),
      importance: Number(item.importance),
    }));
  }
  return Object.entries(raw).map(([feature, importance]) => ({
    feature,
    importance: Number(importance),
  }));
}
