"""
Market-OSINT Correlator

Matches OSINT events to prediction markets and calculates temporal gaps
between trades and public information signals.

The temporal gap is THE key metric for distinguishing insider trading from
legitimate OSINT research:
  - trade BEFORE news → suspicious (negative gap = insider indicator)
  - trade AFTER news → legitimate (positive gap = OSINT_EDGE or FAST_REACTOR)

Usage:
    correlator = MarketCorrelator(vector_store=store)
    correlation = correlator.correlate(market_name, trade_timestamp)
"""
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    """Result of correlating a market with OSINT events."""
    market_id: str
    market_name: str
    trade_timestamp: datetime
    matched_events: List[Dict[str, Any]]
    temporal_gaps_hours: List[float]  # negative = trade before event
    earliest_signal: Optional[datetime]
    latest_signal: Optional[datetime]
    primary_gap_hours: Optional[float]  # gap to most relevant event
    signal_count_before: int  # OSINT signals before trade
    signal_count_after: int   # OSINT signals after trade
    keywords_matched: List[str]
    relevance_scores: List[float]

    @property
    def has_pre_trade_signals(self) -> bool:
        """Were there OSINT signals available before the trade?"""
        return self.signal_count_before > 0

    @property
    def information_asymmetry_indicator(self) -> str:
        """Classify the information asymmetry pattern."""
        if not self.matched_events:
            return "NO_SIGNALS"
        if self.primary_gap_hours is not None and self.primary_gap_hours < -6:
            return "TRADE_WELL_BEFORE_INFO"  # very suspicious
        if self.signal_count_before == 0:
            return "TRADE_BEFORE_INFO"  # suspicious
        if self.signal_count_before > 0 and self.primary_gap_hours is not None and self.primary_gap_hours > 0:
            return "TRADE_AFTER_INFO"  # legitimate
        return "MIXED_SIGNALS"


def _extract_keywords(market_name: str) -> List[str]:
    """Extract search keywords from a prediction market question."""
    # Remove common filler words
    stop_words = {
        "will", "the", "be", "a", "an", "in", "on", "at", "to", "of", "for",
        "and", "or", "is", "it", "this", "that", "by", "from", "with", "as",
        "before", "after", "during", "does", "do", "did", "have", "has", "had",
        "can", "could", "would", "should", "may", "might", "than", "more",
        "most", "what", "when", "where", "who", "how", "which", "there",
        "any", "next", "new", "first", "last", "about", "over", "between",
    }

    # Clean and tokenize
    text = re.sub(r'[?!.,;:\'"()\[\]{}]', " ", market_name.lower())
    words = text.split()
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    # Also extract named entities (capitalized words from original)
    entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', market_name)
    keywords.extend([e.lower() for e in entities if e.lower() not in stop_words])

    return list(dict.fromkeys(keywords))  # dedupe preserving order


