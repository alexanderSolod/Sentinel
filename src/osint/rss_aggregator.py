"""
RSS/News Aggregator for OSINT signals.
Adapted from worldmonitor patterns.

Fetches and normalizes news from multiple RSS sources for
correlation with prediction market events.
"""
import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import time

logger = logging.getLogger(__name__)

# Default RSS feeds to monitor
DEFAULT_FEEDS = {
    # Major News
    "reuters": "https://feeds.reuters.com/reuters/topNews",
    "ap_news": "https://rsshub.app/apnews/topics/apf-topnews",
    "bbc": "http://feeds.bbci.co.uk/news/world/rss.xml",

    # Politics
    "politico": "https://rss.politico.com/politics-news.xml",
    "thehill": "https://thehill.com/feed/",

    # Finance
    "bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
    "cnbc": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",

    # Crypto
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",

    # Sports
    "espn": "https://www.espn.com/espn/rss/news",

    # Tech
    "techcrunch": "https://techcrunch.com/feed/",
    "verge": "https://www.theverge.com/rss/index.xml",
}

# Category detection keywords (from polymarket-insider-tracker)
CATEGORY_KEYWORDS = {
    "politics": [
        "election", "president", "congress", "senate", "governor",
        "democrat", "republican", "trump", "biden", "vote", "ballot",
    ],
    "crypto": [
        "bitcoin", "ethereum", "crypto", "btc", "eth", "blockchain",
        "token", "defi", "nft", "solana",
    ],
    "sports": [
        "nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball",
        "championship", "playoffs", "finals", "super bowl",
    ],
    "finance": [
        "fed", "interest rate", "inflation", "gdp", "stock", "market",
        "recession", "economy", "treasury", "bond",
    ],
    "tech": [
        "apple", "google", "microsoft", "amazon", "meta", "tesla",
        "ai", "artificial intelligence", "openai", "chatgpt",
    ],
    "geopolitics": [
        "war", "conflict", "military", "nato", "sanctions", "invasion",
        "diplomacy", "treaty", "ukraine", "russia", "china", "iran",
    ],
}


@dataclass
class NewsItem:
    """Represents a news item from RSS feed."""
    event_id: str
    title: str
    source: str
    url: str
    published: datetime
    summary: Optional[str] = None
    category: str = "other"
    relevance_score: float = 0.5
    keywords: List[str] = field(default_factory=list)

    @classmethod
    def from_feedparser_entry(
        cls,
        entry: Dict[str, Any],
        source: str,
    ) -> "NewsItem":
        """Create NewsItem from feedparser entry."""
        # Parse published date
        published = None
        for date_field in ["published_parsed", "updated_parsed", "created_parsed"]:
            if hasattr(entry, date_field) and getattr(entry, date_field):
                try:
                    import time
                    published = datetime.fromtimestamp(
                        time.mktime(getattr(entry, date_field)),
                        tz=timezone.utc
                    )
                    break
                except (TypeError, ValueError):
                    continue

        if published is None:
            published = datetime.now(timezone.utc)

        title = entry.get("title", "")
        url = entry.get("link", "")
        summary = entry.get("summary", entry.get("description", ""))

        # Generate event ID from URL hash
        event_id = hashlib.md5(url.encode()).hexdigest()[:12]

        # Detect category
        category = detect_category(title + " " + (summary or ""))

        return cls(
            event_id=event_id,
            title=title,
            source=source,
            url=url,
            published=published,
            summary=summary[:500] if summary else None,
            category=category,
        )


def detect_category(text: str) -> str:
    """Detect category from text using keyword matching."""
    text_lower = text.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return category

    return "other"


