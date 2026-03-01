import { CLASSIFICATION_COLORS } from '../../lib/constants.ts';

interface Props {
  classification: string | null | undefined;
  size?: 'sm' | 'md';
}

export default function ClassificationBadge({ classification, size = 'md' }: Props) {
  const key = classification as keyof typeof CLASSIFICATION_COLORS;
  const colors = CLASSIFICATION_COLORS[key] || { text: '#55556A', bg: '#55556A0F', label: classification || 'Unknown' };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-mono font-semibold uppercase tracking-wider ${
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-[11px]'
      }`}
      style={{ color: colors.text, backgroundColor: colors.bg }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: colors.text }} />
      {colors.label}
    </span>
  );
}
