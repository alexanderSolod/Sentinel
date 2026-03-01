import { scoreColor } from '../../lib/formatters.ts';

interface Props {
  label: string;
  score: number | null | undefined;
  max?: number;
}

export default function ScoreBar({ label, score, max = 100 }: Props) {
  const value = score ?? 0;
  const pct = Math.min(100, (value / max) * 100);
  const color = scoreColor(score);

  return (
    <div className="flex items-center gap-3">
      <span className="font-mono text-xs text-text-secondary w-8 shrink-0">{label}</span>
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
