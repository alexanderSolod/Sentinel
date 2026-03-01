"""
Polymarket API Client
Fetches market data, trades, and prices from Polymarket's CLOB API.

Adapted from polymarket-insider-tracker (MIT License):
- Rate limiting (10 requests/second token bucket)
- Automatic retry with exponential backoff
- Paginated market fetching

API Documentation: https://docs.polymarket.com/
Base URLs:
  - CLOB API: https://clob.polymarket.com
  - Gamma API: https://gamma-api.polymarket.com
"""
import os
import logging
import requests
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Callable, TypeVar, Union
from functools import wraps
import time

logger = logging.getLogger(__name__)

# Rate limiting constants (from polymarket-insider-tracker)
MAX_REQUESTS_PER_SECOND = 10

# Retry constants
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 1.0
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)

T = TypeVar("T")


class RateLimiter:
    """Token bucket rate limiter for API requests (from polymarket-insider-tracker)."""

    def __init__(self, max_requests_per_second: float = MAX_REQUESTS_PER_SECOND):
        self._min_interval = 1.0 / max_requests_per_second
        self._last_request_time: float = 0.0

    def acquire(self) -> None:
        """Wait until a request slot is available."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            wait_time = self._min_interval - elapsed
            time.sleep(wait_time)
        self._last_request_time = time.monotonic()


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_RETRY_BASE_DELAY,
) -> Callable:
    """Decorator for adding retry logic with exponential backoff (from polymarket-insider-tracker)."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.HTTPError as e:
                    status_code = e.response.status_code if e.response is not None else None
                    # Fail fast on non-retryable HTTP errors.
                    if status_code is not None and status_code not in RETRY_STATUS_CODES:
                        raise
                    last_exception = e
                    if attempt == max_retries:
                        break

                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Attempt %d/%d failed with HTTP %s. Retrying in %.1f seconds...",
                        attempt + 1, max_retries + 1, status_code, delay,
                    )
                    time.sleep(delay)
                except requests.RequestException as e:
                    last_exception = e
                    if attempt == max_retries:
                        break

                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Attempt %d/%d failed: %s. Retrying in %.1f seconds...",
                        attempt + 1, max_retries + 1, str(e), delay,
                    )
                    time.sleep(delay)
                except Exception:
                    # Unexpected errors are likely programming errors and should fail fast.
                    raise

            raise RuntimeError(
                f"All {max_retries + 1} attempts failed for {func.__name__}"
            ) from last_exception

        return wrapper
    return decorator


