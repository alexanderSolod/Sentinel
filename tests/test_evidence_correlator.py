import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from src.data.database import get_connection, init_schema, list_evidence_packets
from src.data.websocket_handler import TradeEvent
from src.pipeline.evidence_correlator import EvidenceCorrelator
from src.detection.wallet_profiler import WalletProfile


class EvidenceCorrelatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "evidence.db")
        init_schema(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_temporal_gap_score_behavior(self) -> None:
        self.assertEqual(EvidenceCorrelator.compute_temporal_gap_score(None), 1.0)
        self.assertGreater(
            EvidenceCorrelator.compute_temporal_gap_score(-120.0),
            EvidenceCorrelator.compute_temporal_gap_score(15.0),
        )

    def test_process_trade_persists_evidence_packet(self) -> None:
        correlator = EvidenceCorrelator(db_path=self.db_path)
        trade = TradeEvent(
            trade_id="t-1",
            market_id="mkt-1",
            market_slug="election-market",
            wallet_address="0x" + "1" * 40,
            side="buy",
            outcome="yes",
            price=Decimal("0.62"),
            size=Decimal("1000"),
            notional_value=Decimal("1000"),
            timestamp=datetime.now(timezone.utc),
            raw_data={},
        )

        packet = asyncio.run(correlator.process_trade(trade, osint_events_override=[]))
        self.assertIsNotNone(packet.get("case_id"))
        self.assertEqual(packet["market_id"], "mkt-1")
        self.assertEqual(packet["wallet_address"], trade.wallet_address.lower())
        evidence = json.loads(packet["evidence_json"])
        self.assertIn("autoencoder", evidence)
        self.assertIn("normalized_score", evidence["autoencoder"])

        conn = get_connection(self.db_path)
        try:
            packets = list_evidence_packets(conn, limit=10)
            self.assertEqual(len(packets), 1)
            self.assertEqual(packets[0]["case_id"], packet["case_id"])
            self.assertEqual(packets[0]["packet_id"], packet["case_id"])
        finally:
            conn.close()

    def test_estimate_trade_z_score_uses_wallet_baseline(self) -> None:
        profile = WalletProfile(address="0xabc")
        profile.avg_trade_size = Decimal("1000")

        score = EvidenceCorrelator._estimate_trade_z_score(3000.0, profile)
        self.assertGreater(score, 1.0)


if __name__ == "__main__":
    unittest.main()
