import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { CHART_THEME } from '../../lib/constants.ts';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface VoteDonutProps {
  votes_agree: number;
  votes_disagree: number;
  votes_uncertain: number;
}

// ---------------------------------------------------------------------------
// Colors
// ---------------------------------------------------------------------------

const VOTE_COLORS = {
  Agree: '#00FF88',
  Disagree: '#FF2D55',
  Uncertain: '#FFB800',
} as const;

const EMPTY_COLOR = '#2A2A3E';

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------

interface TooltipPayloadEntry {
  name: string;
  value: number;
  payload: { name: string; value: number; fill: string };
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
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
// VoteDonut
// ---------------------------------------------------------------------------

export default function VoteDonut({
  votes_agree,
  votes_disagree,
  votes_uncertain,
}: VoteDonutProps) {
  const total = votes_agree + votes_disagree + votes_uncertain;
  const isEmpty = total === 0;

  const data = isEmpty
    ? [{ name: 'No votes', value: 1, fill: EMPTY_COLOR }]
    : [
        { name: 'Agree', value: votes_agree, fill: VOTE_COLORS.Agree },
        { name: 'Disagree', value: votes_disagree, fill: VOTE_COLORS.Disagree },
        { name: 'Uncertain', value: votes_uncertain, fill: VOTE_COLORS.Uncertain },
      ].filter((d) => d.value > 0);

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: 180, height: 180 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={80}
              strokeWidth={0}
              paddingAngle={isEmpty ? 0 : 2}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
            {!isEmpty && <Tooltip content={<CustomTooltip />} />}
          </PieChart>
        </ResponsiveContainer>

        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="font-display text-2xl font-bold text-text-primary">
            {isEmpty ? '0' : total}
          </span>
          <span className="font-mono text-[10px] text-text-tertiary uppercase tracking-wider">
            {isEmpty ? 'No votes' : 'votes'}
          </span>
        </div>
      </div>

      {/* Legend */}
      {!isEmpty && (
        <div className="flex items-center gap-4">
          {[
            { label: 'Agree', value: votes_agree, color: VOTE_COLORS.Agree },
            { label: 'Disagree', value: votes_disagree, color: VOTE_COLORS.Disagree },
            { label: 'Uncertain', value: votes_uncertain, color: VOTE_COLORS.Uncertain },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-1.5">
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: item.color }}
              />
              <span className="font-mono text-[11px] text-text-secondary">
                {item.label}: {item.value}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
