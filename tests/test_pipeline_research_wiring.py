import os
import unittest
from unittest.mock import patch

from src.classification.pipeline import SentinelPipeline


class PipelineResearchWiringTests(unittest.TestCase):
    def test_pipeline_populates_research_signals(self) -> None:
        anomaly = {
            "market_id": "mkt-r-1",
            "market_name": "Will tariffs be announced?",
            "wallet_address": "0x" + "a" * 40,
            "wallet_age_days": 2,
            "wallet_trades": 1,
            "trade_size": 50000,
            "price_before": 0.2,
            "price_after": 0.8,
            "z_score": 4.0,
            "hours_before_news": -6,
            "osint_signals_before_trade": 0,
            "timestamp": "2026-03-01T00:00:00+00:00",
            "trade_timestamp": "2026-03-01T00:00:00+00:00",
        }

        with patch.dict(os.environ, {"MISTRAL_API_KEY": ""}, clear=False):
            pipeline = SentinelPipeline(skip_low_suspicion=False, enable_rf_gate=True)
            result = pipeline.process_anomaly(anomaly, save_to_db=False)

        self.assertIn("research_signals", result.analysis)
        research = result.analysis["research_signals"]
        self.assertIn("rf_analysis", research)
        self.assertIn("game_theory_analysis", research)
        self.assertIn("rf_suspicion_score", result.triage)
        self.assertIn("game_theory_score", result.triage)

    def test_pipeline_accepts_alias_fields(self) -> None:
        anomaly = {
            "token": "Tariff Signal Market",
            "wallet": "0x" + "b" * 40,
            "wallet_age_days": 3,
            "wallet_trades": 2,
            "trade_size_usd": 12000,
            "price_before": 0.35,
            "price_after": 0.44,
            "z_score": 2.4,
            "hours_before_news": 1.5,
            "osint_signals_before_trade": 1,
            "timestamp": "2026-03-01T00:00:00+00:00",
        }

        with patch.dict(os.environ, {"MISTRAL_API_KEY": ""}, clear=False):
            pipeline = SentinelPipeline(skip_low_suspicion=False, enable_rf_gate=True)
            result = pipeline.process_anomaly(anomaly, save_to_db=False)

        self.assertTrue(result.classification in {"INSIDER", "OSINT_EDGE", "FAST_REACTOR", "SPECULATOR"})


if __name__ == "__main__":
    unittest.main()