def _parse_timestamp(ts: Any) -> Optional[datetime]:
    """Parse various timestamp formats to datetime."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
    return None


class MarketCorrelator:
    """Correlates OSINT events with prediction market trades."""

    def __init__(self, vector_store=None, db_conn=None):
        """
        Args:
            vector_store: VectorStore instance for semantic search.
            db_conn: SQLite connection for DB-based OSINT lookup.
        """
        self.vector_store = vector_store
        self.db_conn = db_conn

    def correlate(
        self,
        market_id: str,
        market_name: str,
        trade_timestamp: Any,
        window_hours: float = 48,
        max_events: int = 20,
    ) -> CorrelationResult:
        """
        Find OSINT events correlated with a market and compute temporal gaps.

        Args:
            market_id: Market identifier.
            market_name: Market question/name (used for semantic search).
            trade_timestamp: When the suspicious trade occurred.
            window_hours: Hours before/after trade to search.
            max_events: Maximum events to retrieve.

        Returns:
            CorrelationResult with matched events and temporal analysis.
        """
        trade_dt = _parse_timestamp(trade_timestamp)
        if trade_dt is None:
            trade_dt = datetime.now(timezone.utc)

        keywords = _extract_keywords(market_name)

        # Collect events from available sources
        matched_events = []

        # Source 1: Vector store (semantic search)
        if self.vector_store:
            vs_results = self.vector_store.search_by_market(
                market_name, market_keywords=keywords, k=max_events
            )
            for r in vs_results:
                event = {
                    "event_id": r["id"],
                    "title": r["document"],
                    "timestamp": r["metadata"].get("timestamp"),
                    "source": r["metadata"].get("source", "vector_store"),
                    "category": r["metadata"].get("category"),
                    "threat_level": r["metadata"].get("threat_level"),
                    "relevance_score": 1.0 - (r["distance"] or 0.5),
                }
                matched_events.append(event)

        # Source 2: Database (time-window search)
        if self.db_conn:
            try:
                from src.data.database import get_osint_events_in_range
                start = (trade_dt - timedelta(hours=window_hours)).isoformat()
                end = (trade_dt + timedelta(hours=window_hours)).isoformat()
                db_events = get_osint_events_in_range(
                    self.db_conn, start, end, limit=max_events
                )
                for ev in db_events:
                    # Check keyword relevance
                    text = f"{ev.get('headline', '')} {ev.get('description', '')}".lower()
                    matched_kws = [kw for kw in keywords if kw in text]
                    if matched_kws:
                        ev["relevance_score"] = len(matched_kws) / max(len(keywords), 1)
                        ev["matched_keywords"] = matched_kws
                        matched_events.append(ev)
            except Exception as e:
                logger.warning("DB OSINT lookup failed: %s", e)

        # Deduplicate by event_id
        seen_ids = set()
        unique_events = []
        for ev in matched_events:
            eid = ev.get("event_id", id(ev))
            if eid not in seen_ids:
                seen_ids.add(eid)
                unique_events.append(ev)
        matched_events = unique_events

        # Compute temporal gaps
        temporal_gaps = []
        before_count = 0
        after_count = 0
        event_timestamps = []

        for ev in matched_events:
            ev_dt = _parse_timestamp(ev.get("timestamp"))
            if ev_dt:
                gap_hours = (trade_dt - ev_dt).total_seconds() / 3600
                temporal_gaps.append(gap_hours)
                event_timestamps.append(ev_dt)
                ev["gap_hours"] = gap_hours

                if ev_dt <= trade_dt:
                    before_count += 1
                else:
                    after_count += 1

        # Sort by relevance
        matched_events.sort(key=lambda e: e.get("relevance_score", 0), reverse=True)
        relevance_scores = [e.get("relevance_score", 0) for e in matched_events]

        # Primary gap = gap to most relevant event
        primary_gap = None
        if matched_events and matched_events[0].get("gap_hours") is not None:
            primary_gap = matched_events[0]["gap_hours"]

        # Keywords matched across all events
        all_matched_kws = set()
        for ev in matched_events:
            all_matched_kws.update(ev.get("matched_keywords", []))

        return CorrelationResult(
            market_id=market_id,
            market_name=market_name,
            trade_timestamp=trade_dt,
            matched_events=matched_events,
            temporal_gaps_hours=temporal_gaps,
            earliest_signal=min(event_timestamps) if event_timestamps else None,
            latest_signal=max(event_timestamps) if event_timestamps else None,
            primary_gap_hours=primary_gap,
            signal_count_before=before_count,
            signal_count_after=after_count,
            keywords_matched=list(all_matched_kws),
            relevance_scores=relevance_scores,
        )

    def enrich_anomaly(
        self,
        anomaly: Dict[str, Any],
        window_hours: float = 48,
    ) -> Dict[str, Any]:
        """
        Enrich an anomaly dict with OSINT correlation data.

        Adds fields:
            osint_signals_before_trade, osint_signals_after_trade,
            hours_before_news, temporal_gap_hours, information_asymmetry
        """
        correlation = self.correlate(
            market_id=anomaly.get("market_id", "unknown"),
            market_name=anomaly.get("market_name", ""),
            trade_timestamp=anomaly.get("trade_timestamp", anomaly.get("timestamp")),
            window_hours=window_hours,
        )

        enriched = dict(anomaly)
        enriched["osint_signals_before_trade"] = correlation.signal_count_before
        enriched["osint_signals_after_trade"] = correlation.signal_count_after
        enriched["information_asymmetry"] = correlation.information_asymmetry_indicator

        if correlation.primary_gap_hours is not None:
            enriched["hours_before_news"] = correlation.primary_gap_hours
            enriched["temporal_gap_hours"] = correlation.primary_gap_hours

        if correlation.matched_events:
            enriched["osint_context"] = correlation.matched_events[:5]

        return enriched

    def batch_correlate(
        self,
        anomalies: List[Dict[str, Any]],
        window_hours: float = 48,
    ) -> List[Dict[str, Any]]:
        """Enrich a batch of anomalies with OSINT correlation."""
        return [self.enrich_anomaly(a, window_hours) for a in anomalies]


if __name__ == "__main__":
    print("Testing Market-OSINT Correlator...")
    print("=" * 60)

    # Set up vector store with test data
    from src.osint.vector_store import VectorStore

    store = VectorStore()
    test_events = [
        {
            "event_id": "osint-1",
            "title": "US Trade Representative hints at new tariff package",
            "description": "Sources suggest USTR preparing comprehensive tariff action on Chinese imports",
            "source": "GDELT",
            "category": "ECONOMIC",
            "threat_level": "HIGH",
            "timestamp": "2025-02-15T08:00:00Z",
        },
        {
            "event_id": "osint-2",
            "title": "White House confirms tariff announcement scheduled for Tuesday",
            "description": "Official White House statement confirms upcoming tariff announcement",
            "source": "RSS",
            "category": "ECONOMIC",
            "threat_level": "CRITICAL",
            "timestamp": "2025-02-15T18:00:00Z",
        },
        {
            "event_id": "osint-3",
            "title": "Iran nuclear deal talks enter final round",
            "description": "Diplomats report progress on Iran nuclear negotiations",
            "source": "GDELT",
            "category": "DIPLOMATIC",
            "threat_level": "MEDIUM",
            "timestamp": "2025-02-14T14:00:00Z",
        },
        {
            "event_id": "osint-4",
            "title": "Hurricane warning for Florida coast upgraded to Category 4",
            "description": "NHC upgrades hurricane warning as storm strengthens",
            "source": "GDACS",
            "category": "DISASTER",
            "threat_level": "CRITICAL",
            "timestamp": "2025-02-16T06:00:00Z",
        },
    ]
    store.add_events(test_events)

    correlator = MarketCorrelator(vector_store=store)

    # Test 1: Insider-like case (trade well before news)
    print("\n--- Test 1: Trade BEFORE tariff news (suspicious) ---")
    result = correlator.correlate(
        market_id="tariff-market",
        market_name="Will the US announce new tariffs on China?",
        trade_timestamp="2025-02-15T02:00:00Z",  # 6 hours before first signal
    )
    print(f"  Matched events: {len(result.matched_events)}")
    print(f"  Signals before trade: {result.signal_count_before}")
    print(f"  Signals after trade: {result.signal_count_after}")
    print(f"  Primary gap: {result.primary_gap_hours:.1f} hours")
    print(f"  Pattern: {result.information_asymmetry_indicator}")

    # Test 2: OSINT edge case (trade after news)
    print("\n--- Test 2: Trade AFTER tariff hints (legitimate) ---")
    result = correlator.correlate(
        market_id="tariff-market",
        market_name="Will the US announce new tariffs on China?",
        trade_timestamp="2025-02-15T12:00:00Z",  # after first signal
    )
    print(f"  Matched events: {len(result.matched_events)}")
    print(f"  Signals before trade: {result.signal_count_before}")
    print(f"  Primary gap: {result.primary_gap_hours:.1f} hours")
    print(f"  Pattern: {result.information_asymmetry_indicator}")

    # Test 3: Enrich anomaly
    print("\n--- Test 3: Enrich anomaly ---")
    anomaly = {
        "market_id": "hurricane-market",
        "market_name": "Will a hurricane make landfall in Florida?",
        "trade_timestamp": "2025-02-16T04:00:00Z",
        "wallet_address": "0xabc123",
        "trade_size": 25000,
        "z_score": 3.1,
    }
    enriched = correlator.enrich_anomaly(anomaly)
    print(f"  Original keys: {list(anomaly.keys())}")
    print(f"  Enriched keys: {list(enriched.keys())}")
    print(f"  OSINT before: {enriched.get('osint_signals_before_trade')}")
    print(f"  Info asymmetry: {enriched.get('information_asymmetry')}")
    if enriched.get("hours_before_news") is not None:
        print(f"  Hours before news: {enriched['hours_before_news']:.1f}")

    # Cleanup
    store.clear()
    print("\nTest complete.")
