import { scoreColor } from '../../lib/formatters.ts';
import Tooltip from './Tooltip.tsx';

interface Props {
  label: string;
  score: number | null | undefined;
  max?: number;
  tooltip?: string;
}

export default function ScoreBar({ label, score, max = 100, tooltip }: Props) {
  const value = score ?? 0;
  const pct = Math.min(100, (value / max) * 100);
  const color = scoreColor(score);

  const labelEl = (
    <span
      className={`font-mono text-sm text-text-secondary w-10 shrink-0 ${
        tooltip ? 'underline decoration-dotted decoration-text-tertiary underline-offset-2 cursor-help' : ''
      }`}
    >
      {label}
    </span>
  );

  return (
    <div className="flex items-center gap-3">
      {tooltip ? <Tooltip content={tooltip} position="bottom">{labelEl}</Tooltip> : labelEl}
      <div className="flex-1 h-1.5 rounded-full bg-border-subtle overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="font-mono text-sm font-semibold w-8 text-right" style={{ color }}>
        {score ?? '—'}
      </span>
    </div>
  );
}
