export function formatRelativeTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  return `${diffDays}d ago`;
}

export function formatAbsoluteTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  return new Date(isoString).toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
}

export function truncateAddress(address: string | null | undefined, chars = 4): string {
  if (!address) return '—';
  if (address.length <= chars * 2 + 2) return address;
  return `${address.slice(0, chars + 2)}...${address.slice(-chars)}`;
}

export function formatNumber(n: number | null | undefined): string {
  if (n == null) return '—';
  return n.toLocaleString('en-US');
}

export function formatPercent(n: number | null | undefined): string {
  if (n == null) return '—';
  return `${n.toFixed(1)}%`;
}

export function scoreColor(score: number | null | undefined): string {
  if (score == null) return '#55556A';
  if (score > 70) return '#FF2D55';
  if (score > 40) return '#FFB800';
  return '#34D399';
}
