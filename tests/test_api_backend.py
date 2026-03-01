import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app
from src.data.database import (
    get_connection,
    init_schema,
    insert_anomaly,
    insert_case,
    insert_evidence_packet,
)


class APIBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "api.db")
        self.previous_db_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = self.db_path

        init_schema(self.db_path)
        conn = get_connection(self.db_path)
        try:
            insert_anomaly(
                conn,
                {
                    "event_id": "EVENT-API-1",
                    "market_id": "market-1",
                    "market_name": "Will policy X pass?",
                    "timestamp": "2026-02-20T00:00:00+00:00",
                    "trade_timestamp": "2026-02-20T00:00:00+00:00",
                    "wallet_address": "0xabc",
                    "trade_size": 15000,
                    "position_side": "YES",
                    "price_before": 0.31,
                    "price_after": 0.55,
                    "price_change": 0.24,
                    "volume_24h": 250000,
                    "volume_spike_ratio": 3.2,
                    "z_score": 4.1,
                    "classification": "INSIDER",
                    "bss_score": 91,
                    "pes_score": 12,
                    "confidence": 0.93,
                    "xai_narrative": "Suspicious timing and wallet behavior",
                    "fraud_triangle_json": '{"pressure":"high","opportunity":"high","rationalization":"unknown"}',
                },
            )
            insert_case(
                conn,
                {
                    "case_id": "CASE-API-1",
                    "anomaly_event_id": "EVENT-API-1",
                    "market_id": "market-1",
                    "market_name": "Will policy X pass?",
                    "classification": "INSIDER",
                    "bss_score": 91,
                    "pes_score": 12,
                    "temporal_gap_hours": -8.5,
                    "consensus_score": 0,
                    "status": "UNDER_REVIEW",
                    "evidence_json": '{"trade_size_usd":15000,"news_timestamp":"2026-02-20T08:00:00+00:00"}',
                },
            )
            insert_evidence_packet(
                conn,
                {
                    "packet_id": "CASE-API-1",
                    "case_id": "CASE-API-1",
                    "event_id": "EVENT-API-1",
                    "market_id": "market-1",
                    "market_name": "Will policy X pass?",
                    "market_slug": "policy-x-pass",
                    "wallet_address": "0xabc",
                    "trade_timestamp": "2026-02-20T00:00:00+00:00",
                    "side": "buy",
                    "outcome": "yes",
                    "trade_size": 15000,
                    "trade_price": 0.55,
                    "wallet_age_hours": 12,
                    "wallet_trade_count": 1,
                    "wallet_win_rate": None,
                    "wallet_risk_score": 0.82,
                    "is_fresh_wallet": 1,
                    "cluster_id": "cluster-1",
                    "cluster_size": 3,
                    "cluster_confidence": 0.6,
                    "osint_event_id": None,
                    "osint_source": None,
                    "osint_title": None,
                    "osint_timestamp": None,
                    "temporal_gap_minutes": -510,
                    "temporal_gap_score": 0.95,
                    "correlation_score": 0.83,
                    "evidence_json": '{"risk_flags":["fresh_wallet"],"osint_event_count":0}',
                },
            )
            conn.commit()
        finally:
            conn.close()

        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self.previous_db_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self.previous_db_path
        self.temp_dir.cleanup()

    def test_health_endpoint(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("stats", data)
        self.assertEqual(data["stats"]["total_cases"], 1)

    def test_anomalies_endpoint_with_filters(self) -> None:
        response = self.client.get("/api/anomalies", params={"classification": "INSIDER", "min_bss": 90})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["event_id"], "EVENT-API-1")
        self.assertIn("fraud_triangle", data["items"][0])

    def test_index_endpoint(self) -> None:
        response = self.client.get("/api/index", params={"status": "UNDER_REVIEW", "search": "policy"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"][0]["case_id"], "CASE-API-1")
        self.assertIn("evidence", data["items"][0])

    def test_case_detail_endpoint(self) -> None:
        response = self.client.get("/api/cases/CASE-API-1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["case"]["case_id"], "CASE-API-1")
        self.assertEqual(data["anomaly"]["event_id"], "EVENT-API-1")
        self.assertEqual(data["evidence_packet"]["case_id"], "CASE-API-1")
        self.assertEqual(data["vote_count"], 0)

    def test_vote_submission_updates_case(self) -> None:
        response = self.client.post(
            "/api/vote",
            json={
                "case_id": "CASE-API-1",
                "vote": "agree",
                "voter_id": "qa-user",
                "confidence": 5,
                "comment": "Matches insider profile",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "recorded")
        self.assertEqual(data["case_id"], "CASE-API-1")
        self.assertEqual(data["updated_case"]["vote_count"], 1)
        self.assertEqual(data["updated_case"]["votes_agree"], 1)

    def test_metrics_endpoint_available(self) -> None:
        response = self.client.get("/api/metrics", params={"min_votes": 1})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("evaluation", payload)


if __name__ == "__main__":
    unittest.main()
