"""
Feature Extraction Module

Produces standardised feature vectors from raw anomaly data, wallet profiles,
cluster analysis, and OSINT correlation for the classification pipeline.

Feature set (from PRD Section 2.1):
    - wallet_age_days       : Wallet age in days
    - wallet_trade_count    : Number of prior trades
    - wallet_win_rate       : Win rate [0-1]
    - position_size_pct     : Trade size as % of market 24h volume
    - hours_before_news     : Temporal gap (negative = before, positive = after)
    - z_score               : Statistical anomaly score of volume spike
    - cluster_member        : Whether wallet belongs to a DBSCAN cluster (bool → 0/1)
    - osint_signal_count    : Number of OSINT signals available before the trade
    - is_fresh_wallet       : Wallet < 7 days old and < 5 trades (bool → 0/1)
    - funding_risk          : Funding chain risk (mixer/bridge = 1, clean = 0)

Usage:
    extractor = FeatureExtractor()
    vec = extractor.extract(anomaly_dict)
    # vec.to_dict()   → dict for classifier prompt
    # vec.to_array()  → numpy array for ML models
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

FRESH_WALLET_AGE_DAYS = 7
FRESH_WALLET_MAX_TRADES = 5


@dataclass
class FeatureVector:
    """Standardised feature vector for classification."""

    # Wallet features
    wallet_age_days: float = 30.0
    wallet_trade_count: int = 10
    wallet_win_rate: float = 0.5
    is_fresh_wallet: int = 0          # 0 or 1
    funding_risk: int = 0             # 0 = clean, 1 = risky

    # Trade features
    trade_size_usd: float = 0.0
    position_size_pct: float = 0.0    # trade as % of 24h market volume
    z_score: float = 0.0

    # Timing / OSINT features
    hours_before_news: Optional[float] = None
    osint_signal_count: int = 0
    information_asymmetry: str = "UNKNOWN"

    # Cluster features
    cluster_member: int = 0           # 0 or 1
    cluster_id: Optional[int] = None
    is_sniper: int = 0                # 0 or 1

    # Risk composite (from CompositeRiskScorer)
    composite_risk_score: float = 0.0

    # Human-readable provenance for XAI
    feature_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return dict suitable for classifier prompt input."""
        d = asdict(self)
        # Drop notes and internal-only fields for the prompt
        d.pop("feature_notes", None)
        d.pop("cluster_id", None)
        return d

    def to_classifier_input(self) -> Dict[str, Any]:
        """Return the subset of features the Stage 1 classifier expects."""
        return {
            "wallet_age_days": self.wallet_age_days,
            "wallet_trades": self.wallet_trade_count,
            "trade_size_usd": self.trade_size_usd,
            "hours_before_news": self.hours_before_news,
            "osint_signals_before_trade": self.osint_signal_count,
            "z_score": self.z_score,
            # Extended features (used by fine-tuned model)
            "wallet_win_rate": self.wallet_win_rate,
            "position_size_pct": self.position_size_pct,
            "is_fresh_wallet": self.is_fresh_wallet,
            "cluster_member": self.cluster_member,
            "funding_risk": self.funding_risk,
        }

    def to_array(self) -> list:
        """Return a numeric array for ML models (fixed-order features)."""
        return [
            self.wallet_age_days,
            float(self.wallet_trade_count),
            self.wallet_win_rate,
            float(self.is_fresh_wallet),
            float(self.funding_risk),
            self.trade_size_usd,
            self.position_size_pct,
            self.z_score,
            self.hours_before_news if self.hours_before_news is not None else 0.0,
            float(self.osint_signal_count),
            float(self.cluster_member),
            float(self.is_sniper),
            self.composite_risk_score,
        ]

    @staticmethod
    def feature_names() -> List[str]:
        """Feature names matching to_array() order."""
        return [
            "wallet_age_days",
            "wallet_trade_count",
            "wallet_win_rate",
            "is_fresh_wallet",
            "funding_risk",
            "trade_size_usd",
            "position_size_pct",
            "z_score",
            "hours_before_news",
            "osint_signal_count",
            "cluster_member",
            "is_sniper",
            "composite_risk_score",
        ]

    @property
    def suspicion_heuristic(self) -> float:
        """
        Quick heuristic suspicion score [0-100] for sorting/prioritisation.

        Not used for classification — just for ranking anomalies before
        sending them through the AI pipeline.
        """
        score = 0.0

        # Fresh wallet is suspicious
        if self.is_fresh_wallet:
            score += 25

        # Trade before news is suspicious
        if self.hours_before_news is not None and self.hours_before_news < -2:
            score += min(30, abs(self.hours_before_news) * 3)

        # No OSINT signals = less explainable
        if self.osint_signal_count == 0:
            score += 15

        # High z-score
        if self.z_score > 3:
            score += 15
        elif self.z_score > 2:
            score += 8

        # Cluster/sniper membership
        if self.is_sniper:
            score += 10
        elif self.cluster_member:
            score += 5

        # Funding risk
        if self.funding_risk:
            score += 10

        # Large position relative to market
        if self.position_size_pct > 10:
            score += 10
        elif self.position_size_pct > 5:
            score += 5

        return min(100, score)


