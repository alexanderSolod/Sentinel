import unittest

import requests

from src.data.polymarket_client import PolymarketClient, with_retry


class StubPolymarketClient(PolymarketClient):
    def __init__(self):
        super().__init__(requests_per_second=1000)

    def get_price(self, token_id: str):
        return 0.6 if "yes" in token_id else 0.4


class PolymarketClientTests(unittest.TestCase):
    def test_get_prices_alias_returns_expected_outcomes(self) -> None:
        client = StubPolymarketClient()
        market = {
            "tokens": [
                {"token_id": "token-yes", "outcome": "Yes"},
                {"token_id": "token-no", "outcome": "No"},
            ]
        }
        self.assertEqual(client.get_prices(market), {"yes": 0.6, "no": 0.4})

    def test_detect_volume_spike_uses_fallback_baseline(self) -> None:
        client = PolymarketClient(requests_per_second=1000)
        market = {
            "conditionId": "market-1",
            "question": "Will X happen?",
            "volume24hr": 250,
        }
        spike = client.detect_volume_spike(market, threshold_multiplier=2.5)
        self.assertIsNotNone(spike)
        self.assertAlmostEqual(spike["spike_ratio"], 2.5)

    def test_retry_wrapper_fails_fast_for_non_retryable_http_errors(self) -> None:
        attempts = {"count": 0}

        @with_retry(max_retries=3, base_delay=0)
        def always_bad_request():
            attempts["count"] += 1
            response = requests.Response()
            response.status_code = 400
            raise requests.HTTPError(response=response)

        with self.assertRaises(requests.HTTPError):
            always_bad_request()
        self.assertEqual(attempts["count"], 1)

    def test_retry_wrapper_retries_for_retryable_http_errors(self) -> None:
        attempts = {"count": 0}

        @with_retry(max_retries=3, base_delay=0)
        def always_retryable_error():
            attempts["count"] += 1
            response = requests.Response()
            response.status_code = 503
            raise requests.HTTPError(response=response)

        with self.assertRaises(RuntimeError):
            always_retryable_error()
        # initial attempt + 3 retries
        self.assertEqual(attempts["count"], 4)


if __name__ == "__main__":
    unittest.main()
