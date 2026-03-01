"""
DBSCAN Sniper Clustering & Composite Risk Scoring
Adapted from polymarket-insider-tracker (MIT License)

Provides:
- DBSCAN clustering for detecting coordinated wallet behavior
- Sniper detection (wallets that enter markets within minutes of creation)
- Composite risk scoring with weighted signal aggregation
"""
import hashlib
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Set
from decimal import Decimal

logger = logging.getLogger(__name__)

# Try to import sklearn, fall back to simple clustering if not available
try:
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    np = None  # type: ignore
    logger.warning("sklearn not available - using simplified clustering")


# Risk scoring weights (from polymarket-insider-tracker)
# Updated to match original: fresh_wallet: 0.40, size_anomaly: 0.35, niche_market: 0.25
DEFAULT_WEIGHTS = {
    "fresh_wallet": 0.40,
    "size_anomaly": 0.35,
    "niche_market": 0.25,
}

# Multi-signal bonuses (from polymarket-insider-tracker)
MULTI_SIGNAL_BONUS_2 = 1.2  # 20% bonus for 2 signals
MULTI_SIGNAL_BONUS_3 = 1.3  # 30% bonus for 3+ signals

# Sniper detection parameters
DEFAULT_ENTRY_THRESHOLD_SECONDS = 300  # 5 minutes - max time after market creation
DEFAULT_MIN_CLUSTER_SIZE = 3
DEFAULT_MIN_ENTRIES_PER_WALLET = 2

# DBSCAN parameters
DBSCAN_EPS = 0.5  # Maximum distance between samples
DBSCAN_MIN_SAMPLES = 2  # Minimum samples for core point


@dataclass
class ClusterMembership:
    """Cluster membership info for a wallet."""
    wallet_address: str
    cluster_id: int
    cluster_size: int
    is_core_member: bool
    centroid_distance: float


@dataclass
class SniperSignal:
    """Signal indicating potential sniper behavior."""
    wallet_address: str
    market_id: str
    trade_timestamp: datetime
    event_timestamp: Optional[datetime] = None
    time_delta_seconds: Optional[float] = None
    cluster_id: Optional[str] = None
    cluster_size: int = 0
    confidence: float = 0.0


@dataclass
class RiskAssessment:
    """Composite risk assessment for a wallet/trade."""
    overall_score: float  # 0-100
    component_scores: Dict[str, float] = field(default_factory=dict)
    risk_level: str = "low"  # low, medium, high, critical
    flags: List[str] = field(default_factory=list)
    explanation: str = ""


