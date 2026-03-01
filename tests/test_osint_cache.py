import time
import unittest

from src.osint.sources import SimpleCache


class SimpleCacheTests(unittest.TestCase):
    def test_get_returns_none_after_expiry_and_evicts(self) -> None:
        cache = SimpleCache()
        cache.set("key", "value", ttl=1)
        self.assertEqual(cache.get("key"), "value")
        time.sleep(1.1)
        self.assertIsNone(cache.get("key"))
        self.assertFalse(cache.is_valid("key"))

    def test_is_valid_evicts_stale_entries(self) -> None:
        cache = SimpleCache()
        cache.set("another", {"x": 1}, ttl=0)
        self.assertFalse(cache.is_valid("another"))
        self.assertIsNone(cache.get("another"))


if __name__ == "__main__":
    unittest.main()