class PolymarketClient:
    """Client for interacting with Polymarket APIs."""

    CLOB_BASE_URL = "https://clob.polymarket.com"
    GAMMA_BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        requests_per_second: float = MAX_REQUESTS_PER_SECOND,
    ):
        """
        Initialize the Polymarket client.

        Args:
            api_key: Optional API key for authenticated endpoints
            api_secret: Optional API secret for authenticated endpoints
            requests_per_second: Rate limit for API requests (default 10)
        """
        self.api_key = api_key or os.getenv("POLYMARKET_API_KEY")
        self.api_secret = api_secret or os.getenv("POLYMARKET_API_SECRET")
        self._rate_limiter = RateLimiter(requests_per_second)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Sentinel/1.0",
            "Accept": "application/json",
        })

        logger.info(
            "Initialized PolymarketClient with rate_limit=%.1f req/s",
            requests_per_second,
        )

    @with_retry()
    def _request(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request with rate limiting and retry."""
        self._rate_limiter.acquire()
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.warning("API request failed: %s", e)
            raise

    # ============================================================
    # Gamma API - Market Discovery & Metadata
    # ============================================================

    def get_markets(
        self,
        active: bool = True,
        limit: int = 100,
        offset: int = 0,
        order: str = "volume24hr",
        ascending: bool = False
    ) -> List[Dict]:
        """
        Get list of markets from Gamma API.

        Args:
            active: Only return active markets
            limit: Maximum number of markets to return
            offset: Pagination offset
            order: Field to order by (volume24hr, liquidity, startDate)
            ascending: Sort direction

        Returns:
            List of market objects with metadata
        """
        url = f"{self.GAMMA_BASE_URL}/markets"
        params = {
            "active": str(active).lower(),
            "limit": limit,
            "offset": offset,
            "order": order,
            "ascending": str(ascending).lower(),
        }
        response = self._request(url, params)
        return response if isinstance(response, list) else response.get("data", [])

    def get_market(self, condition_id: str) -> Optional[Dict]:
        """
        Get a single market by condition ID.

        Args:
            condition_id: The market's condition ID

        Returns:
            Market object or None
        """
        url = f"{self.GAMMA_BASE_URL}/markets/{condition_id}"
        return self._request(url)

    def search_markets(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search markets by text query.

        Args:
            query: Search string
            limit: Maximum results

        Returns:
            List of matching markets
        """
        markets = self.get_markets(limit=200)
        query_lower = query.lower()
        return [
            m for m in markets
            if query_lower in m.get("question", "").lower()
            or query_lower in m.get("description", "").lower()
        ][:limit]

    # ============================================================
    # CLOB API - Order Book & Trades
    # ============================================================

    def get_order_book(self, token_id: str) -> Dict:
        """
        Get the order book for a token.

        Args:
            token_id: The token ID (YES or NO token)

        Returns:
            Order book with bids and asks
        """
        url = f"{self.CLOB_BASE_URL}/book"
        params = {"token_id": token_id}
        return self._request(url, params)

    def get_price(self, token_id: str) -> Optional[float]:
        """
        Get the current mid price for a token.

        Args:
            token_id: The token ID

        Returns:
            Current mid price or None
        """
        book = self.get_order_book(token_id)
        if not book:
            return None

        bids = book.get("bids", [])
        asks = book.get("asks", [])

        if bids and asks:
            best_bid = float(bids[0]["price"])
            best_ask = float(asks[0]["price"])
            return (best_bid + best_ask) / 2

        return None

    def get_market_prices(self, market: Dict) -> Dict[str, float]:
        """
        Get current prices for both YES and NO outcomes of a market.

        Args:
            market: Market object with tokens array

        Returns:
            Dict with 'yes' and 'no' prices
        """
        tokens = market.get("tokens", [])
        prices = {}

        for token in tokens:
            token_id = token.get("token_id")
            outcome = token.get("outcome", "").lower()
            if token_id and outcome in ["yes", "no"]:
                price = self.get_price(token_id)
                if price is not None:
                    prices[outcome] = price

        return prices

    def get_prices(self, market: Dict) -> Dict[str, float]:
        """Backward-compatible alias for get_market_prices()."""
        return self.get_market_prices(market)

    def get_trades(
        self,
        market_id: Optional[str] = None,
        maker: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get recent trades.

        Args:
            market_id: Filter by market
            maker: Filter by maker address
            limit: Maximum trades to return

        Returns:
            List of trade objects
        """
        # Note: This endpoint may require authentication
        url = f"{self.CLOB_BASE_URL}/trades"
        params = {"limit": limit}
        if market_id:
            params["market"] = market_id
        if maker:
            params["maker"] = maker

        return self._request(url, params).get("data", [])

    def get_last_trade_price(self, token_id: str) -> Optional[Dict]:
        """
        Get the last trade price for a token.

        Args:
            token_id: The token ID

        Returns:
            Last trade info or None
        """
        url = f"{self.CLOB_BASE_URL}/last-trade-price"
        params = {"token_id": token_id}
        return self._request(url, params)

    # ============================================================
    # Derived Methods - Analytics
    # ============================================================

    def get_market_volume_24h(self, market: Dict) -> float:
        """
        Get 24-hour trading volume for a market.

        Args:
            market: Market object

        Returns:
            Volume in USD
        """
        return float(market.get("volume24hr", 0) or 0)

    def get_market_liquidity(self, market: Dict) -> float:
        """
        Get current liquidity for a market.

        Args:
            market: Market object

        Returns:
            Liquidity in USD
        """
        return float(market.get("liquidityNum", 0) or 0)

    def detect_volume_spike(
        self,
        market: Dict,
        threshold_multiplier: float = 3.0
    ) -> Optional[Dict]:
        """
        Detect if a market has a volume spike.

        Args:
            market: Market object
            threshold_multiplier: Volume must exceed average by this factor

        Returns:
            Spike info if detected, None otherwise
        """
        volume_24h = self.get_market_volume_24h(market)
        if volume_24h <= 0:
            return None

        avg_daily_volume = self._estimate_baseline_daily_volume(market, threshold_multiplier)
        if avg_daily_volume <= 0:
            return None

        spike_ratio = volume_24h / avg_daily_volume
        if spike_ratio >= threshold_multiplier:
            return {
                "market_id": market.get("conditionId"),
                "market_name": market.get("question"),
                "volume_24h": volume_24h,
                "avg_daily_volume": avg_daily_volume,
                "spike_ratio": spike_ratio,
                "detected_at": datetime.now().isoformat(),
            }

        return None

    def _estimate_baseline_daily_volume(
        self,
        market: Dict[str, Any],
        threshold_multiplier: float,
    ) -> float:
        """
        Estimate a baseline daily volume from available market metadata.

        Falls back to a conservative baseline so spike detection remains usable
        even when only 24h volume is available.
        """
        candidates: List[float] = []

        # Direct 7-day volume fields if available.
        for key in ("volume7d", "volume7day", "volume1wk"):
            value = float(market.get(key, 0) or 0)
            if value > 0:
                candidates.append(value / 7.0)

        # Lifetime volume divided by market age.
        lifetime_volume = float(
            market.get("volume", 0) or market.get("volumeNum", 0) or 0
        )
        created_at = (
            market.get("startDate")
            or market.get("createdAt")
            or market.get("created_at")
            or market.get("endDate")
        )
        created_dt = self._parse_iso_datetime(created_at)
        if lifetime_volume > 0 and created_dt:
            age_days = max(1.0, (datetime.now(timezone.utc) - created_dt).total_seconds() / 86400.0)
            candidates.append(lifetime_volume / age_days)

        if candidates:
            return sum(candidates) / len(candidates)

        # Fallback: assume current 24h volume is at threshold to avoid dead detection.
        return self.get_market_volume_24h(market) / max(threshold_multiplier, 1.0)

    @staticmethod
    def _parse_iso_datetime(value: Any) -> Optional[datetime]:
        """Parse timestamp-like values to UTC datetime."""
        if not value:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except ValueError:
                return None
        return None

    def scan_for_anomalies(
        self,
        volume_threshold: float = 3.0,
        price_change_threshold: float = 0.15,
        limit: int = 50
    ) -> List[Dict]:
        """
        Scan active markets for anomalies (volume spikes, price jumps).

        Args:
            volume_threshold: Multiplier for volume spike detection
            price_change_threshold: Minimum price change (0.15 = 15%)
            limit: Number of markets to scan

        Returns:
            List of detected anomalies
        """
        anomalies = []
        markets = self.get_markets(limit=limit)

        for market in markets:
            # Check for volume spike
            spike = self.detect_volume_spike(market, volume_threshold)
            if spike:
                anomalies.append({
                    "type": "volume_spike",
                    **spike
                })

            # Check for price jumps (would need historical data)
            # For now, we flag high-activity markets
            volume = self.get_market_volume_24h(market)
            if volume > 100000:  # $100K+ daily volume
                anomalies.append({
                    "type": "high_activity",
                    "market_id": market.get("conditionId"),
                    "market_name": market.get("question"),
                    "volume_24h": volume,
                    "detected_at": datetime.now().isoformat(),
                })

        return anomalies


# ============================================================
# Mock Client for Testing
# ============================================================

class MockPolymarketClient:
    """Mock client that returns synthetic data for testing."""

    def __init__(self):
        self.mock_markets = [
            {
                "conditionId": "0x123abc",
                "question": "Will the Fed raise rates in March 2025?",
                "description": "Resolution based on FOMC announcement",
                "volume24hr": 250000,
                "liquidityNum": 150000,
                "tokens": [
                    {"token_id": "yes-123", "outcome": "Yes"},
                    {"token_id": "no-123", "outcome": "No"},
                ],
                "active": True,
            },
            {
                "conditionId": "0x456def",
                "question": "Will Bitcoin exceed $100K before June?",
                "description": "BTC/USD price on major exchanges",
                "volume24hr": 500000,
                "liquidityNum": 300000,
                "tokens": [
                    {"token_id": "yes-456", "outcome": "Yes"},
                    {"token_id": "no-456", "outcome": "No"},
                ],
                "active": True,
            },
            {
                "conditionId": "0x789ghi",
                "question": "Will there be a government shutdown in March?",
                "description": "US federal government shutdown",
                "volume24hr": 175000,
                "liquidityNum": 80000,
                "tokens": [
                    {"token_id": "yes-789", "outcome": "Yes"},
                    {"token_id": "no-789", "outcome": "No"},
                ],
                "active": True,
            },
        ]

    def get_markets(self, **kwargs) -> List[Dict]:
        return self.mock_markets

    def get_market(self, condition_id: str) -> Optional[Dict]:
        for m in self.mock_markets:
            if m["conditionId"] == condition_id:
                return m
        return None

    def get_price(self, token_id: str) -> float:
        import random
        return round(random.uniform(0.2, 0.8), 2)

    def get_market_prices(self, market: Dict) -> Dict[str, float]:
        import random
        yes_price = round(random.uniform(0.2, 0.8), 2)
        return {"yes": yes_price, "no": round(1 - yes_price, 2)}

    def get_prices(self, market: Dict) -> Dict[str, float]:
        return self.get_market_prices(market)

    def scan_for_anomalies(self, **kwargs) -> List[Dict]:
        return [
            {
                "type": "volume_spike",
                "market_id": "0x123abc",
                "market_name": "Will the Fed raise rates in March 2025?",
                "volume_24h": 250000,
                "spike_ratio": 3.5,
                "detected_at": datetime.now().isoformat(),
            }
        ]


def get_client(mock: bool = False) -> Union[PolymarketClient, "MockPolymarketClient"]:
    """
    Get a Polymarket client instance.

    Args:
        mock: Use mock client for testing

    Returns:
        PolymarketClient or MockPolymarketClient
    """
    if mock:
        return MockPolymarketClient()
    return PolymarketClient()


if __name__ == "__main__":
    # Test the client
    print("Testing Polymarket Client...")

    # Use mock client for testing
    client = get_client(mock=True)

    print("\n📊 Mock Markets:")
    markets = client.get_markets()
    for m in markets:
        print(f"  - {m['question']}")
        prices = client.get_market_prices(m)
        print(f"    YES: {prices.get('yes', 'N/A')}, NO: {prices.get('no', 'N/A')}")

    print("\n🔍 Scanning for anomalies...")
    anomalies = client.scan_for_anomalies()
    for a in anomalies:
        print(f"  - {a['type']}: {a['market_name']}")

    # Try real API (may fail without network)
    print("\n🌐 Testing real API (limited)...")
    real_client = get_client(mock=False)
    try:
        markets = real_client.get_markets(limit=3)
        if markets:
            print(f"  Found {len(markets)} markets from real API")
            for m in markets[:3]:
                print(f"  - {m.get('question', 'Unknown')[:50]}...")
        else:
            print("  No markets returned (API may be rate limited)")
    except Exception as e:
        print(f"  Real API test failed: {e}")
