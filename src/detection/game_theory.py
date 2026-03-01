"""
Game-theory-informed behavioral analysis for Sentinel.

Provides entropy, lightweight pattern matching, and a composite score that can
be consumed by Stage 1/2 classification and dashboard explainability.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
import math
from typing import Any, Dict, Iterable, List, Optional, Sequence

import numpy as np


class PlayerType(Enum):
    INSIDER = "insider"
    OSINT_EDGE = "osint_edge"
    FAST_REACTOR = "fast_reactor"
    SPECULATOR = "speculator"


@dataclass
class GameTheoryAnalysis:
    behavioral_deviation_score: float
    player_type_fit: Dict[str, float]
    best_fit_type: str
    composite_entropy: float
    entropy_anomaly: bool
    entropy_details: Dict[str, Any]
    matched_patterns: List[Dict[str, Any]]
    pattern_confidence: float
    network_features: Dict[str, float]
    game_theory_suspicion_score: float

    def to_classifier_context(self) -> str:
        return (
            "Game Theory Analysis:\n"
            f"  Best-fit player type: {self.best_fit_type}\n"
            f"  Behavioral deviation: {self.behavioral_deviation_score:.1f}/100\n"
            f"  Composite entropy: {self.composite_entropy:.3f} "
            f"({'ANOMALOUS' if self.entropy_anomaly else 'normal'})\n"
            f"  Pattern confidence: {self.pattern_confidence:.2f}\n"
            f"  Network correlated wallets: {self.network_features.get('correlated_wallets_count', 0):.0f}\n"
            f"  GT suspicion score: {self.game_theory_suspicion_score:.1f}/100"
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BehavioralEntropyAnalyzer:
    """Compute entropy statistics across trader behavior dimensions."""

    def compute_trading_entropy(self, trades: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        if len(trades) < 3:
            return {
                "overall_entropy": 0.0,
                "composite_entropy": 0.0,
                "insufficient_data": True,
                "anomaly_flag": False,
            }

        # Defensive timestamp parsing.
        parsed = []
        for trade in trades:
            ts = trade.get("timestamp")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    ts = None
            if isinstance(ts, datetime):
                parsed.append((trade, ts))

        hours = [ts.hour for _, ts in parsed] if parsed else [12]
        markets = [t.get("market_id", "unknown") for t, _ in parsed] if parsed else ["unknown"]
        sizes = [float(t.get("position_size_usd", t.get("trade_size", 0.0)) or 0.0) for t in trades]
        directions = [str(t.get("direction", t.get("side", "buy"))).lower() for t in trades]

        temporal_entropy = self._shannon_entropy(hours, bins=24)
        market_entropy = self._shannon_entropy(markets)
        size_entropy = self._shannon_entropy(np.histogram(sizes, bins=10)[0].tolist())
        direction_entropy = self._shannon_entropy(directions)

        entropy_values = [temporal_entropy, market_entropy, size_entropy, direction_entropy]
        composite = float(np.mean(entropy_values))
        anomaly_flag = self._is_entropy_anomalous(composite, market_entropy)

        return {
            "temporal_entropy": temporal_entropy,
            "market_entropy": market_entropy,
            "size_entropy": size_entropy,
            "direction_entropy": direction_entropy,
            "composite_entropy": composite,
            "overall_entropy": composite,
            "insufficient_data": False,
            "anomaly_flag": anomaly_flag,
        }

    @staticmethod
    def _shannon_entropy(values: Sequence[Any], bins: Optional[int] = None) -> float:
        if not values:
            return 0.0

        if bins is not None:
            counts, _ = np.histogram(values, bins=bins, range=(0, bins))
        elif all(isinstance(v, (int, float, np.integer, np.floating)) for v in values):
            counts = np.asarray(values, dtype=float)
        else:
            counts = np.array(list(Counter(values).values()), dtype=float)

        total = float(np.sum(counts))
        if total <= 0:
            return 0.0

        probs = counts / total
        probs = probs[probs > 0]
        if probs.size == 0:
            return 0.0
        return float(-np.sum(probs * np.log2(probs)))

    @staticmethod
    def _is_entropy_anomalous(composite_entropy: float, market_entropy: float) -> bool:
        # Low entropy = unusually concentrated behavior; very high entropy can
        # indicate obfuscation/noise patterns.
        return composite_entropy < 0.5 or composite_entropy > 3.8 or market_entropy < 0.1


class ACOPatternMiner:
    """Lightweight suspicious-pattern matcher inspired by ACO framing."""

    def __init__(self) -> None:
        self.discovered_patterns: List[Dict[str, Any]] = []

    def encode_trade_sequence(self, trades: Sequence[Dict[str, Any]]) -> List[str]:
        tokens: List[str] = []
        for trade in sorted(trades, key=lambda x: str(x.get("timestamp", ""))):
            size = float(trade.get("position_size_usd", trade.get("trade_size", 0.0)) or 0.0)
            size_cat = self._categorize_size(size)
            hours = trade.get("hours_before_news")
            timing_cat = self._categorize_timing(hours)
            wallet_cat = "FRESH" if trade.get("is_fresh_wallet") else "ESTAB"
            side = str(trade.get("direction", trade.get("side", "BUY"))).upper()
            tokens.append(f"{wallet_cat}_{side}_{size_cat}_{timing_cat}")
        return tokens

    def match_pattern(self, trade_sequence: Sequence[str]) -> List[Dict[str, Any]]:
        if not trade_sequence:
            return []

        seq = " ".join(trade_sequence)
        matches: List[Dict[str, Any]] = []

        # Rule-like motifs seeded from literature-inspired behavior families.
        motifs = [
            ("FRESH_BUY_WHALE", 0.82),
            ("FRESH_BUY_LARGE_MINUTES_BEFORE", 0.78),
            ("ESTAB_BUY_MEDIUM_BEFORE", 0.42),
        ]
        for motif, conf in motifs:
            if motif in seq:
                matches.append(
                    {
                        "pattern": motif.split("_"),
                        "confidence": conf,
                        "support": min(1.0, len(trade_sequence) / 10.0),
                        "lift": 1.0 + conf,
                    }
                )

        return sorted(matches, key=lambda x: x["confidence"], reverse=True)

    @staticmethod
    def _categorize_size(size_usd: float) -> str:
        if size_usd > 50000:
            return "WHALE"
        if size_usd > 10000:
            return "LARGE"
        if size_usd > 1000:
            return "MEDIUM"
        return "SMALL"

    @staticmethod
    def _categorize_timing(hours: Any) -> str:
        try:
            h = float(hours)
        except Exception:
            return "UNKNOWN"

        if h > 24:
            return "FAR_BEFORE"
        if h > 6:
            return "BEFORE"
        if h > 1:
            return "JUST_BEFORE"
        if h > 0:
            return "MINUTES_BEFORE"
        return "AFTER"


class WalletGraphAnalyzer:
    """Fallback graph feature extractor with no external graph dependency."""

    def compute_network_features(
        self,
        wallet_address: str,
        trades: Sequence[Dict[str, Any]],
    ) -> Dict[str, float]:
        if not trades:
            return self._default_features()

        same_market_wallets: Dict[str, set[str]] = defaultdict(set)
        for trade in trades:
            market = str(trade.get("market_id", ""))
            wallet = str(trade.get("wallet_address", ""))
            if market and wallet:
                same_market_wallets[market].add(wallet)

        correlated = set()
        for wallets in same_market_wallets.values():
            if wallet_address in wallets:
                correlated.update(w for w in wallets if w != wallet_address)

        component_size = 1 + len(correlated)
        return {
            "degree_centrality": min(1.0, len(correlated) / 10.0),
            "clustering_coefficient": min(1.0, len(correlated) / max(component_size, 1)),
            "component_size": float(component_size),
            "neighbor_avg_risk": 0.0,
            "neighbor_max_risk": 0.0,
            "funding_depth": 5.0,
            "correlated_wallets_count": float(len(correlated)),
        }

    @staticmethod
    def _default_features() -> Dict[str, float]:
        return {
            "degree_centrality": 0.0,
            "clustering_coefficient": 0.0,
            "component_size": 1.0,
            "neighbor_avg_risk": 0.0,
            "neighbor_max_risk": 0.0,
            "funding_depth": 10.0,
            "correlated_wallets_count": 0.0,
        }


def compute_game_theory_score(
    deviation_score: float,
    entropy_result: Dict[str, Any],
    pattern_matches: Sequence[Dict[str, Any]],
    network_features: Dict[str, float],
) -> float:
    """Weighted composite of game-theory-informed components, normalized 0-100."""
    weights = {
        "deviation": 0.30,
        "entropy": 0.20,
        "pattern": 0.25,
        "network": 0.25,
    }

    deviation_component = float(np.clip(deviation_score, 0, 100))

    entropy_component = 0.0
    if entropy_result.get("anomaly_flag"):
        entropy_component = 80.0
    elif float(entropy_result.get("composite_entropy", 0.0) or 0.0) < 1.0:
        entropy_component = 50.0

    pattern_component = 0.0
    if pattern_matches:
        pattern_component = min(100.0, float(pattern_matches[0].get("confidence", 0.0)) * 100.0)

    network_component = min(
        100.0,
        float(network_features.get("correlated_wallets_count", 0.0)) * 20.0
        + float(network_features.get("neighbor_max_risk", 0.0)) * 50.0
        + (30.0 if float(network_features.get("funding_depth", 10.0)) > 5 else 0.0),
    )

    composite = (
        weights["deviation"] * deviation_component
        + weights["entropy"] * entropy_component
        + weights["pattern"] * pattern_component
        + weights["network"] * network_component
    )

    return round(float(np.clip(composite, 0, 100)), 1)


class GameTheoryEngine:
    """High-level orchestrator for game-theory analysis."""

    def __init__(self) -> None:
        self.entropy = BehavioralEntropyAnalyzer()
        self.pattern_miner = ACOPatternMiner()
        self.graph = WalletGraphAnalyzer()

    def analyze(
        self,
        *,
        anomaly: Dict[str, Any],
        feature_vector: Any,
        wallet_trades: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> GameTheoryAnalysis:
        trades = list(wallet_trades or [])
        if not trades:
            # Build a one-event pseudo-history from the current anomaly.
            trades = [
                {
                    "timestamp": anomaly.get("trade_timestamp") or anomaly.get("timestamp"),
                    "market_id": anomaly.get("market_id"),
                    "wallet_address": anomaly.get("wallet_address"),
                    "trade_size": anomaly.get("trade_size", anomaly.get("trade_size_usd", 0.0)),
                    "side": anomaly.get("position_side", "buy"),
                    "hours_before_news": anomaly.get("hours_before_news"),
                    "is_fresh_wallet": bool(getattr(feature_vector, "is_fresh_wallet", 0)),
                }
            ]

        entropy_result = self.entropy.compute_trading_entropy(trades)
        sequence = self.pattern_miner.encode_trade_sequence(trades)
        matched_patterns = self.pattern_miner.match_pattern(sequence)
        network_features = self.graph.compute_network_features(
            str(anomaly.get("wallet_address", "")),
            trades,
        )

        player_fit = self._compute_player_type_fit(anomaly, feature_vector)
        best_fit = max(player_fit, key=player_fit.get) if player_fit else PlayerType.SPECULATOR.value

        # Deviation score as inverse fit to legitimate classes + insider affinity.
        insider_fit = player_fit.get(PlayerType.INSIDER.value, 0.0)
        legit_fit = max(
            player_fit.get(PlayerType.OSINT_EDGE.value, 0.0),
            player_fit.get(PlayerType.FAST_REACTOR.value, 0.0),
            player_fit.get(PlayerType.SPECULATOR.value, 0.0),
        )
        deviation_score = float(np.clip((insider_fit - legit_fit + 0.5) * 100.0, 0, 100))

        gt_score = compute_game_theory_score(
            deviation_score=deviation_score,
            entropy_result=entropy_result,
            pattern_matches=matched_patterns,
            network_features=network_features,
        )

        return GameTheoryAnalysis(
            behavioral_deviation_score=round(deviation_score, 1),
            player_type_fit={k: round(v, 3) for k, v in player_fit.items()},
            best_fit_type=best_fit,
            composite_entropy=float(entropy_result.get("composite_entropy", 0.0) or 0.0),
            entropy_anomaly=bool(entropy_result.get("anomaly_flag", False)),
            entropy_details=entropy_result,
            matched_patterns=matched_patterns,
            pattern_confidence=float(matched_patterns[0].get("confidence", 0.0)) if matched_patterns else 0.0,
            network_features=network_features,
            game_theory_suspicion_score=gt_score,
        )

    @staticmethod
    def _compute_player_type_fit(anomaly: Dict[str, Any], feature_vector: Any) -> Dict[str, float]:
        hbn = anomaly.get("hours_before_news")
        osint_count = float(anomaly.get("osint_signals_before_trade", 0) or 0)
        fresh = float(getattr(feature_vector, "is_fresh_wallet", 0) or 0)
        z_score = float(anomaly.get("z_score", 0) or 0)
        pos_pct = float(getattr(feature_vector, "position_size_pct", 0.0) or 0.0)

        try:
            hbn_val = float(hbn) if hbn is not None else None
        except Exception:
            hbn_val = None

        insider = 0.2 + 0.25 * fresh + 0.15 * min(1.0, z_score / 5.0) + 0.10 * min(1.0, pos_pct / 10.0)
        if hbn_val is not None and hbn_val < 0:
            insider += min(0.35, abs(hbn_val) / 24.0)
        if osint_count <= 0:
            insider += 0.10

        osint_edge = 0.15 + 0.15 * min(1.0, osint_count / 5.0)
        if hbn_val is not None and hbn_val > 1:
            osint_edge += min(0.35, hbn_val / 48.0)

        fast = 0.10
        if hbn_val is not None and 0 <= hbn_val <= 0.25:
            fast += 0.75

        spec = 0.20
        if hbn_val is None:
            spec += 0.40
        if z_score < 1.5:
            spec += 0.15

        raw = {
            PlayerType.INSIDER.value: float(np.clip(insider, 0, 1)),
            PlayerType.OSINT_EDGE.value: float(np.clip(osint_edge, 0, 1)),
            PlayerType.FAST_REACTOR.value: float(np.clip(fast, 0, 1)),
            PlayerType.SPECULATOR.value: float(np.clip(spec, 0, 1)),
        }

        total = sum(raw.values())
        if total <= 0:
            return raw
        return {k: v / total for k, v in raw.items()}


__all__ = [
    "PlayerType",
    "GameTheoryAnalysis",
    "BehavioralEntropyAnalyzer",
    "ACOPatternMiner",
    "WalletGraphAnalyzer",
    "compute_game_theory_score",
    "GameTheoryEngine",
]
