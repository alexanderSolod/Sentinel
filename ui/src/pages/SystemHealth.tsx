import { motion } from 'framer-motion';
import {
  Cpu,
  Database as DbIcon,
  Activity,
  Wifi,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import { useHealth, useMetrics } from '../api/hooks.ts';
import Card from '../components/ui/Card.tsx';
import StatusBadge from '../components/ui/StatusBadge.tsx';
import Skeleton from '../components/ui/Skeleton.tsx';
import { formatNumber } from '../lib/formatters.ts';
import { CLASSIFICATION_COLORS, CHART_THEME } from '../lib/constants.ts';

// ---------------------------------------------------------------------------
// Classification chart colors
// ---------------------------------------------------------------------------

const CLASS_COLORS: Record<string, string> = {
  INSIDER: '#FF2D55',
  OSINT_EDGE: '#FF6B2D',
  FAST_REACTOR: '#FFB800',
  SPECULATOR: '#34D399',
};

// ---------------------------------------------------------------------------
// Metric card (stat tile)
// ---------------------------------------------------------------------------

interface StatCardProps {
  label: string;
  value: number | undefined;
  icon: React.ReactNode;
  loading: boolean;
  delay?: number;
}

function StatCard({ label, value, icon, loading, delay = 0 }: StatCardProps) {
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
// Status dot
// ---------------------------------------------------------------------------

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className="pulse-dot inline-block w-2.5 h-2.5 rounded-full shrink-0"
      style={{ backgroundColor: ok ? '#00FF88' : '#FF2D55' }}
    />
  );
}

// ---------------------------------------------------------------------------
// Custom chart tooltip
// ---------------------------------------------------------------------------

