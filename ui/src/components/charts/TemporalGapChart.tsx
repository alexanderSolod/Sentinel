import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Diamond, Circle, Star } from 'lucide-react';
import type { EvidenceJson, OsintSignal } from '../../api/types.ts';

interface Props {
  evidence: EvidenceJson | null | undefined;
  classification?: string | null | undefined;
}

interface TimelineEvent {
  type: 'trade' | 'osint' | 'news';
  label: string;
  hoursFromTrade: number;
  source?: string;
}

const TRADE_COLOR = '#ff8c00';
const OSINT_COLOR = '#33ff33';
const NEWS_COLOR = '#ff8c00';
const GAP_SUSPICIOUS = '#ff202033';
const GAP_SAFE = '#33ff3322';
const TIMELINE_COLOR = '#33ff3366';

const SUSPICIOUS_CLASSIFICATIONS = ['INSIDER', 'OSINT_EDGE'];

export default function TemporalGapChart({ evidence, classification }: Props) {
  const events = useMemo<TimelineEvent[]>(() => {
    if (!evidence) return [];
    const items: TimelineEvent[] = [];

    // Trade is always at 0
    items.push({
      type: 'trade',
      label: 'Trade executed',
      hoursFromTrade: 0,
    });

    // OSINT signals
    if (evidence.osint_signals && evidence.osint_signals.length > 0) {
      evidence.osint_signals.forEach((s: OsintSignal) => {
        items.push({
          type: 'osint',
          label: s.headline,
          hoursFromTrade: Number(s.hours_before_trade),
          source: s.source,
        });
      });
    }

    // News event — try multiple sources for timing data
    let newsAdded = false;

    // Method 1: news_headline + news_timestamp (compute gap from timestamps)
    if (evidence.news_headline && evidence.news_timestamp && evidence.trade_timestamp) {
      const tradeTime = new Date(evidence.trade_timestamp).getTime();
      const newsTime = new Date(evidence.news_timestamp).getTime();
      const hoursDiff = (tradeTime - newsTime) / (1000 * 60 * 60);

      const alreadyPresent = evidence.osint_signals?.some(
        (s) => s.headline === evidence.news_headline,
      );
      if (!alreadyPresent) {
        items.push({
          type: 'news',
          label: evidence.news_headline,
          hoursFromTrade: hoursDiff,
        });
        newsAdded = true;
      }
    }

    // Method 2: hours_before_news is available (from pipeline --live)
    if (!newsAdded && evidence.hours_before_news != null && Number(evidence.hours_before_news) !== 0) {
      items.push({
        type: 'news',
        label: evidence.news_headline ?? 'Public information event',
        hoursFromTrade: Number(evidence.hours_before_news),
      });
    }

    return items;
  }, [evidence]);

  if (!evidence || events.length <= 1) {
    return (
      <div className="flex items-center justify-center h-48 text-text-tertiary font-mono text-sm">
        No temporal data available
      </div>
    );
  }

  // Compute timeline extent
  const allHours = events.map((e) => e.hoursFromTrade);
  const minHour = Math.min(...allHours);
  const maxHour = Math.max(...allHours);
  const range = maxHour - minHour || 1;
  const padding = range * 0.15;
  const domainMin = minHour - padding;
  const domainMax = maxHour + padding;
  const domainRange = domainMax - domainMin;

  // SVG dimensions
  const svgWidth = 900;
  const svgHeight = 200;
  const marginLeft = 40;
  const marginRight = 40;
  const plotWidth = svgWidth - marginLeft - marginRight;
  const centerY = svgHeight / 2;

  const xScale = (hours: number) =>
    marginLeft + ((hours - domainMin) / domainRange) * plotWidth;

  // First OSINT event (closest to trade)
  const osintEvents = events.filter((e) => e.type === 'osint' || e.type === 'news');
  const closestOsint = osintEvents.length > 0
    ? osintEvents.reduce((closest, e) =>
        Math.abs(e.hoursFromTrade) < Math.abs(closest.hoursFromTrade) ? e : closest,
      )
    : null;

  const tradeBeforeNews = closestOsint ? closestOsint.hoursFromTrade > 0 : false;
  const gapHours = closestOsint ? Math.abs(closestOsint.hoursFromTrade) : 0;
  const gapHoursWhole = Math.floor(gapHours);
  const gapMinutes = Math.round((gapHours - gapHoursWhole) * 60);
  const gapColor = tradeBeforeNews ? GAP_SUSPICIOUS : GAP_SAFE;

  const isPulsing = SUSPICIOUS_CLASSIFICATIONS.includes(classification ?? '');

  // Gap rectangle coordinates
  const gapX1 = closestOsint ? Math.min(xScale(0), xScale(closestOsint.hoursFromTrade)) : 0;
  const gapX2 = closestOsint ? Math.max(xScale(0), xScale(closestOsint.hoursFromTrade)) : 0;
  const gapWidth = gapX2 - gapX1;

  // Time labels on the axis
  const tickCount = 5;
  const ticks: number[] = [];
  for (let i = 0; i <= tickCount; i++) {
    ticks.push(domainMin + (domainRange / tickCount) * i);
  }

  const formatTickLabel = (hours: number): string => {
    const abs = Math.abs(hours);
    if (abs < 1) return `${Math.round(abs * 60)}m`;
    if (abs < 24) return `${abs.toFixed(1)}h`;
    return `${(abs / 24).toFixed(1)}d`;
  };

  return (
    <div className="w-full">
      {/* Gap label */}
      {closestOsint && (
        <div className="text-center mb-3">
          <span
            className="font-mono text-lg font-bold"
            style={{ color: tradeBeforeNews ? '#ff2020' : '#33ff33', textShadow: tradeBeforeNews ? '0 0 8px #ff202066' : '0 0 8px #33ff3366' }}
          >
            {gapHoursWhole > 0 ? `${gapHoursWhole}h ` : ''}
            {gapMinutes}m{' '}
            {tradeBeforeNews ? 'BEFORE' : 'AFTER'} public information
          </span>
        </div>
      )}

      <svg
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className="w-full"
        style={{ maxHeight: '200px' }}
      >
        {/* Timeline axis */}
        <line
          x1={marginLeft}
          y1={centerY}
          x2={svgWidth - marginRight}
          y2={centerY}
          stroke={TIMELINE_COLOR}
          strokeWidth={2}
        />

        {/* Tick marks */}
        {ticks.map((t, i) => (
          <g key={i}>
            <line
              x1={xScale(t)}
              y1={centerY - 4}
              x2={xScale(t)}
              y2={centerY + 4}
              stroke={TIMELINE_COLOR}
              strokeWidth={1}
            />
            <text
              x={xScale(t)}
              y={centerY + 22}
              textAnchor="middle"
              fill="#33ff3399"
              fontSize={10}
              fontFamily="Courier New, monospace"
            >
              {t === 0 ? '0' : `${t > 0 ? '+' : '-'}${formatTickLabel(t)}`}
            </text>
          </g>
        ))}

        {/* Gap shading */}
        {closestOsint && gapWidth > 0 && (
          <>
            {isPulsing ? (
              <motion.rect
                x={gapX1}
                y={centerY - 50}
                width={gapWidth}
                height={100}
                rx={4}
                fill={gapColor}
                initial={{ opacity: 0.5 }}
                animate={{ opacity: [0.3, 0.7, 0.3] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
              />
            ) : (
              <rect
                x={gapX1}
                y={centerY - 50}
                width={gapWidth}
                height={100}
                rx={4}
                fill={gapColor}
              />
            )}
            {/* Gap border lines */}
            <line
              x1={gapX1}
              y1={centerY - 50}
              x2={gapX1}
              y2={centerY + 50}
              stroke={tradeBeforeNews ? NEWS_COLOR : '#34D399'}
              strokeWidth={1}
              strokeDasharray="4 2"
              opacity={0.4}
            />
            <line
              x1={gapX2}
              y1={centerY - 50}
              x2={gapX2}
              y2={centerY + 50}
              stroke={tradeBeforeNews ? NEWS_COLOR : '#34D399'}
              strokeWidth={1}
              strokeDasharray="4 2"
              opacity={0.4}
            />
          </>
        )}

        {/* OSINT event markers */}
        {events
          .filter((e) => e.type === 'osint')
          .map((e, i) => {
            const cx = xScale(e.hoursFromTrade);
            return (
              <g key={`osint-${i}`}>
                <circle
                  cx={cx}
                  cy={centerY}
                  r={6}
                  fill={OSINT_COLOR}
                  fillOpacity={0.9}
                  stroke={OSINT_COLOR}
                  strokeWidth={1.5}
                  strokeOpacity={0.4}
                />
                {/* Label */}
                <text
                  x={cx}
                  y={centerY - 16}
                  textAnchor="middle"
                  fill={OSINT_COLOR}
                  fontSize={9}
                  fontFamily="Courier New, monospace"
                >
                  {e.source ?? 'OSINT'}
                </text>
                <title>{e.label}</title>
              </g>
            );
          })}

        {/* News event marker */}
        {events
          .filter((e) => e.type === 'news')
          .map((e, i) => {
            const cx = xScale(e.hoursFromTrade);
            return (
              <g key={`news-${i}`}>
                {/* Star shape via polygon */}
                <polygon
                  points={starPoints(cx, centerY, 8, 4)}
                  fill={NEWS_COLOR}
                  fillOpacity={0.9}
                  stroke={NEWS_COLOR}
                  strokeWidth={1}
                  strokeOpacity={0.4}
                />
                <text
                  x={cx}
                  y={centerY - 18}
                  textAnchor="middle"
                  fill={NEWS_COLOR}
                  fontSize={9}
                  fontFamily="Courier New, monospace"
                >
                  NEWS
                </text>
                <title>{e.label}</title>
              </g>
            );
          })}

        {/* Trade marker (diamond) */}
        {events
          .filter((e) => e.type === 'trade')
          .map((e, i) => {
            const cx = xScale(e.hoursFromTrade);
            return (
              <g key={`trade-${i}`}>
                <polygon
                  points={`${cx},${centerY - 10} ${cx + 8},${centerY} ${cx},${centerY + 10} ${cx - 8},${centerY}`}
                  fill={TRADE_COLOR}
                  fillOpacity={0.9}
                  stroke={TRADE_COLOR}
                  strokeWidth={1.5}
                  strokeOpacity={0.5}
                />
                {/* Glow effect */}
                <polygon
                  points={`${cx},${centerY - 10} ${cx + 8},${centerY} ${cx},${centerY + 10} ${cx - 8},${centerY}`}
                  fill="none"
                  stroke={TRADE_COLOR}
                  strokeWidth={3}
                  strokeOpacity={0.15}
                />
                <text
                  x={cx}
                  y={centerY + 36}
                  textAnchor="middle"
                  fill={TRADE_COLOR}
                  fontSize={10}
                  fontWeight={600}
                  fontFamily="Courier New, monospace"
                >
                  TRADE
                </text>
              </g>
            );
          })}

        {/* Axis labels */}
        <text
          x={marginLeft}
          y={svgHeight - 6}
          fill="#33ff3399"
          fontSize={9}
          fontFamily="Courier New, monospace"
        >
          &larr; Earlier
        </text>
        <text
          x={svgWidth - marginRight}
          y={svgHeight - 6}
          textAnchor="end"
          fill="#33ff3399"
          fontSize={9}
          fontFamily="Courier New, monospace"
        >
          Later &rarr;
        </text>
      </svg>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 mt-2 font-mono text-[10px] text-text-tertiary">
        <span className="inline-flex items-center gap-1.5">
          <Diamond size={10} color={TRADE_COLOR} fill={TRADE_COLOR} />
          Trade
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Circle size={10} color={OSINT_COLOR} fill={OSINT_COLOR} />
          OSINT Signal
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Star size={10} color={NEWS_COLOR} fill={NEWS_COLOR} />
          News
        </span>
      </div>
    </div>
  );
}

/** Generate SVG star polygon points string */
function starPoints(cx: number, cy: number, outerR: number, innerR: number, tips = 5): string {
  const points: string[] = [];
  for (let i = 0; i < tips * 2; i++) {
    const angle = (Math.PI / tips) * i - Math.PI / 2;
    const r = i % 2 === 0 ? outerR : innerR;
    points.push(`${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`);
  }
  return points.join(' ');
}
