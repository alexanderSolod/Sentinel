import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceArea,
} from 'recharts';
import { CLASSIFICATION_COLORS, CHART_THEME } from '../../lib/constants.ts';

interface Props {
  bss: number | null | undefined;
  pes: number | null | undefined;
}

const ACCENT = '#00F0FF';

const QUADRANT_OPACITY = 0.06;

const QUADRANTS = [
  {
    x1: 0,
    x2: 50,
    y1: 0,
    y2: 50,
    fill: CLASSIFICATION_COLORS.SPECULATOR.text,
    label: 'Speculator',
    labelX: 25,
    labelY: 25,
  },
  {
    x1: 50,
    x2: 100,
    y1: 0,
    y2: 50,
    fill: CLASSIFICATION_COLORS.INSIDER.text,
    label: 'Insider',
    labelX: 75,
    labelY: 25,
  },
  {
    x1: 0,
    x2: 50,
    y1: 50,
    y2: 100,
    fill: CLASSIFICATION_COLORS.OSINT_EDGE.text,
    label: 'OSINT Edge',
    labelX: 25,
    labelY: 75,
  },
  {
    x1: 50,
    x2: 100,
    y1: 50,
    y2: 100,
    fill: CLASSIFICATION_COLORS.FAST_REACTOR.text,
    label: 'Fast Reactor',
    labelX: 75,
    labelY: 75,
  },
] as const;

interface DataPoint {
  bss: number;
  pes: number;
}

interface TooltipPayloadEntry {
  payload: DataPoint;
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
}) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0].payload;
  return (
    <div
      className="rounded px-3 py-2 font-mono text-xs border"
      style={{
        backgroundColor: CHART_THEME.tooltipBg,
        borderColor: CHART_THEME.tooltipBorder,
        color: CHART_THEME.tooltipTextColor,
      }}
    >
      <div>
        BSS: <span className="font-semibold">{point.bss}</span>
      </div>
      <div>
        PES: <span className="font-semibold">{point.pes}</span>
      </div>
    </div>
  );
}

export default function ClassificationQuadrant({ bss, pes }: Props) {
  const hasBoth = bss != null && pes != null;
  const data: DataPoint[] = hasBoth ? [{ bss: bss!, pes: pes! }] : [];

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 20, right: 20, bottom: 25, left: 10 }}>
          <CartesianGrid
            stroke={CHART_THEME.gridColor}
            strokeDasharray="3 3"
            strokeOpacity={0.5}
          />

          {/* Quadrant backgrounds */}
          {QUADRANTS.map((q) => (
            <ReferenceArea
              key={q.label}
              x1={q.x1}
              x2={q.x2}
              y1={q.y1}
              y2={q.y2}
              fill={q.fill}
              fillOpacity={QUADRANT_OPACITY}
              strokeOpacity={0}
            />
          ))}

          {/* Center dividers */}
          <ReferenceArea
            x1={49.5}
            x2={50.5}
            y1={0}
            y2={100}
            fill={CHART_THEME.axisLineColor}
            fillOpacity={0.3}
            strokeOpacity={0}
          />
          <ReferenceArea
            x1={0}
            x2={100}
            y1={49.5}
            y2={50.5}
            fill={CHART_THEME.axisLineColor}
            fillOpacity={0.3}
            strokeOpacity={0}
          />

          {/* Quadrant labels via ReferenceArea labels */}
          {QUADRANTS.map((q) => (
            <ReferenceArea
              key={`label-${q.label}`}
              x1={q.labelX - 1}
              x2={q.labelX + 1}
              y1={q.labelY - 1}
              y2={q.labelY + 1}
              fillOpacity={0}
              strokeOpacity={0}
              label={{
                value: q.label,
                fill: q.fill,
                fontSize: 10,
                fontFamily: CHART_THEME.fontFamily,
                opacity: 0.5,
              }}
            />
          ))}

          <XAxis
            type="number"
            dataKey="bss"
            domain={[0, 100]}
            tick={{
              fontSize: CHART_THEME.fontSize,
              fill: CHART_THEME.axisLabelColor,
              fontFamily: CHART_THEME.fontFamily,
            }}
            stroke={CHART_THEME.axisLineColor}
            label={{
              value: 'BSS (Behavioral Suspicion)',
              position: 'insideBottom',
              offset: -15,
              style: {
                fontSize: 10,
                fill: CHART_THEME.axisLabelColor,
                fontFamily: CHART_THEME.fontFamily,
              },
            }}
          />
          <YAxis
            type="number"
            dataKey="pes"
            domain={[0, 100]}
            tick={{
              fontSize: CHART_THEME.fontSize,
              fill: CHART_THEME.axisLabelColor,
              fontFamily: CHART_THEME.fontFamily,
            }}
            stroke={CHART_THEME.axisLineColor}
            label={{
              value: 'PES (Public Explainability)',
              angle: -90,
              position: 'insideLeft',
              offset: 5,
              style: {
                fontSize: 10,
                fill: CHART_THEME.axisLabelColor,
                fontFamily: CHART_THEME.fontFamily,
              },
            }}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ strokeDasharray: '3 3', stroke: CHART_THEME.axisLineColor }}
          />

          <Scatter data={data} isAnimationActive>
            {data.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={ACCENT}
                stroke={ACCENT}
                strokeWidth={2}
                r={7}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      {!hasBoth && (
        <div className="text-center text-text-tertiary font-mono text-xs -mt-32">
          No BSS/PES scores available
        </div>
      )}
    </div>
  );
}
