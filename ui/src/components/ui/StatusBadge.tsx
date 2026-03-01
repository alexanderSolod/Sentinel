import { STATUS_COLORS } from '../../lib/constants.ts';

interface Props {
  status: string | null | undefined;
}

export default function StatusBadge({ status }: Props) {
  const key = status as keyof typeof STATUS_COLORS;
  const colors = STATUS_COLORS[key] || { text: '#55556A', bg: '#55556A0F' };
  const label = status?.replace(/_/g, ' ') || 'Unknown';

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full font-mono text-[10px] font-semibold uppercase tracking-wider"
      style={{ color: colors.text, backgroundColor: colors.bg }}
    >
      {label}
    </span>
  );
}
