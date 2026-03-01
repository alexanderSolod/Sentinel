export const CLASSIFICATION_COLORS = {
  INSIDER:      { text: '#FF2D55', bg: '#FF2D550F', label: 'Insider' },
  OSINT_EDGE:   { text: '#FF6B2D', bg: '#FF6B2D0F', label: 'OSINT Edge' },
  FAST_REACTOR: { text: '#FFB800', bg: '#FFB8000F', label: 'Fast Reactor' },
  SPECULATOR:   { text: '#34D399', bg: '#34D3990F', label: 'Speculator' },
} as const;

export const STATUS_COLORS = {
  CONFIRMED:    { text: '#00FF88', bg: '#00FF880F' },
  DISPUTED:     { text: '#FF2D55', bg: '#FF2D550F' },
  UNDER_REVIEW: { text: '#00F0FF', bg: '#00F0FF0F' },
} as const;

export const CHART_THEME = {
  backgroundColor: 'transparent',
  gridColor: '#1A1A2E',
  axisLabelColor: '#55556A',
  axisLineColor: '#2A2A3E',
  tooltipBg: '#0F0F18',
  tooltipBorder: '#2A2A3E',
  tooltipTextColor: '#E8E8F0',
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 11,
} as const;
