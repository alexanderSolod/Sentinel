import os
import unittest
from unittest.mock import patch

from src.osint.sources import FIRMSClient


class FirmsEnvAliasTests(unittest.TestCase):
    def test_firms_client_uses_primary_env_var(self) -> None:
        with patch.dict(
            os.environ,
            {"NASA_FIRMS_API_KEY": "primary-key", "NASA_FIRMS_KEY": "legacy-key"},
            clear=False,
        ):
            client = FIRMSClient()
            self.assertEqual(client.api_key, "primary-key")

    def test_firms_client_falls_back_to_legacy_env_var(self) -> None:
        with patch.dict(
            os.environ,
            {"NASA_FIRMS_API_KEY": "", "NASA_FIRMS_KEY": "legacy-key"},
            clear=False,
        ):
            client = FIRMSClient()
            self.assertEqual(client.api_key, "legacy-key")


if __name__ == "__main__":
    unittest.main()
