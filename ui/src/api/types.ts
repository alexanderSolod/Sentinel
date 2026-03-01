// ---------------------------------------------------------------------------
// Classification string literal unions (no enums – erasableSyntaxOnly)
// ---------------------------------------------------------------------------

export type Classification = 'INSIDER' | 'OSINT_EDGE' | 'FAST_REACTOR' | 'SPECULATOR';

export type CaseStatus = 'CONFIRMED' | 'DISPUTED' | 'UNDER_REVIEW';

export type VoteValue = 'agree' | 'disagree' | 'uncertain';

// ---------------------------------------------------------------------------
// Anomaly (anomaly_events table)
// ---------------------------------------------------------------------------

export interface FraudTriangle {
  pressure: string;
  opportunity: string;
  rationalization: string;
}

export interface Anomaly {
  event_id: string;
  market_id: string;
  market_name: string | null;
  timestamp: string;
  trade_timestamp: string | null;
  wallet_address: string | null;
  trade_size: number | null;
  position_side: string | null;
  price_before: number | null;
  price_after: number | null;
  price_change: number | null;
  volume_24h: number | null;
  volume_spike_ratio: number | null;
  z_score: number | null;
  classification: Classification | null;
  bss_score: number | null;
  pes_score: number | null;
  confidence: number | null;
  xai_narrative: string | null;
  fraud_triangle: FraudTriangle | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// EvidenceJson (decoded evidence_json blob inside SentinelCase)
// ---------------------------------------------------------------------------

export interface OsintSignal {
  source: string;
  headline: string;
  hours_before_trade: number;
}

export interface GateEvaluation {
  gates_passed: Array<{ gate: string; decision: string; score: number }>;
}

export interface RfAnalysis {
  rf_score: number;
  top_features: Record<string, number>;
}

export interface GameTheoryAnalysis {
  game_theory_suspicion_score: number;
  best_fit_type: string;
}

export interface NlpRelevance {
  source: string;
  composite_relevance: number;
}

export interface EvidenceClassification {
  case_id: string;
  event_id: string;
  classification: string;
  bss_score: number;
  pes_score: number;
  confidence: number;
  rf_score: number;
  game_theory_score: number;
}

export interface EvidenceJson {
  trade_timestamp: string | null;
  news_timestamp: string | null;
  news_headline: string | null;
  trade_size_usd: number | null;
  osint_signals: OsintSignal[] | null;
  gate_evaluation: GateEvaluation | null;
  rf_analysis: RfAnalysis | null;
  game_theory_analysis: GameTheoryAnalysis | null;
  nlp_relevance: NlpRelevance[] | null;
  classification: EvidenceClassification | null;
}

// ---------------------------------------------------------------------------
// SentinelCase (sentinel_index table)
// ---------------------------------------------------------------------------

export interface SentinelCase {
  case_id: string;
  anomaly_event_id: string | null;
  market_id: string;
  market_name: string | null;
  classification: Classification;
  bss_score: number | null;
  pes_score: number | null;
  temporal_gap_hours: number | null;
  consensus_score: number | null;
  vote_count: number;
  votes_agree: number;
  votes_disagree: number;
  votes_uncertain: number;
  status: CaseStatus;
  sar_report: string | null;
  xai_summary: string | null;
  evidence: EvidenceJson | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// EvidencePacket (evidence_packets table)
// ---------------------------------------------------------------------------

export interface EvidencePacket {
  case_id: string;
  event_id: string | null;
  market_id: string;
  market_name: string | null;
  market_slug: string | null;
  wallet_address: string;
  trade_timestamp: string;
  side: string | null;
  outcome: string | null;
  trade_size: number | null;
  trade_price: number | null;
  wallet_age_hours: number | null;
  wallet_trade_count: number | null;
  wallet_win_rate: number | null;
  wallet_risk_score: number | null;
  is_fresh_wallet: number;
  cluster_id: string | null;
  cluster_size: number;
  cluster_confidence: number | null;
  osint_event_id: string | null;
  osint_source: string | null;
  osint_title: string | null;
  osint_timestamp: string | null;
  temporal_gap_minutes: number | null;
  temporal_gap_score: number | null;
  correlation_score: number | null;
  evidence: Record<string, unknown> | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Votes
// ---------------------------------------------------------------------------

export interface Vote {
  vote_id: string;
  case_id: string;
  voter_id: string | null;
  vote: VoteValue;
  confidence: number | null;
  comment: string | null;
  created_at: string;
}

export interface VoteRequest {
  case_id: string;
  vote: VoteValue;
  voter_id?: string;
  confidence?: number;
  comment?: string;
}

// ---------------------------------------------------------------------------
// Paginated wrapper
// ---------------------------------------------------------------------------

export interface PaginatedResponse<T> {
  count: number;
  total: number;
  limit: number;
  offset: number;
  items: T[];
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: 'ok' | 'degraded';
  timestamp: string;
  database: {
    status: string;
    path: string;
  };
  stats: {
    total_anomalies: number;
    total_osint_events: number;
    total_wallets: number;
    total_cases: number;
    total_evidence_packets: number;
    cases_by_classification: Record<string, number>;
    cases_by_status: Record<string, number>;
  };
}

// ---------------------------------------------------------------------------
// Case detail
// ---------------------------------------------------------------------------

export interface CaseDetailResponse {
  case: SentinelCase;
  anomaly: Anomaly | null;
  evidence_packet: EvidencePacket | null;
  votes: Vote[];
  vote_count: number;
}

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------

export interface MetricsResponse {
  status: string;
  timestamp: string;
  evaluation: {
    coverage: {
      total_cases: number;
      evaluated_cases: number;
      min_votes: number;
    };
    arena_consensus: {
      consensus_accuracy: number | null;
      confirmed_cases: number;
      disputed_cases: number;
    };
    metrics: {
      fpr: number | null;
      fnr: number | null;
      accuracy: number | null;
    };
    binary_confusion_matrix: {
      counts: {
        tp: number;
        fp: number;
        tn: number;
        fn: number;
      };
    };
  };
}
