import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app
from src.classification.evaluation import compute_evaluation_metrics
from src.data.database import get_connection, init_schema, insert_case, insert_vote


class EvaluationMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "metrics.db")
        init_schema(self.db_path)
        self.conn = get_connection(self.db_path)

        self._seed_case("CASE-M-1", "INSIDER", ["agree"] * 5)
        self._seed_case("CASE-M-2", "INSIDER", ["disagree"] * 5)
        self._seed_case("CASE-M-3", "SPECULATOR", ["agree"] * 5)
        self._seed_case("CASE-M-4", "SPECULATOR", ["disagree"] * 5)

        self.conn.commit()

    def tearDown(self) -> None:
        self.conn.close()
        self.temp_dir.cleanup()

    def _seed_case(self, case_id: str, classification: str, votes: list[str]) -> None:
        insert_case(
            self.conn,
            {
                "case_id": case_id,
                "market_id": f"market-{case_id.lower()}",
                "market_name": f"Market {case_id}",
                "classification": classification,
                "status": "UNDER_REVIEW",
            },
        )
        for idx, vote in enumerate(votes):
            insert_vote(
                self.conn,
                {
                    "vote_id": f"{case_id}-v{idx}",
                    "case_id": case_id,
                    "voter_id": f"user-{idx}",
                    "vote": vote,
                    "confidence": 5,
                },
            )

    def test_compute_metrics_fpr_fnr_and_confusion(self) -> None:
        metrics = compute_evaluation_metrics(self.conn, min_votes=5, positive_classes=["INSIDER"])
        counts = metrics["binary_confusion_matrix"]["counts"]
        arena = metrics["arena_consensus"]

        self.assertEqual(counts["tp"], 1)
        self.assertEqual(counts["fp"], 1)
        self.assertEqual(counts["tn"], 1)
        self.assertEqual(counts["fn"], 1)
        self.assertAlmostEqual(metrics["metrics"]["fpr"], 0.5)
        self.assertAlmostEqual(metrics["metrics"]["fnr"], 0.5)
        self.assertAlmostEqual(metrics["metrics"]["accuracy"], 0.5)
        self.assertAlmostEqual(arena["consensus_accuracy"], 0.5)


class EvaluationMetricsEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "metrics_api.db")
        self.previous_db_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = self.db_path

        init_schema(self.db_path)
        conn = get_connection(self.db_path)
        try:
            insert_case(
                conn,
                {
                    "case_id": "CASE-API-M-1",
                    "market_id": "market-api-m-1",
                    "market_name": "API metrics market",
                    "classification": "INSIDER",
                    "status": "UNDER_REVIEW",
                },
            )
            for idx in range(5):
                insert_vote(
                    conn,
                    {
                        "vote_id": f"api-m-v{idx}",
                        "case_id": "CASE-API-M-1",
                        "voter_id": f"api-user-{idx}",
                        "vote": "agree",
                        "confidence": 5,
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

    def test_metrics_endpoint_returns_evaluation_block(self) -> None:
        response = self.client.get("/api/metrics", params={"min_votes": 5})
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["status"], "ok")
        self.assertIn("evaluation", payload)
        self.assertEqual(payload["evaluation"]["coverage"]["evaluated_cases"], 1)
        self.assertEqual(payload["evaluation"]["binary_confusion_matrix"]["counts"]["tp"], 1)


if __name__ == "__main__":
    unittest.main()
