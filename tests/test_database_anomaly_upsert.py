import tempfile
import unittest
from pathlib import Path

from src.data.database import get_anomaly, get_connection, init_schema, insert_anomaly


class DatabaseAnomalyUpsertTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        init_schema(self.db_path)
        self.conn = get_connection(self.db_path)

    def tearDown(self) -> None:
        self.conn.close()
        self.temp_dir.cleanup()

    def test_insert_anomaly_upserts_existing_event(self) -> None:
        base = {
            "event_id": "EVENT-1",
            "market_id": "market-1",
            "market_name": "Will X happen?",
            "timestamp": "2026-02-01T00:00:00+00:00",
            "trade_timestamp": "2026-02-01T00:00:00+00:00",
            "wallet_address": "0xabc",
            "trade_size": 1000.0,
            "position_side": "YES",
            "price_before": 0.4,
            "price_after": 0.6,
            "price_change": 0.2,
            "volume_24h": 10000.0,
            "volume_spike_ratio": 2.0,
            "z_score": 3.0,
            "classification": "SPECULATOR",
            "bss_score": 20,
            "pes_score": 50,
            "confidence": 0.7,
            "xai_narrative": "initial",
            "fraud_triangle_json": "{}",
        }
        insert_anomaly(self.conn, base)

        updated = dict(base)
        updated["classification"] = "INSIDER"
        updated["bss_score"] = 90
        updated["xai_narrative"] = "updated"
        insert_anomaly(self.conn, updated)
        self.conn.commit()

        stored = get_anomaly(self.conn, "EVENT-1")
        self.assertIsNotNone(stored)
        self.assertEqual(stored["classification"], "INSIDER")
        self.assertEqual(stored["bss_score"], 90)
        self.assertEqual(stored["xai_narrative"], "updated")


if __name__ == "__main__":
    unittest.main()
