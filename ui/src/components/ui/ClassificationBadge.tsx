interface Props {
  classification: string | null | undefined;
  size?: 'sm' | 'md';
}

const CONFIG: Record<string, { color: string; symbol: string; label: string }> = {
  INSIDER:      { color: '#ff2020', symbol: '▲', label: 'INSIDER' },
  OSINT_EDGE:   { color: '#33ff33', symbol: '●', label: 'OSINT EDGE' },
  FAST_REACTOR: { color: '#ff8c00', symbol: '◆', label: 'FAST REACTOR' },
  SPECULATOR:   { color: '#ff6b0066', symbol: '○', label: 'SPECULATOR' },
};

export default function ClassificationBadge({ classification, size = 'md' }: Props) {
  const cfg = CONFIG[classification ?? ''] ?? { color: '#ff6b0044', symbol: '○', label: classification ?? 'UNKNOWN' };
  const fs = size === 'sm' ? 10 : 11;

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 5,
      border: `1px solid ${cfg.color}`,
      color: cfg.color,
      background: `${cfg.color}18`,
      fontFamily: 'Courier New, monospace',
      fontSize: fs,
      fontWeight: 700,
      letterSpacing: '0.12em',
      padding: size === 'sm' ? '2px 6px' : '3px 8px',
      textShadow: `0 0 6px ${cfg.color}88`,
      whiteSpace: 'nowrap',
    }}>
      {cfg.symbol} {cfg.label}
    </span>
  );
}