class FeatureExtractor:
    """
    Extracts standardised feature vectors from heterogeneous anomaly data.

    Handles data from multiple sources:
      - Raw anomaly dicts (from detection or mock data)
      - WalletProfile objects (from wallet_profiler.py)
      - Cluster analysis results (from cluster_analysis.py)
      - OSINT correlation results (from correlator.py)
    """

    def extract(self, anomaly: Dict[str, Any]) -> FeatureVector:
        """
        Extract a feature vector from an anomaly dict.

        The anomaly dict may contain raw fields or enriched fields
        from the correlator / profiler. This method normalises both.
        """
        vec = FeatureVector()
        notes: List[str] = []

        # ----------------------------------------------------------
        # Wallet features
        # ----------------------------------------------------------
        vec.wallet_age_days = float(anomaly.get("wallet_age_days", 30))
        vec.wallet_trade_count = int(anomaly.get("wallet_trades", anomaly.get("wallet_trade_count", 10)))
        vec.wallet_win_rate = float(anomaly.get("win_rate", anomaly.get("wallet_win_rate", 0.5)))

        vec.is_fresh_wallet = int(
            vec.wallet_age_days < FRESH_WALLET_AGE_DAYS
            and vec.wallet_trade_count < FRESH_WALLET_MAX_TRADES
        )
        if vec.is_fresh_wallet:
            notes.append(f"Fresh wallet: {vec.wallet_age_days:.0f} days, {vec.wallet_trade_count} trades")

        # Funding risk
        risk_flags = anomaly.get("risk_flags", [])
        funding = anomaly.get("funding_chain", {})
        if isinstance(funding, dict):
            source_type = funding.get("source_type", "")
            if source_type in ("mixer", "tornado_cash"):
                vec.funding_risk = 1
                notes.append(f"Risky funding source: {source_type}")
        if "mixer_funded" in risk_flags:
            vec.funding_risk = 1
            notes.append("Mixer-funded wallet")

        # ----------------------------------------------------------
        # Trade features
        # ----------------------------------------------------------
        vec.trade_size_usd = float(anomaly.get("trade_size", anomaly.get("trade_size_usd", 0)))
        vec.z_score = float(anomaly.get("z_score", 0))

        # Position size as % of market volume
        market_volume = float(anomaly.get("market_volume_24h", 0) or 0)
        if market_volume > 0 and vec.trade_size_usd > 0:
            vec.position_size_pct = (vec.trade_size_usd / market_volume) * 100
            if vec.position_size_pct > 5:
                notes.append(f"Large position: {vec.position_size_pct:.1f}% of 24h volume")
        else:
            vec.position_size_pct = 0.0

        # ----------------------------------------------------------
        # Timing / OSINT features
        # ----------------------------------------------------------
        hbn = anomaly.get("hours_before_news")
        if hbn is not None:
            try:
                vec.hours_before_news = float(hbn)
            except (TypeError, ValueError):
                vec.hours_before_news = None

        vec.osint_signal_count = int(anomaly.get(
            "osint_signals_before_trade",
            anomaly.get("osint_signal_count", 0),
        ))

        vec.information_asymmetry = anomaly.get("information_asymmetry", "UNKNOWN")

        if vec.hours_before_news is not None and vec.hours_before_news < -2 and vec.osint_signal_count == 0:
            notes.append(
                f"Trade {abs(vec.hours_before_news):.1f}h before news with NO public signals"
            )

        # ----------------------------------------------------------
        # Cluster features
        # ----------------------------------------------------------
        vec.cluster_member = int(anomaly.get("cluster_member", anomaly.get("cluster_id") is not None))
        vec.cluster_id = anomaly.get("cluster_id")
        vec.is_sniper = int(anomaly.get("is_sniper", 0))
        vec.composite_risk_score = float(anomaly.get("composite_risk_score", anomaly.get("risk_score", 0)))

        if vec.is_sniper:
            notes.append("Sniper cluster member (coordinated trading detected)")
        elif vec.cluster_member:
            notes.append(f"Cluster member (cluster_id={vec.cluster_id})")

        vec.feature_notes = notes
        return vec

    def extract_batch(self, anomalies: List[Dict[str, Any]]) -> List[FeatureVector]:
        """Extract feature vectors for a batch of anomalies."""
        return [self.extract(a) for a in anomalies]

    def enrich_anomaly(self, anomaly: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract features and merge them back into the anomaly dict.

        This is the primary integration point — call this before sending
        an anomaly through the classification pipeline.
        """
        vec = self.extract(anomaly)
        enriched = dict(anomaly)
        enriched.update(vec.to_classifier_input())
        enriched["feature_vector"] = vec.to_dict()
        enriched["feature_notes"] = vec.feature_notes
        enriched["suspicion_heuristic"] = vec.suspicion_heuristic
        return enriched

    def enrich_batch(self, anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich a batch of anomalies with feature vectors."""
        return [self.enrich_anomaly(a) for a in anomalies]


if __name__ == "__main__":
    print("Testing Feature Extraction Module")
    print("=" * 60)

    extractor = FeatureExtractor()

    test_cases = [
        {
            "name": "Classic Insider",
            "wallet_age_days": 2,
            "wallet_trades": 1,
            "win_rate": 1.0,
            "trade_size": 50000,
            "market_volume_24h": 200000,
            "hours_before_news": -8,
            "osint_signals_before_trade": 0,
            "z_score": 4.5,
            "is_sniper": False,
            "risk_flags": ["mixer_funded"],
        },
        {
            "name": "OSINT Edge",
            "wallet_age_days": 180,
            "wallet_trades": 45,
            "win_rate": 0.68,
            "trade_size": 15000,
            "market_volume_24h": 500000,
            "hours_before_news": 6,
            "osint_signals_before_trade": 3,
            "z_score": 2.1,
            "information_asymmetry": "TRADE_AFTER_INFO",
        },
        {
            "name": "Fast Reactor",
            "wallet_age_days": 90,
            "wallet_trades": 20,
            "win_rate": 0.55,
            "trade_size": 5000,
            "market_volume_24h": 300000,
            "hours_before_news": 0.05,
            "osint_signals_before_trade": 1,
            "z_score": 1.0,
        },
        {
            "name": "Sniper Cluster",
            "wallet_age_days": 5,
            "wallet_trades": 3,
            "win_rate": 0.9,
            "trade_size": 30000,
            "market_volume_24h": 150000,
            "hours_before_news": -4,
            "osint_signals_before_trade": 0,
            "z_score": 3.8,
            "cluster_id": 2,
            "is_sniper": True,
            "composite_risk_score": 0.82,
        },
        {
            "name": "Normal Speculator",
            "wallet_age_days": 60,
            "wallet_trades": 12,
            "win_rate": 0.45,
            "trade_size": 800,
            "market_volume_24h": 1000000,
            "hours_before_news": None,
            "osint_signals_before_trade": 0,
            "z_score": 0.4,
        },
    ]

    for case in test_cases:
        name = case.pop("name")
        vec = extractor.extract(case)

        print(f"\n--- {name} ---")
        print(f"  Suspicion heuristic: {vec.suspicion_heuristic:.0f}/100")
        print(f"  Fresh wallet:  {bool(vec.is_fresh_wallet)}")
        print(f"  Position size: {vec.position_size_pct:.1f}% of market")
        print(f"  Cluster:       {'sniper' if vec.is_sniper else ('member' if vec.cluster_member else 'none')}")
        print(f"  Funding risk:  {bool(vec.funding_risk)}")
        if vec.feature_notes:
            print(f"  Notes:")
            for note in vec.feature_notes:
                print(f"    - {note}")

        # Show classifier input
        ci = vec.to_classifier_input()
        print(f"  Classifier input: {ci}")
        print(f"  Array ({len(vec.to_array())} features): {vec.to_array()}")

    # Test enrich_anomaly integration
    print("\n" + "=" * 60)
    print("Testing enrich_anomaly():")
    enriched = extractor.enrich_anomaly(test_cases[0])
    print(f"  Original keys:  {len(test_cases[0])} keys")
    print(f"  Enriched keys:  {len(enriched)} keys")
    print(f"  Added keys:     {set(enriched.keys()) - set(test_cases[0].keys())}")
    print(f"  Suspicion:      {enriched['suspicion_heuristic']:.0f}/100")