class ClusterAnalyzer:
    """
    DBSCAN clustering for detecting coordinated wallet behavior.

    Wallets are clustered based on:
    - Temporal proximity of trades (trading at similar times)
    - Market overlap (trading the same markets)
    - Volume patterns (similar trade sizes)
    - Funding source similarity
    """

    def __init__(self, eps: float = DBSCAN_EPS, min_samples: int = DBSCAN_MIN_SAMPLES):
        self.eps = eps
        self.min_samples = min_samples
        self._clusters: Dict[int, List[str]] = {}
        self._wallet_features: Dict[str, List[float]] = {}

    def extract_features(
        self,
        wallet_address: str,
        trades: List[Dict[str, Any]],
        markets_traded: List[str],
        funding_source: Optional[str] = None,
    ) -> List[float]:
        """
        Extract feature vector for a wallet.

        Features:
        - avg_trade_time_of_day (0-24)
        - trade_count
        - avg_trade_size
        - market_diversity (unique markets / total trades)
        - funding_source_hash (numeric)

        Returns:
            Feature vector
        """
        if not trades:
            return [12.0, 0, 0, 0, 0]

        # Average trade time of day
        trade_hours = [t.get("timestamp", datetime.now()).hour for t in trades if "timestamp" in t]
        avg_hour = sum(trade_hours) / len(trade_hours) if trade_hours else 12

        # Trade count
        trade_count = len(trades)

        # Average trade size
        sizes = [float(t.get("size", 0)) for t in trades]
        avg_size = sum(sizes) / len(sizes) if sizes else 0

        # Market diversity
        unique_markets = len(set(markets_traded))
        diversity = unique_markets / trade_count if trade_count > 0 else 0

        # Funding source hash (simple numeric representation)
        funding_hash = hash(funding_source or "unknown") % 100 if funding_source else 50

        features = [avg_hour, trade_count, avg_size / 10000, diversity, funding_hash / 100]

        self._wallet_features[wallet_address] = features
        return features

    def run_clustering(self, wallet_features: Dict[str, List[float]]) -> Dict[int, List[str]]:
        """
        Run DBSCAN clustering on wallet features.

        Args:
            wallet_features: Dict mapping wallet address to feature vector

        Returns:
            Dict mapping cluster_id to list of wallet addresses
        """
        if not wallet_features:
            return {}

        addresses = list(wallet_features.keys())
        features = list(wallet_features.values())

        if SKLEARN_AVAILABLE and len(features) >= self.min_samples:
            return self._sklearn_clustering(addresses, features)
        else:
            return self._simple_clustering(addresses, features)

    def _sklearn_clustering(
        self,
        addresses: List[str],
        features: List[List[float]]
    ) -> Dict[int, List[str]]:
        """Full DBSCAN clustering using sklearn."""
        X = np.array(features)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        dbscan = DBSCAN(eps=self.eps, min_samples=self.min_samples)
        labels = dbscan.fit_predict(X_scaled)

        clusters: Dict[int, List[str]] = {}
        for addr, label in zip(addresses, labels):
            if label == -1:  # Noise point
                continue
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(addr)

        self._clusters = clusters
        logger.info("DBSCAN found %d clusters from %d wallets", len(clusters), len(addresses))
        return clusters

    def _simple_clustering(
        self,
        addresses: List[str],
        features: List[List[float]]
    ) -> Dict[int, List[str]]:
        """Simplified clustering without sklearn."""
        # Group by similar trade times (simple heuristic)
        clusters: Dict[int, List[str]] = {}
        time_buckets: Dict[int, List[str]] = {}

        for addr, feat in zip(addresses, features):
            hour_bucket = int(feat[0] / 4)  # 6 buckets of 4 hours each
            if hour_bucket not in time_buckets:
                time_buckets[hour_bucket] = []
            time_buckets[hour_bucket].append(addr)

        cluster_id = 0
        for bucket, wallets in time_buckets.items():
            if len(wallets) >= self.min_samples:
                clusters[cluster_id] = wallets
                cluster_id += 1

        self._clusters = clusters
        return clusters

    def get_cluster_for_wallet(self, wallet_address: str) -> Optional[ClusterMembership]:
        """Get cluster membership info for a wallet."""
        for cluster_id, members in self._clusters.items():
            if wallet_address in members:
                return ClusterMembership(
                    wallet_address=wallet_address,
                    cluster_id=cluster_id,
                    cluster_size=len(members),
                    is_core_member=True,  # Simplified
                    centroid_distance=0.0,  # Would need to calculate
                )
        return None

    def get_suspicious_clusters(self, min_size: int = 3) -> List[Dict[str, Any]]:
        """
        Get clusters that appear suspicious.

        Criteria:
        - Size >= min_size
        - Members trade similar markets
        - Members trade at similar times
        """
        suspicious = []
        for cluster_id, members in self._clusters.items():
            if len(members) >= min_size:
                suspicious.append({
                    "cluster_id": cluster_id,
                    "size": len(members),
                    "members": members,
                    "suspicion_score": min(len(members) / 10, 1.0),
                })
        return suspicious


@dataclass
class MarketEntry:
    """
    Record of a wallet's entry into a market.
    Adapted from polymarket-insider-tracker.
    """
    wallet_address: str
    market_id: str
    entry_delta_seconds: float  # Time between market creation and entry
    position_size: Decimal
    timestamp: datetime