interface ChartTooltipEntry {
  name: string;
  value: number;
  payload: { name: string; value: number; fill: string };
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: ChartTooltipEntry[];
}) {
  if (!active || !payload?.length) return null;
  const entry = payload[0];
  return (
    <div
      className="rounded px-3 py-2 font-mono text-xs shadow-lg"
      style={{
        backgroundColor: CHART_THEME.tooltipBg,
        border: `1px solid ${CHART_THEME.tooltipBorder}`,
        color: CHART_THEME.tooltipTextColor,
      }}
    >
      <span style={{ color: entry.payload.fill }}>{entry.name}</span>
      {': '}
      <span className="font-semibold">{entry.value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Confusion Matrix Cell
// ---------------------------------------------------------------------------

function MatrixCell({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center p-3 rounded-lg border border-border-subtle bg-bg-tertiary">
      <span className="overline mb-1">{label}</span>
      <span className="font-display text-2xl font-bold" style={{ color }}>
        {value}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SystemHealth page
// ---------------------------------------------------------------------------

export default function SystemHealth() {
  const { data: health, loading: healthLoading } = useHealth();
  const { data: metrics, loading: metricsLoading } = useMetrics();

  const stats = health?.stats;
  const dbOk = health?.database?.status === 'ok';
  const apiOk = health?.status === 'ok';

  // Classification distribution chart data
  const classificationData = stats?.cases_by_classification
    ? Object.entries(stats.cases_by_classification).map(([key, value]) => ({
        name:
          CLASSIFICATION_COLORS[key as keyof typeof CLASSIFICATION_COLORS]?.label ?? key,
        value,
        fill: CLASS_COLORS[key] ?? '#55556A',
      }))
    : [];

  // Case status data
  const statusData = stats?.cases_by_status
    ? Object.entries(stats.cases_by_status)
    : [];

  // Evaluation data
  const evaluation = metrics?.evaluation ?? null;
  const confusion = evaluation?.binary_confusion_matrix?.counts ?? null;

  // FPR/FNR bar data
  const rateBarData =
    evaluation?.metrics
      ? [
          {
            name: 'FPR',
            value: (evaluation.metrics.fpr ?? 0) * 100,
            fill: (evaluation.metrics.fpr ?? 0) > 0.2 ? '#FF2D55' : '#FFB800',
          },
          {
            name: 'FNR',
            value: (evaluation.metrics.fnr ?? 0) * 100,
            fill: (evaluation.metrics.fnr ?? 0) > 0.2 ? '#FF2D55' : '#FFB800',
          },
        ]
      : [];

  return (
    <div className="space-y-6">
      {/* ---- Page Title ---- */}
      <div>
        <p className="overline mb-1">// SYSTEM</p>
        <h1 className="font-display text-2xl font-bold text-text-primary">
          System Health
        </h1>
      </div>

      {/* ---- Status Row ---- */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Database */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          className="bg-bg-secondary border border-border-subtle rounded-lg p-4 hover:border-border-default transition-colors duration-200"
        >
          <div className="flex items-center gap-2 mb-3">
            <DbIcon size={16} className="text-text-tertiary" />
            <span className="overline">DATABASE</span>
          </div>
          {healthLoading ? (
            <Skeleton className="h-5 w-32" />
          ) : (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <StatusDot ok={dbOk} />
                <span className="font-mono text-sm text-text-primary">
                  {dbOk ? 'Connected' : 'Error'}
                </span>
              </div>
              {health?.database?.path && (
                <p className="font-mono text-[11px] text-text-tertiary truncate" title={health.database.path}>
                  {health.database.path}
                </p>
              )}
            </div>
          )}
        </motion.div>

        {/* API Status */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
          className="bg-bg-secondary border border-border-subtle rounded-lg p-4 hover:border-border-default transition-colors duration-200"
        >
          <div className="flex items-center gap-2 mb-3">
            <Cpu size={16} className="text-text-tertiary" />
            <span className="overline">API STATUS</span>
          </div>
          {healthLoading ? (
            <Skeleton className="h-5 w-24" />
          ) : (
            <div className="flex items-center gap-2">
              <StatusDot ok={apiOk} />
              <span className="font-mono text-sm text-text-primary">
                {apiOk ? 'Operational' : 'Degraded'}
              </span>
            </div>
          )}
        </motion.div>

        {/* Monitoring */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="bg-bg-secondary border border-border-subtle rounded-lg p-4 hover:border-border-default transition-colors duration-200"
        >
          <div className="flex items-center gap-2 mb-3">
            <Wifi size={16} className="text-text-tertiary" />
            <span className="overline">MONITORING</span>
          </div>
          {healthLoading ? (
            <Skeleton className="h-5 w-28" />
          ) : (
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <StatusDot ok={(stats?.total_evidence_packets ?? 0) > 0} />
                <span className="font-mono text-sm text-text-primary">
                  {(stats?.total_evidence_packets ?? 0) > 0 ? 'Active' : 'Idle'}
                </span>
              </div>
              <p className="font-mono text-[11px] text-text-tertiary">
                {formatNumber(stats?.total_evidence_packets ?? 0)} evidence packets
              </p>
            </div>
          )}
        </motion.div>
      </div>

      {/* ---- Database Statistics ---- */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <StatCard
          label="ANOMALY EVENTS"
          value={stats?.total_anomalies}
          icon={<AlertCircle size={18} />}
          loading={healthLoading}
          delay={0}
        />
        <StatCard
          label="OSINT EVENTS"
          value={stats?.total_osint_events}
          icon={<Activity size={18} />}
          loading={healthLoading}
          delay={0.05}
        />
        <StatCard
          label="WALLET PROFILES"
          value={stats?.total_wallets}
          icon={<Cpu size={18} />}
          loading={healthLoading}
          delay={0.1}
        />
        <StatCard
          label="INDEXED CASES"
          value={stats?.total_cases}
          icon={<DbIcon size={18} />}
          loading={healthLoading}
          delay={0.15}
        />
        <StatCard
          label="EVIDENCE PACKETS"
          value={stats?.total_evidence_packets}
          icon={<CheckCircle2 size={18} />}
          loading={healthLoading}
          delay={0.2}
        />
      </div>

      {/* ---- Charts Row ---- */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* ---- Classification Distribution ---- */}
        <Card title="CLASSIFICATION DISTRIBUTION">
          {healthLoading ? (
            <div className="flex justify-center py-10">
              <Skeleton className="h-[220px] w-[220px] rounded-full" />
            </div>
          ) : classificationData.length === 0 ? (
            <p className="font-mono text-sm text-text-tertiary text-center py-10">
              No classification data available
            </p>
          ) : (
            <div>
              <div style={{ width: '100%', height: 260 }}>
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={classificationData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      strokeWidth={0}
                      paddingAngle={2}
                    >
                      {classificationData.map((entry, index) => (
                        <Cell key={`class-cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              {/* Legend */}
              <div className="flex flex-wrap items-center justify-center gap-4 mt-3">
                {classificationData.map((item) => (
                  <div key={item.name} className="flex items-center gap-1.5">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: item.fill }}
                    />
                    <span className="font-mono text-[11px] text-text-secondary">
                      {item.name}: {item.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>

        {/* ---- Case Status Summary ---- */}
        <Card title="CASE STATUS SUMMARY">
          {healthLoading ? (
            <div className="space-y-3 py-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : statusData.length === 0 ? (
            <p className="font-mono text-sm text-text-tertiary text-center py-10">
              No status data available
            </p>
          ) : (
            <div className="space-y-3">
              {statusData.map(([status, count]) => (
                <div
                  key={status}
                  className="flex items-center justify-between p-3 rounded-lg border border-border-subtle bg-bg-tertiary hover:border-border-default transition-colors"
                >
                  <StatusBadge status={status} />
                  <span className="font-display text-lg font-bold text-text-primary">
                    {formatNumber(count)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* ---- Evaluation Metrics ---- */}
      <Card title="EVALUATION METRICS">
        {metricsLoading ? (
          <div className="space-y-4 py-4">
            <Skeleton className="h-12 w-48" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : !evaluation ? (
          <div className="py-12 text-center">
            <XCircle size={36} className="mx-auto mb-3 text-text-tertiary" />
            <p className="font-mono text-sm text-text-tertiary">
              Run evaluation to see metrics
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Top metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {/* Arena Consensus Accuracy */}
              <div className="text-center p-4 rounded-lg border border-border-subtle bg-bg-tertiary">
                <p className="overline mb-2">CONSENSUS ACCURACY</p>
                <span className="font-display text-4xl font-bold text-accent">
                  {evaluation.arena_consensus.consensus_accuracy != null
                    ? `${(evaluation.arena_consensus.consensus_accuracy * 100).toFixed(1)}%`
                    : '--'}
                </span>
                <div className="mt-2 flex justify-center gap-4 font-mono text-[11px] text-text-tertiary">
                  <span>Confirmed: {evaluation.arena_consensus.confirmed_cases}</span>
                  <span>Disputed: {evaluation.arena_consensus.disputed_cases}</span>
                </div>
              </div>

              {/* Accuracy */}
              <div className="text-center p-4 rounded-lg border border-border-subtle bg-bg-tertiary">
                <p className="overline mb-2">ACCURACY</p>
                <span className="font-display text-4xl font-bold text-status-online">
                  {evaluation.metrics.accuracy != null
                    ? `${(evaluation.metrics.accuracy * 100).toFixed(1)}%`
                    : '--'}
                </span>
                <div className="mt-2 font-mono text-[11px] text-text-tertiary">
                  {evaluation.coverage.evaluated_cases} / {evaluation.coverage.total_cases} cases evaluated
                </div>
              </div>

              {/* Coverage */}
              <div className="text-center p-4 rounded-lg border border-border-subtle bg-bg-tertiary">
                <p className="overline mb-2">COVERAGE</p>
                <span className="font-display text-4xl font-bold text-threat-medium">
                  {evaluation.coverage.total_cases > 0
                    ? `${((evaluation.coverage.evaluated_cases / evaluation.coverage.total_cases) * 100).toFixed(0)}%`
                    : '--'}
                </span>
                <div className="mt-2 font-mono text-[11px] text-text-tertiary">
                  Min votes: {evaluation.coverage.min_votes}
                </div>
              </div>
            </div>

            {/* FPR / FNR Bars */}
            {rateBarData.length > 0 && (
              <div>
                <p className="overline mb-3">FALSE POSITIVE / FALSE NEGATIVE RATES</p>
                <div style={{ width: '100%', height: 120 }}>
                  <ResponsiveContainer>
                    <BarChart
                      data={rateBarData}
                      layout="vertical"
                      margin={{ top: 0, right: 20, bottom: 0, left: 40 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke={CHART_THEME.gridColor}
                        horizontal={false}
                      />
                      <XAxis
                        type="number"
                        domain={[0, 100]}
                        tick={{ fill: CHART_THEME.axisLabelColor, fontSize: CHART_THEME.fontSize }}
                        axisLine={{ stroke: CHART_THEME.axisLineColor }}
                        tickLine={false}
                        tickFormatter={(v: number) => `${v}%`}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fill: CHART_THEME.axisLabelColor, fontSize: CHART_THEME.fontSize, fontFamily: CHART_THEME.fontFamily }}
                        axisLine={false}
                        tickLine={false}
                        width={35}
                      />
                      <Tooltip
                        cursor={false}
                        content={({ active, payload }) => {
                          if (!active || !payload?.length) return null;
                          const entry = payload[0];
                          return (
                            <div
                              className="rounded px-3 py-2 font-mono text-xs shadow-lg"
                              style={{
                                backgroundColor: CHART_THEME.tooltipBg,
                                border: `1px solid ${CHART_THEME.tooltipBorder}`,
                                color: CHART_THEME.tooltipTextColor,
                              }}
                            >
                              {entry.name}: <span className="font-semibold">{typeof entry.value === 'number' ? entry.value.toFixed(1) : entry.value}%</span>
                            </div>
                          );
                        }}
                      />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={20}>
                        {rateBarData.map((entry, index) => (
                          <Cell key={`rate-cell-${index}`} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Confusion Matrix */}
            {confusion && (
              <div>
                <p className="overline mb-3">BINARY CONFUSION MATRIX</p>
                <div className="grid grid-cols-2 gap-3 max-w-xs">
                  <MatrixCell label="TP" value={confusion.tp} color="#00FF88" />
                  <MatrixCell label="FP" value={confusion.fp} color="#FF2D55" />
                  <MatrixCell label="FN" value={confusion.fn} color="#FFB800" />
                  <MatrixCell label="TN" value={confusion.tn} color="#34D399" />
                </div>
                <div className="mt-2 grid grid-cols-2 gap-3 max-w-xs font-mono text-[10px] text-text-tertiary">
                  <span className="text-center">Predicted Positive</span>
                  <span className="text-center">Predicted Negative</span>
                </div>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
