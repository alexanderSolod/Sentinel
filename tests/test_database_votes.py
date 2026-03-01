import tempfile
import unittest
from pathlib import Path

from src.data.database import (
    get_connection,
    get_case,
    init_schema,
    insert_case,
    insert_vote,
)


class DatabaseVoteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        init_schema(self.db_path)
        self.conn = get_connection(self.db_path)

        insert_case(
            self.conn,
            {
                "case_id": "CASE-TEST-1",
                "market_id": "market-1",
                "classification": "INSIDER",
                "status": "UNDER_REVIEW",
            },
        )
        self.conn.commit()

    def tearDown(self) -> None:
        self.conn.close()
        self.temp_dir.cleanup()

    def test_rejects_invalid_vote_value(self) -> None:
        with self.assertRaises(ValueError):
            insert_vote(
                self.conn,
                {
                    "vote_id": "vote-invalid",
                    "case_id": "CASE-TEST-1",
                    "vote": "drop_table",
                },
            )

    def test_updates_consensus_counters_and_status(self) -> None:
        votes = ["agree", "agree", "agree", "agree", "disagree"]
        for idx, vote in enumerate(votes):
            insert_vote(
                self.conn,
                {
                    "vote_id": f"vote-{idx}",
                    "case_id": "CASE-TEST-1",
                    "voter_id": f"user-{idx}",
                    "vote": vote,
                },
            )
        self.conn.commit()

        case = get_case(self.conn, "CASE-TEST-1")
        self.assertIsNotNone(case)
        self.assertEqual(case["vote_count"], 5)
        self.assertEqual(case["votes_agree"], 4)
        self.assertEqual(case["votes_disagree"], 1)
        self.assertEqual(case["votes_uncertain"], 0)
        self.assertEqual(case["status"], "CONFIRMED")
        self.assertAlmostEqual(case["consensus_score"], 80.0)


if __name__ == "__main__":
    unittest.main()
