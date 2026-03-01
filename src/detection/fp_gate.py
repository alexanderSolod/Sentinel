"""False-positive management gates and FPR tracking utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


class FalsePositiveGate:
    """
    Cascading decision gate combining statistical, RF, autoencoder,
    game-theory, and triage-level AI signals.

    This class is intentionally model-agnostic: each gate reads normalized
    scores from ``features`` and applies consistent decision thresholds.
    """

    def __init__(
        self,
        *,
        gate_weights: Optional[Dict[str, float]] = None,
        dismiss_threshold: float = 0.25,
        suspicious_threshold: float = 0.60,
    ) -> None:
        self.gate_weights = gate_weights or {
            "statistical": 0.20,
            "rf_classifier": 0.25,
            "autoencoder": 0.15,
            "game_theory": 0.20,
            "mistral": 0.20,
        }
        self.dismiss_threshold = dismiss_threshold
        self.suspicious_threshold = suspicious_threshold

    def evaluate(self, trade: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        gates = [
            ("statistical", self._score_statistical(features)),
            ("rf_classifier", self._score_rf(features)),
            ("autoencoder", self._score_autoencoder(features)),
            ("game_theory", self._score_game_theory(features)),
            ("mistral", self._score_mistral(features)),
        ]

        results: List[Dict[str, Any]] = []
        weighted_sum = 0.0
        total_weight = 0.0

        for gate_name, score in gates:
            weight = float(self.gate_weights.get(gate_name, 0.0))
            total_weight += weight
            weighted_sum += score * weight

            decision = "ESCALATE" if score >= self.suspicious_threshold else "PASS"
            if score <= self.dismiss_threshold:
                decision = "DISMISS"

            results.append({"gate": gate_name, "score": round(score, 4), "decision": decision})

            if decision == "DISMISS":
                return {
                    "final_decision": "LEGITIMATE",
                    "dismissed_at_gate": gate_name,
                    "gates_passed": results,
                    "cumulative_score": round(weighted_sum / max(total_weight, 1e-9), 4),
                }

        normalized_score = weighted_sum / max(total_weight, 1e-9)
        final_decision = "SUSPICIOUS" if normalized_score >= self.suspicious_threshold else "LEGITIMATE"

        return {
            "final_decision": final_decision,
            "gates_passed": results,
            "cumulative_score": round(normalized_score, 4),
        }

    @staticmethod
    def _score_statistical(features: Dict[str, Any]) -> float:
        return float(min(1.0, max(0.0, features.get("statistical_score", 0.0))))

    @staticmethod
    def _score_rf(features: Dict[str, Any]) -> float:
        return float(min(1.0, max(0.0, features.get("rf_score", 0.0))))

    @staticmethod
    def _score_autoencoder(features: Dict[str, Any]) -> float:
        # Expects an already normalized anomaly score. If absent, use a neutral
        # midpoint so this gate does not auto-dismiss due to missing telemetry.
        value = features.get("autoencoder_score")
        if value is None:
            return 0.5
        return float(min(1.0, max(0.0, value)))

    @staticmethod
    def _score_game_theory(features: Dict[str, Any]) -> float:
        gt = features.get("game_theory_score", 0.0)
        return float(min(1.0, max(0.0, gt / 100.0 if gt > 1 else gt)))

    @staticmethod
    def _score_mistral(features: Dict[str, Any]) -> float:
        # Map BSS to suspiciousness score if present.
        bss = features.get("bss_score")
        if bss is None:
            return 0.5
        return float(min(1.0, max(0.0, float(bss) / 100.0)))


class FPRTracker:
    def __init__(self) -> None:
        self.predictions: List[tuple[str, str]] = []

    def record(self, predicted: str, actual: str) -> None:
        self.predictions.append((predicted, actual))

    def compute_fpr(self) -> Dict[str, Any]:
        if not self.predictions:
            return {"fpr": None, "sample_size": 0}

        fp = sum(1 for p, a in self.predictions if p == "SUSPICIOUS" and a in ("FAST_REACTOR", "SPECULATOR"))
        tn = sum(1 for p, a in self.predictions if p == "LEGITIMATE" and a in ("FAST_REACTOR", "SPECULATOR"))
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        return {
            "fpr": fpr,
            "false_positives": fp,
            "true_negatives": tn,
            "sample_size": len(self.predictions),
            "target": "< 10%",
            "status": "OK" if fpr < 0.10 else "HIGH - retrain needed",
        }