@dataclass
class ClusterInfo:
    """Information about a detected sniper cluster."""
    cluster_id: str
    wallet_addresses: Set[str]
    avg_entry_delta: float
    markets_in_common: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SniperDetector:
    """
    Detects sniper clusters using DBSCAN clustering algorithm.
    Adapted from polymarket-insider-tracker (MIT License).

    The detector tracks wallet entries across markets and periodically
    runs DBSCAN clustering to identify groups of wallets with similar
    timing patterns (consistently entering markets early after creation).

    A sniper typically:
    - Enters markets within minutes of their creation
    - Shows coordinated behavior with other wallets
    - Makes large, confident bets
    """

    def __init__(
        self,
        *,
        entry_threshold_seconds: int = DEFAULT_ENTRY_THRESHOLD_SECONDS,
        min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE,
        eps: float = DBSCAN_EPS,
        min_samples: int = DBSCAN_MIN_SAMPLES,
        min_entries_per_wallet: int = DEFAULT_MIN_ENTRIES_PER_WALLET,
    ) -> None:
        """
        Initialize the sniper detector.

        Args:
            entry_threshold_seconds: Max seconds after market creation to track (default 300).
            min_cluster_size: Minimum wallets to form a cluster (default 3).
            eps: DBSCAN epsilon (default 0.5).
            min_samples: DBSCAN min samples (default 2).
            min_entries_per_wallet: Minimum entries to include wallet (default 2).
        """
        self.entry_threshold_seconds = entry_threshold_seconds
        self.min_cluster_size = min_cluster_size
        self.eps = eps
        self.min_samples = min_samples
        self.min_entries_per_wallet = min_entries_per_wallet

        # Entry tracking
        self._entries: List[MarketEntry] = []
        self._wallet_entries: Dict[str, List[MarketEntry]] = defaultdict(list)
        self._market_wallets: Dict[str, Set[str]] = defaultdict(set)

        # Cluster tracking
        self._known_clusters: Dict[str, ClusterInfo] = {}
        self._wallet_cluster_map: Dict[str, str] = {}

        # Previously signaled wallets (to avoid duplicate signals)
        self._signaled_wallets: Set[str] = set()

    def record_entry(
        self,
        wallet_address: str,
        market_id: str,
        entry_timestamp: datetime,
        market_created_at: datetime,
        position_size: Decimal,
    ) -> None:
        """
        Record a market entry for clustering analysis.

        Only records entries that occur within the threshold time after
        market creation (potential sniper behavior).

        Args:
            wallet_address: Wallet that entered the market.
            market_id: Market condition ID.
            entry_timestamp: When the trade occurred.
            market_created_at: When the market was created.
            position_size: Size of the position in USD.
        """
        # Calculate entry delta
        delta = (entry_timestamp - market_created_at).total_seconds()

        # Only track entries within threshold (potential snipers)
        if delta < 0 or delta > self.entry_threshold_seconds:
            return

        entry = MarketEntry(
            wallet_address=wallet_address.lower(),
            market_id=market_id,
            entry_delta_seconds=delta,
            position_size=position_size,
            timestamp=entry_timestamp,
        )

        self._entries.append(entry)
        self._wallet_entries[entry.wallet_address].append(entry)
        self._market_wallets[entry.market_id].add(entry.wallet_address)

        logger.debug(
            "Recorded sniper entry: wallet=%s market=%s delta=%.1fs",
            entry.wallet_address[:10],
            entry.market_id[:10] if len(entry.market_id) > 10 else entry.market_id,
            delta,
        )

    def run_clustering(self) -> List[SniperSignal]:
        """
        Run DBSCAN clustering and return new sniper signals.

        Returns:
            List of SniperSignal for newly detected cluster members.
        """
        # Filter wallets with enough entries
        eligible_wallets = [
            wallet
            for wallet, entries in self._wallet_entries.items()
            if len(entries) >= self.min_entries_per_wallet
        ]

        if len(eligible_wallets) < self.min_cluster_size:
            logger.debug(
                "Not enough eligible wallets for clustering: %d < %d",
                len(eligible_wallets),
                self.min_cluster_size,
            )
            return []

        if not SKLEARN_AVAILABLE:
            return self._simple_clustering(eligible_wallets)

        # Build feature matrix
        feature_vectors, wallet_index = self._build_feature_matrix(eligible_wallets)
        if len(feature_vectors) == 0:
            return []

        return self._sklearn_clustering(feature_vectors, wallet_index)

    def _build_feature_matrix(
        self,
        wallets: List[str],
    ) -> tuple:
        """
        Build feature matrix for DBSCAN clustering.

        Features per entry (from polymarket-insider-tracker):
        - Normalized market hash (0-1 range)
        - Normalized entry delta (in hours)
        - Log-normalized position size
        """
        if not SKLEARN_AVAILABLE:
            return [], {}

        features = []
        wallet_index: Dict[int, str] = {}
        row_idx = 0

        for wallet in wallets:
            entries = self._wallet_entries[wallet]
            for entry in entries:
                # Normalize market ID to 0-1 range
                market_hash = (
                    int(hashlib.md5(entry.market_id.encode()).hexdigest()[:8], 16) % 1000
                ) / 1000.0

                # Normalize entry delta to hours (0-5 mins = 0-0.083 hours)
                delta_hours = entry.entry_delta_seconds / 3600.0

                # Log-normalize position size
                log_size = float(np.log10(max(float(entry.position_size), 1.0)))

                features.append([market_hash, delta_hours, log_size])
                wallet_index[row_idx] = wallet
                row_idx += 1

        return np.array(features) if features else np.array([]), wallet_index

    def _sklearn_clustering(
        self,
        features: Any,  # np.ndarray when sklearn available
        wallet_index: Dict[int, str],
    ) -> List[SniperSignal]:
        """Full DBSCAN clustering using sklearn."""
        clustering = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric="euclidean",
        ).fit(features)

        # Group rows by cluster
        cluster_rows: Dict[int, List[int]] = defaultdict(list)
        for row_idx, label in enumerate(clustering.labels_):
            if label != -1:  # Skip noise
                cluster_rows[label].append(row_idx)

        signals: List[SniperSignal] = []

        for cluster_label, rows in cluster_rows.items():
            # Get unique wallets in this cluster
            cluster_wallets = {wallet_index[row] for row in rows}

            if len(cluster_wallets) < self.min_cluster_size:
                continue

            # Calculate cluster statistics
            cluster_stats = self._calculate_cluster_stats(cluster_wallets)

            # Generate or reuse cluster ID
            cluster_id = self._get_or_create_cluster_id(cluster_wallets)

            # Update cluster info
            self._known_clusters[cluster_id] = ClusterInfo(
                cluster_id=cluster_id,
                wallet_addresses=cluster_wallets,
                avg_entry_delta=cluster_stats["avg_delta"],
                markets_in_common=int(cluster_stats["markets_in_common"]),
            )

            # Update wallet-cluster mapping and generate signals
            for wallet in cluster_wallets:
                self._wallet_cluster_map[wallet] = cluster_id

                if wallet not in self._signaled_wallets:
                    confidence = self._calculate_confidence(cluster_wallets, cluster_stats)

                    signal = SniperSignal(
                        wallet_address=wallet,
                        market_id=cluster_id,  # Use cluster_id as identifier
                        trade_timestamp=datetime.now(timezone.utc),
                        cluster_id=cluster_id,
                        cluster_size=len(cluster_wallets),
                        confidence=confidence,
                    )

                    signals.append(signal)
                    self._signaled_wallets.add(wallet)

                    logger.info(
                        "New sniper detected: wallet=%s cluster=%s confidence=%.2f",
                        wallet[:10],
                        cluster_id[:8],
                        confidence,
                    )

        return signals

    def _simple_clustering(self, wallets: List[str]) -> List[SniperSignal]:
        """Simplified clustering without sklearn."""
        # Group wallets by similar entry timing (simple heuristic)
        timing_buckets: Dict[int, List[str]] = defaultdict(list)

        for wallet in wallets:
            entries = self._wallet_entries[wallet]
            avg_delta = sum(e.entry_delta_seconds for e in entries) / len(entries)
            bucket = int(avg_delta / 60)  # Bucket by minute
            timing_buckets[bucket].append(wallet)

        signals: List[SniperSignal] = []
        for bucket, cluster_wallets in timing_buckets.items():
            if len(cluster_wallets) >= self.min_cluster_size:
                cluster_id = str(uuid.uuid4())
                for wallet in cluster_wallets:
                    if wallet not in self._signaled_wallets:
                        signal = SniperSignal(
                            wallet_address=wallet,
                            market_id=cluster_id,
                            trade_timestamp=datetime.now(timezone.utc),
                            cluster_id=cluster_id,
                            cluster_size=len(cluster_wallets),
                            confidence=0.5,
                        )
                        signals.append(signal)
                        self._signaled_wallets.add(wallet)

        return signals

    def _calculate_cluster_stats(self, cluster_wallets: Set[str]) -> Dict[str, float]:
        """Calculate statistics for a cluster of wallets."""
        all_deltas: List[float] = []
        for wallet in cluster_wallets:
            for entry in self._wallet_entries[wallet]:
                all_deltas.append(entry.entry_delta_seconds)

        avg_delta = sum(all_deltas) / len(all_deltas) if all_deltas else 0.0

        # Calculate markets in common
        wallet_markets: List[Set[str]] = []
        for wallet in cluster_wallets:
            markets = {e.market_id for e in self._wallet_entries[wallet]}
            wallet_markets.append(markets)

        if len(wallet_markets) >= 2:
            common_markets = set.intersection(*wallet_markets)
            markets_in_common = len(common_markets)
        else:
            markets_in_common = 0

        return {
            "avg_delta": avg_delta,
            "markets_in_common": markets_in_common,
        }

    def _get_or_create_cluster_id(self, wallets: Set[str]) -> str:
        """Get existing cluster ID or create new one."""
        existing_clusters: Dict[str, int] = defaultdict(int)
        for wallet in wallets:
            if wallet in self._wallet_cluster_map:
                existing_clusters[self._wallet_cluster_map[wallet]] += 1

        if existing_clusters:
            best_cluster = max(existing_clusters, key=lambda k: existing_clusters[k])
            if existing_clusters[best_cluster] >= len(wallets) // 2:
                return best_cluster

        return str(uuid.uuid4())

    def _calculate_confidence(
        self,
        cluster_wallets: Set[str],
        stats: Dict[str, float],
    ) -> float:
        """
        Calculate confidence score for a cluster.
        Higher confidence when: larger cluster, faster entries, more markets in common.
        """
        # Size factor: more wallets = higher confidence
        size_factor = min(1.0, len(cluster_wallets) / 10.0)

        # Speed factor: faster entries = higher confidence
        avg_delta = float(stats["avg_delta"])
        speed_factor = max(0.0, 1.0 - (avg_delta / self.entry_threshold_seconds))

        # Overlap factor: more markets in common = higher confidence
        markets_common = int(stats["markets_in_common"])
        overlap_factor = min(1.0, markets_common / 5.0)

        # Weighted combination (from polymarket-insider-tracker)
        confidence = 0.3 * size_factor + 0.4 * speed_factor + 0.3 * overlap_factor

        return round(min(1.0, confidence), 3)

    def is_sniper(self, wallet_address: str) -> bool:
        """Check if a wallet is in any known sniper cluster."""
        return wallet_address.lower() in self._wallet_cluster_map

    def get_cluster_for_wallet(self, wallet_address: str) -> Optional[ClusterInfo]:
        """Get cluster info for a wallet if it belongs to one."""
        cluster_id = self._wallet_cluster_map.get(wallet_address.lower())
        if cluster_id:
            return self._known_clusters.get(cluster_id)
        return None

    def get_entry_count(self) -> int:
        """Return the total number of tracked entries."""
        return len(self._entries)

    def get_wallet_count(self) -> int:
        """Return the number of unique wallets tracked."""
        return len(self._wallet_entries)

    def get_cluster_count(self) -> int:
        """Return the number of detected clusters."""
        return len(self._known_clusters)

    def clear_entries(self) -> None:
        """Clear all tracked entries (for periodic cleanup)."""
        self._entries.clear()
        self._wallet_entries.clear()
        self._market_wallets.clear()
        logger.info("Cleared all sniper detector entries")


