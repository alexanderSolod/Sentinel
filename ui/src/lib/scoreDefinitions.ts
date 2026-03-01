export const SCORE_DEFINITIONS = {
  BSS: {
    label: 'BSS',
    short: 'Behavioral Suspicion Score',
    long: 'Behavioral Suspicion Score (0-100). Measures how suspicious the trading behavior is. Higher = more suspicious. Factors: fresh wallet (+25), trade before news (+30), no OSINT signals (+15), high z-score (+15), high win rate (+10), mixer funding (+15).',
  },
  PES: {
    label: 'PES',
    short: 'Public Explainability Score',
    long: 'Public Explainability Score (0-100). Measures how well publicly available information explains the trade. Higher = more explainable by public info. Inverse relationship with BSS.',
  },
  Z_SCORE: {
    label: 'Z-Score',
    short: 'Volume Deviation Statistic',
    long: 'Statistical measure of volume deviation from baseline. z = (current_volume - mean) / stdev. Values >= 2.0 flag anomalous volume spikes. Higher values indicate more unusual trading activity.',
  },
  CONSENSUS: {
    label: 'Consensus',
    short: 'Community Vote Confidence',
    long: 'Consensus Score (0-100). Aggregated community vote confidence from the Arena voting system. Reflects collective analyst agreement on the case classification.',
  },
} as const;