class RSSAggregator:
    """
    Aggregates news from multiple RSS feeds.

    Features:
    - Multi-source fetching
    - Deduplication via content hashing
    - Category detection
    - Relevance scoring
    """

    def __init__(
        self,
        feeds: Optional[Dict[str, str]] = None,
        cache_ttl_seconds: int = 300,  # 5 minutes
    ):
        """
        Initialize the aggregator.

        Args:
            feeds: Dict of source_name -> feed_url
            cache_ttl_seconds: How long to cache feed results
        """
        self.feeds = feeds or DEFAULT_FEEDS.copy()
        self.cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, tuple[float, List[NewsItem]]] = {}
        self._seen_ids: set = set()

    def fetch_feed(self, source: str, url: str) -> List[NewsItem]:
        """
        Fetch and parse a single RSS feed.

        Args:
            source: Source name
            url: Feed URL

        Returns:
            List of NewsItem objects
        """
        try:
            import feedparser
        except ImportError:
            logger.error("feedparser not installed. Run: pip install feedparser")
            return []

        # Check cache
        cache_key = f"{source}:{url}"
        if cache_key in self._cache:
            cached_time, cached_items = self._cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_items

        try:
            feed = feedparser.parse(url)

            if feed.bozo and feed.bozo_exception:
                logger.warning("Feed parse warning for %s: %s", source, feed.bozo_exception)

            items = []
            for entry in feed.entries[:20]:  # Limit to 20 items per feed
                try:
                    item = NewsItem.from_feedparser_entry(entry, source)

                    # Deduplication
                    if item.event_id not in self._seen_ids:
                        self._seen_ids.add(item.event_id)
                        items.append(item)

                except Exception as e:
                    logger.debug("Failed to parse entry from %s: %s", source, e)
                    continue

            # Update cache
            self._cache[cache_key] = (time.time(), items)

            logger.debug("Fetched %d items from %s", len(items), source)
            return items

        except Exception as e:
            logger.error("Failed to fetch feed %s: %s", source, e)
            return []

    def fetch_all(
        self,
        categories: Optional[List[str]] = None,
        max_age_hours: float = 24,
    ) -> List[NewsItem]:
        """
        Fetch from all configured feeds.

        Args:
            categories: Filter by categories (None = all)
            max_age_hours: Only return items newer than this

        Returns:
            List of NewsItem objects, sorted by recency
        """
        all_items = []
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)

        for source, url in self.feeds.items():
            items = self.fetch_feed(source, url)

            for item in items:
                # Filter by age
                if item.published.timestamp() < cutoff_time:
                    continue

                # Filter by category
                if categories and item.category not in categories:
                    continue

                all_items.append(item)

        # Sort by recency
        all_items.sort(key=lambda x: x.published, reverse=True)

        logger.info("Aggregated %d items from %d feeds", len(all_items), len(self.feeds))
        return all_items

    def search(
        self,
        query: str,
        max_results: int = 20,
    ) -> List[NewsItem]:
        """
        Search recent items by keyword.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            List of matching NewsItem objects
        """
        query_lower = query.lower()
        all_items = self.fetch_all()

        matches = []
        for item in all_items:
            text = f"{item.title} {item.summary or ''}".lower()
            if query_lower in text:
                # Calculate relevance score based on match quality
                title_match = query_lower in item.title.lower()
                item.relevance_score = 0.8 if title_match else 0.5
                matches.append(item)

        # Sort by relevance then recency
        matches.sort(key=lambda x: (x.relevance_score, x.published.timestamp()), reverse=True)

        return matches[:max_results]

    def get_items_in_window(
        self,
        start_time: datetime,
        end_time: datetime,
        category: Optional[str] = None,
    ) -> List[NewsItem]:
        """
        Get items within a time window.

        Useful for temporal gap analysis.

        Args:
            start_time: Window start
            end_time: Window end
            category: Optional category filter

        Returns:
            List of NewsItem objects in the window
        """
        all_items = self.fetch_all(
            categories=[category] if category else None,
            max_age_hours=72,  # Look back 3 days
        )

        window_items = []
        for item in all_items:
            if start_time <= item.published <= end_time:
                window_items.append(item)

        return window_items

    def clear_cache(self):
        """Clear the feed cache."""
        self._cache.clear()
        self._seen_ids.clear()


# GDELT API Client (adapted from worldmonitor)
class GDELTClient:
    """
    Client for GDELT (Global Database of Events, Language, and Tone).

    GDELT provides real-time monitoring of global news and events.
    """

    BASE_URL = "https://api.gdeltproject.org/api/v2"

    def __init__(self, cache_ttl_minutes: int = 15):
        self.cache_ttl = cache_ttl_minutes * 60
        self._cache: Dict[str, tuple[float, Any]] = {}

    def search_documents(
        self,
        query: str,
        max_records: int = 20,
        timespan: str = "72h",
        sort: str = "DateDesc",
    ) -> List[Dict[str, Any]]:
        """
        Search GDELT documents.

        Args:
            query: Search query
            max_records: Maximum results (max 250)
            timespan: Time span (e.g., "72h", "1w")
            sort: Sort order

        Returns:
            List of article dicts
        """
        import requests

        cache_key = f"gdelt:{query}:{timespan}"
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data

        try:
            url = f"{self.BASE_URL}/doc/doc"
            params = {
                "query": query,
                "mode": "ArtList",
                "maxrecords": min(max_records, 250),
                "timespan": timespan,
                "sort": sort,
                "format": "json",
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            articles = data.get("articles", [])

            # Cache results
            self._cache[cache_key] = (time.time(), articles)

            logger.debug("GDELT returned %d articles for '%s'", len(articles), query)
            return articles

        except Exception as e:
            logger.error("GDELT search failed: %s", e)
            return []

    def get_events(
        self,
        query: str,
        timespan: str = "24h",
    ) -> List[Dict[str, Any]]:
        """
        Get GDELT events matching query.

        Args:
            query: Search query
            timespan: Time span

        Returns:
            List of event dicts
        """
        import requests

        try:
            url = f"{self.BASE_URL}/geo/geo"
            params = {
                "query": query,
                "format": "GeoJSON",
                "timespan": timespan,
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            features = data.get("features", [])

            return [f.get("properties", {}) for f in features]

        except Exception as e:
            logger.error("GDELT events query failed: %s", e)
            return []


if __name__ == "__main__":
    # Test the aggregator
    print("Testing RSS Aggregator...")

    try:
        import feedparser
    except ImportError:
        print("Installing feedparser...")
        import subprocess
        subprocess.run(["pip", "install", "feedparser", "-q"])

    aggregator = RSSAggregator()

    # Test single feed
    print("\n📰 Testing single feed (Reuters):")
    items = aggregator.fetch_feed("reuters", DEFAULT_FEEDS["reuters"])
    for item in items[:3]:
        print(f"  [{item.category}] {item.title[:60]}...")

    # Test search
    print("\n🔍 Testing search (politics):")
    matches = aggregator.search("election", max_results=5)
    for item in matches:
        print(f"  [{item.source}] {item.title[:50]}...")

    # Test GDELT
    print("\n🌐 Testing GDELT:")
    gdelt = GDELTClient()
    articles = gdelt.search_documents("prediction market", max_records=3)
    for article in articles:
        print(f"  {article.get('title', 'No title')[:50]}...")