class CompositeRiskScorer:
    """
    Calculates composite risk scores using weighted signal aggregation.

    Adapted from polymarket-insider-tracker (MIT License).

    Scoring Formula:
        weighted_score = sum(signal.confidence * weight[type] for signal in signals)

        # Multi-signal bonus
        if signals >= 2: weighted_score *= 1.2
        if signals >= 3: weighted_score *= 1.3

        # Cap at 1.0
        final_score = min(weighted_score, 1.0)
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        alert_threshold: float = 0.6,
    ):
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.alert_threshold = alert_threshold

    def calculate(
        self,
        signals: Dict[str, float],
    ) -> RiskAssessment:
        """
        Calculate composite risk score from individual signals.

        Args:
            signals: Dict mapping signal name to confidence score (0-1)
                e.g., {"fresh_wallet": 0.8, "size_anomaly": 0.6, ...}

        Returns:
            RiskAssessment with overall score and breakdown
        """
        score = 0.0
        signals_triggered = 0
        component_scores = {}
        flags = []

        for signal_name, signal_confidence in signals.items():
            weight = self.weights.get(signal_name, 0.1)  # Default weight
            contribution = signal_confidence * weight
            score += contribution
            signals_triggered += 1

            component_scores[signal_name] = round(signal_confidence * 100, 1)

            # Flag high-scoring components
            if signal_confidence >= 0.7:
                flags.append(f"high_{signal_name}")

        # Apply multi-signal bonus (from polymarket-insider-tracker)
        if signals_triggered >= 3:
            score *= MULTI_SIGNAL_BONUS_3
        elif signals_triggered >= 2:
            score *= MULTI_SIGNAL_BONUS_2

        # Cap at 1.0 and convert to 0-100 scale
        score = min(score, 1.0)
        overall_score = score * 100

        # Determine risk level based on threshold
        if score >= 0.8:
            risk_level = "critical"
        elif score >= self.alert_threshold:
            risk_level = "high"
        elif score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Generate explanation
        top_contributors = sorted(
            component_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        explanation_parts = [f"{name}: {score:.0f}%" for name, score in top_contributors]
        explanation = f"Top risk factors: {', '.join(explanation_parts)}"

        if signals_triggered >= 2:
            explanation += f" (multi-signal bonus applied: {signals_triggered} signals)"

        return RiskAssessment(
            overall_score=round(overall_score, 1),
            component_scores=component_scores,
            risk_level=risk_level,
            flags=flags,
            explanation=explanation,
        )


def aggregate_wallet_risk(
    wallet_profile: Dict[str, Any],
    trade_signals: Dict[str, float],
    cluster_analyzer: Optional[ClusterAnalyzer] = None,
) -> RiskAssessment:
    """
    Convenience function to aggregate all risk signals for a wallet.

    Args:
        wallet_profile: Wallet profile data
        trade_signals: Signals from current trade analysis
        cluster_analyzer: Optional cluster analyzer for cluster membership

    Returns:
        RiskAssessment
    """
    signals = dict(trade_signals)

    # Add wallet-level signals
    if wallet_profile.get("nonce", 10) <= 5:
        signals["fresh_wallet"] = 0.8
    if wallet_profile.get("win_rate", 0.5) > 0.85:
        signals["high_win_rate"] = min(wallet_profile.get("win_rate", 0.5), 0.95)

    # Add funding risk
    funding_risk = wallet_profile.get("funding_risk", 0.0)
    if funding_risk > 0:
        signals["funding_risk"] = funding_risk

    # Add cluster membership
    if cluster_analyzer:
        address = wallet_profile.get("address", "")
        membership = cluster_analyzer.get_cluster_for_wallet(address)
        if membership and membership.cluster_size >= 3:
            signals["cluster_member"] = min(membership.cluster_size / 10, 0.9)

    scorer = CompositeRiskScorer()
    return scorer.calculate(signals)


if __name__ == "__main__":
    print("Testing Cluster Analysis & Risk Scoring...")

    # Test cluster analyzer
    print("\n📊 Cluster Analyzer:")
    analyzer = ClusterAnalyzer()

    # Create mock wallet features
    wallet_features = {
        "0xaaa": [10.0, 5, 0.5, 0.3, 0.5],
        "0xbbb": [10.5, 6, 0.6, 0.3, 0.5],  # Similar to 0xaaa
        "0xccc": [11.0, 4, 0.4, 0.4, 0.5],  # Similar to 0xaaa
        "0xddd": [22.0, 10, 2.0, 0.8, 0.2],  # Different
        "0xeee": [23.0, 8, 1.8, 0.7, 0.2],  # Similar to 0xddd
    }

    clusters = analyzer.run_clustering(wallet_features)
    print(f"  Found {len(clusters)} clusters")
    for cid, members in clusters.items():
        print(f"    Cluster {cid}: {members}")

    # Test sniper detector
    print("\n🎯 Sniper Detector:")
    detector = SniperDetector()
    market_created = datetime.now(timezone.utc) - timedelta(minutes=2)

    # Seed entries for three wallets to create an eligible cluster.
    for wallet, offsets in {
        "0xaaa": [20, 30],
        "0xbbb": [25, 35],
        "0xccc": [22, 28],
    }.items():
        for offset in offsets:
            detector.record_entry(
                wallet_address=wallet,
                market_id=f"market-{offset}",
                entry_timestamp=market_created + timedelta(seconds=offset),
                market_created_at=market_created,
                position_size=Decimal("1000"),
            )

    sniper_signals = detector.run_clustering()
    print(f"  Signals detected: {len(sniper_signals)}")
    for sig in sniper_signals:
        print(f"    wallet={sig.wallet_address[:8]} cluster={sig.cluster_id[:8]} conf={sig.confidence:.2f}")

    # Test composite risk scorer
    print("\n📈 Composite Risk Scorer:")
    signals = {
        "fresh_wallet": 0.8,
        "volume_spike": 0.6,
        "high_win_rate": 0.9,
        "cluster_member": 0.3,
    }

    scorer = CompositeRiskScorer()
    assessment = scorer.calculate(signals)
    print(f"  Overall score: {assessment.overall_score}")
    print(f"  Risk level: {assessment.risk_level}")
    print(f"  Flags: {assessment.flags}")
    print(f"  Explanation: {assessment.explanation}")
