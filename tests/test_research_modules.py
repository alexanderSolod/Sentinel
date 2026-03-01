import unittest

from src.detection.features import FeatureVector
from src.detection.fp_gate import FalsePositiveGate
from src.detection.game_theory import GameTheoryEngine
from src.detection.rf_classifier import RFClassifier
from src.detection.streaming_detector import StreamingAnomalyDetector
from src.osint.text_analyzer import OSINTTextAnalyzer


class ResearchModulesTests(unittest.TestCase):
    def test_rf_classifier_heuristic_prediction_shape(self) -> None:
        clf = RFClassifier(model_path="/tmp/nonexistent-rf.pkl")
        vec = FeatureVector(
            wallet_age_days=2,
            wallet_trade_count=1,
            is_fresh_wallet=1,
            z_score=4.2,
            hours_before_news=-4,
            osint_signal_count=0,
        )

        pred = clf.predict(vec)
        self.assertIn("rf_score", pred)
        self.assertIn("rf_label", pred)
        self.assertIn("top_features", pred)
        self.assertGreaterEqual(pred["rf_score"], 0.0)
        self.assertLessEqual(pred["rf_score"], 1.0)

    def test_game_theory_engine_output_ranges(self) -> None:
        engine = GameTheoryEngine()
        vec = FeatureVector(
            wallet_age_days=3,
            wallet_trade_count=1,
            is_fresh_wallet=1,
            z_score=3.5,
            hours_before_news=-5,
            osint_signal_count=0,
            position_size_pct=15.0,
        )
        analysis = engine.analyze(
            anomaly={
                "market_id": "mkt-1",
                "wallet_address": "0xabc",
                "trade_timestamp": "2026-03-01T00:00:00+00:00",
                "hours_before_news": -5,
                "z_score": 3.5,
                "osint_signals_before_trade": 0,
            },
            feature_vector=vec,
        )

        self.assertGreaterEqual(analysis.game_theory_suspicion_score, 0.0)
        self.assertLessEqual(analysis.game_theory_suspicion_score, 100.0)
        self.assertTrue(analysis.best_fit_type)

    def test_streaming_detector_flags_spike_after_baseline(self) -> None:
        detector = StreamingAnomalyDetector(baseline_window=100, z_threshold=2.0)
        for _ in range(30):
            detector.process_trade(
                {
                    "market_id": "mkt-1",
                    "amount_usd": 1000,
                    "price": 0.5,
                    "timestamp": "2026-03-01T00:00:00+00:00",
                }
            )

        out = detector.process_trade(
            {
                "market_id": "mkt-1",
                "amount_usd": 10000,
                "price": 0.8,
                "timestamp": "2026-03-01T00:01:00+00:00",
            }
        )
        self.assertTrue(out["is_anomalous"])

    def test_text_analyzer_returns_relevance(self) -> None:
        analyzer = OSINTTextAnalyzer()
        result = analyzer.compute_relevance_score(
            osint_text="White House announces tariffs on China imports",
            market_description="Will the US announce China tariffs?",
            market_keywords=["us", "china", "tariffs"],
        )
        self.assertIn("composite_relevance", result)
        self.assertGreaterEqual(result["composite_relevance"], 0.0)

    def test_false_positive_gate_emits_decision(self) -> None:
        gate = FalsePositiveGate()
        result = gate.evaluate(
            trade={"market_id": "mkt-1"},
            features={
                "statistical_score": 0.7,
                "rf_score": 0.8,
                "autoencoder_score": 0.6,
                "game_theory_score": 70,
                "bss_score": 85,
            },
        )
        self.assertIn("final_decision", result)
        self.assertIn("gates_passed", result)

    def test_false_positive_gate_missing_autoencoder_is_neutral(self) -> None:
        gate = FalsePositiveGate()
        result = gate.evaluate(
            trade={"market_id": "mkt-1"},
            features={
                "statistical_score": 0.8,
                "rf_score": 0.8,
                "game_theory_score": 80,
                "bss_score": 80,
            },
        )
        self.assertNotEqual(result.get("dismissed_at_gate"), "autoencoder")


if __name__ == "__main__":
    unittest.main()
