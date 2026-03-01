import unittest

from src.classification.stage1_triage import _classify_with_rules


class Stage1TriageTests(unittest.TestCase):
    def test_fast_reactor_precedence_for_small_positive_gap(self) -> None:
        result = _classify_with_rules(
            {
                "wallet_age_days": 90,
                "wallet_trades": 20,
                "trade_size_usd": 5000,
                "hours_before_news": 0.05,
                "osint_signals_before_trade": 2,
                "z_score": 1.0,
            }
        )
        self.assertEqual(result.classification, "FAST_REACTOR")


if __name__ == "__main__":
    unittest.main()
