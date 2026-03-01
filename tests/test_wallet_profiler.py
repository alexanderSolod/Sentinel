import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.detection.wallet_profiler import FundingSource, WalletProfiler


class WalletProfilerTests(unittest.TestCase):
    def test_nonce_and_age_update_on_trade(self) -> None:
        profiler = WalletProfiler()
        first_seen = datetime.now(timezone.utc) - timedelta(hours=4)
        profiler.get_or_create_profile("0xabc", nonce=0, first_seen=first_seen)

        profiler.record_trade(
            wallet_address="0xabc",
            market_id="market-1",
            side="buy",
            outcome="yes",
            size=Decimal("100"),
            price=Decimal("0.42"),
        )
        profile = profiler.get_profile("0xabc")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.nonce, 1)
        self.assertGreaterEqual(profile.age_hours or 0, 4.0)

    def test_funding_chain_total_and_source_selection(self) -> None:
        profiler = WalletProfiler()
        txs = [
            {
                "from": "0x503828976d22510aad0201ac7ec88293211d23da",  # coinbase
                "value": "100",
                "hash": "0x1",
            },
            {
                "from": "0x722122df12d4e14e13ac3b6895a86e84145b6967",  # tornado
                "value": "250",
                "hash": "0x2",
            },
            {
                "from": "0x9999999999999999999999999999999999999999",
                "value": "300",
                "hash": "0x3",
            },
        ]

        chain = profiler.analyze_funding_chain("0xwallet", txs)
        self.assertEqual(chain.total_funded, Decimal("650"))
        self.assertEqual(chain.source_type, FundingSource.MIXER)
        self.assertAlmostEqual(chain.risk_score, 0.9)


if __name__ == "__main__":
    unittest.main()
