from datetime import datetime, timezone
import unittest

from src.osint.correlator import CorrelationResult


class OSINTCorrelatorTests(unittest.TestCase):
    def test_trade_well_before_info_indicator(self) -> None:
        result = CorrelationResult(
            market_id="mkt-1",
            market_name="Will X happen?",
            trade_timestamp=datetime.now(timezone.utc),
            matched_events=[{"event_id": "ev-1"}],
            temporal_gaps_hours=[-7.0],
            earliest_signal=None,
            latest_signal=None,
            primary_gap_hours=-7.0,
            signal_count_before=0,
            signal_count_after=1,
            keywords_matched=[],
            relevance_scores=[0.9],
        )
        self.assertEqual(result.information_asymmetry_indicator, "TRADE_WELL_BEFORE_INFO")


if __name__ == "__main__":
    unittest.main()
