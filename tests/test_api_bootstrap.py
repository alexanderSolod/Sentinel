import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app


class APIBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "fresh-bootstrap.db")
        self.previous_db_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = self.db_path

    def tearDown(self) -> None:
        if self.previous_db_path is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self.previous_db_path
        self.temp_dir.cleanup()

    def test_api_bootstraps_schema_for_fresh_database(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            health = client.get("/api/health")
            self.assertEqual(health.status_code, 200)
            self.assertEqual(health.json().get("status"), "ok")

            anomalies = client.get("/api/anomalies")
            self.assertEqual(anomalies.status_code, 200)
            payload = anomalies.json()
            self.assertEqual(payload.get("count"), 0)
            self.assertEqual(payload.get("total"), 0)


if __name__ == "__main__":
    unittest.main()
