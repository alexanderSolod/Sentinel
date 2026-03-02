"""
OSINT Data Sources for Sentinel
Adapted from worldmonitor (https://github.com/koala73/worldmonitor)

This module provides access to multiple intelligence sources for
correlating with prediction market events.

Sources included:
- ACLED (Armed Conflict Location & Event Data)
- GDELT (Global Database of Events, Language, and Tone)
- GDACS (Global Disaster Alert and Coordination System)
- NASA FIRMS (Fire Information for Resource Management System)
- UCDP (Uppsala Conflict Data Program)
- EONET (Earth Observatory Natural Event Tracker)
"""
import os
import logging
import hashlib
import time
import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

import requests

logger = logging.getLogger(__name__)

# Cache TTLs (aligned with upstream refresh rates - from worldmonitor)
CACHE_TTL = {
    "acled": 900,      # 15 minutes (rate-limited API)
    "gdelt": 300,      # 5 minutes (frequent updates)
    "gdacs": 300,      # 5 minutes
    "firms": 3600,     # 1 hour (FIRMS updates ~3 hours)
    "ucdp": 21600,     # 6 hours
    "eonet": 1800,     # 30 minutes
}


class ThreatLevel(Enum):
    """Threat classification levels (from worldmonitor threat-classifier)."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EventCategory(Enum):
    """Event categories for classification."""
    CONFLICT = "conflict"
    PROTEST = "protest"
    DISASTER = "disaster"
    DIPLOMATIC = "diplomatic"
    ECONOMIC = "economic"
    TERRORISM = "terrorism"
    CYBER = "cyber"
    HEALTH = "health"
    ENVIRONMENTAL = "environmental"
    MILITARY = "military"
    POLITICAL = "political"


# Threat classification keywords (from worldmonitor threat-classifier.ts)
THREAT_KEYWORDS = {
    ThreatLevel.CRITICAL: [
        "nuclear strike", "invasion", "declaration of war", "coup",
        "genocide", "chemical attack", "biological attack", "mass casualty",
    ],
    ThreatLevel.HIGH: [
        "war", "armed conflict", "airstrike", "drone strike", "missile",
        "troops deployed", "cyberattack", "ransomware", "sanctions",
        "assassination", "terrorist attack", "insurgency",
    ],
    ThreatLevel.MEDIUM: [
        "protest", "riot", "military exercise", "diplomatic crisis",
        "trade war", "recession", "flood", "wildfire", "outbreak",
        "border tension", "naval exercise",
    ],
    ThreatLevel.LOW: [
        "election", "vote", "treaty", "climate change", "vaccine",
        "interest rate", "summit", "negotiation", "ceasefire",
    ],
}


@dataclass
class OSINTEvent:
    """Base class for OSINT events."""
    event_id: str
    source: str
    timestamp: datetime
    title: str
    description: Optional[str] = None
    category: EventCategory = EventCategory.POLITICAL
    threat_level: ThreatLevel = ThreatLevel.INFO
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country: Optional[str] = None
    url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConflictEvent(OSINTEvent):
    """Conflict/violence event (ACLED, UCDP)."""
    event_type: str = ""
    sub_event_type: str = ""
    fatalities: int = 0
    actors: List[str] = field(default_factory=list)


@dataclass
class DisasterEvent(OSINTEvent):
    """Natural disaster event (GDACS, EONET, FIRMS)."""
    disaster_type: str = ""  # earthquake, flood, wildfire, etc.
    severity: str = ""  # red, orange, green
    magnitude: Optional[float] = None


@dataclass
class IntelligenceEvent(OSINTEvent):
    """News/intelligence event (GDELT)."""
    tone: Optional[float] = None  # -100 to +100
    source_domain: str = ""


def classify_threat(text: str) -> ThreatLevel:
    """Classify threat level from text using keyword matching."""
    text_lower = text.lower()

    for level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH, ThreatLevel.MEDIUM, ThreatLevel.LOW]:
        for keyword in THREAT_KEYWORDS[level]:
            if keyword in text_lower:
                return level

    return ThreatLevel.INFO


class SimpleCache:
    """Simple in-memory cache with TTL."""

    def __init__(self):
        self._cache: Dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            expiry, data = self._cache[key]
            if time.time() < expiry:
                return data
            # Auto-evict stale entries when accessed.
            del self._cache[key]
        return None

    def set(self, key: str, data: Any, ttl: int):
        self._cache[key] = (time.time() + ttl, data)

    def is_valid(self, key: str) -> bool:
        if key in self._cache:
            expiry, _ = self._cache[key]
            is_valid = time.time() < expiry
            if not is_valid:
                del self._cache[key]
            return is_valid
        return False


# Global cache instance
_cache = SimpleCache()


class ACLEDClient:
    """
    ACLED (Armed Conflict Location & Event Data) client.

    API: https://acleddata.com/api/acled/read
    Requires: ACLED_ACCESS_TOKEN

    Tracks: Battles, Explosions/Remote violence, Violence against civilians
    """

    BASE_URL = "https://api.acleddata.com/acled/read"

    # Event types to track (from worldmonitor)
    EVENT_TYPES = [
        "Battles",
        "Explosions/Remote violence",
        "Violence against civilians",
        "Riots",
        "Protests",
        "Strategic developments",
    ]

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("ACLED_ACCESS_TOKEN")
        if not self.access_token:
            logger.warning("ACLED_ACCESS_TOKEN not set - ACLED queries will fail")

    def get_events(
        self,
        event_types: Optional[List[str]] = None,
        country: Optional[str] = None,
        days: int = 7,
        limit: int = 500,
    ) -> List[ConflictEvent]:
        """
        Fetch conflict events from ACLED.

        Args:
            event_types: Filter by event type
            country: Filter by country
            days: Look back N days
            limit: Maximum results

        Returns:
            List of ConflictEvent objects
        """
        if not self.access_token:
            return []

        cache_key = f"acled:{event_types}:{country}:{days}"
        if _cache.is_valid(cache_key):
            return _cache.get(cache_key)

        try:
            # Build date range
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            params = {
                "key": self.access_token,
                "event_date": f"{start_date}|{end_date}",
                "event_date_where": "BETWEEN",
                "limit": limit,
            }

            if event_types:
                params["event_type"] = "|".join(event_types)

            if country:
                params["country"] = country

            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            events = []
            for item in data.get("data", []):
                try:
                    event = ConflictEvent(
                        event_id=str(item.get("event_id_cnty", "")),
                        source="acled",
                        timestamp=datetime.strptime(
                            item.get("event_date", ""),
                            "%Y-%m-%d"
                        ).replace(tzinfo=timezone.utc),
                        title=f"{item.get('event_type', '')} in {item.get('location', '')}",
                        description=item.get("notes", ""),
                        category=EventCategory.CONFLICT,
                        threat_level=classify_threat(item.get("notes", "")),
                        latitude=float(item.get("latitude", 0)) or None,
                        longitude=float(item.get("longitude", 0)) or None,
                        country=item.get("country", ""),
                        event_type=item.get("event_type", ""),
                        sub_event_type=item.get("sub_event_type", ""),
                        fatalities=int(item.get("fatalities", 0)),
                        actors=[item.get("actor1", ""), item.get("actor2", "")],
                        raw_data=item,
                    )
                    events.append(event)
                except Exception as e:
                    logger.debug("Failed to parse ACLED event: %s", e)

            _cache.set(cache_key, events, CACHE_TTL["acled"])
            logger.info("Fetched %d ACLED events", len(events))
            return events

        except Exception as e:
            logger.error("ACLED query failed: %s", e)
            return []


class GDELTClient:
    """
    GDELT (Global Database of Events, Language, and Tone) client.

    API: https://api.gdeltproject.org/api/v2
    No API key required (public API)

    Provides real-time news monitoring with tone analysis.
    """

    DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
    GEO_API = "https://api.gdeltproject.org/api/v2/geo/geo"

    # Intelligence topics (from worldmonitor intel topics)
    INTEL_TOPICS = {
        "military": '(military exercise OR troop deployment OR airstrike OR "naval exercise")',
        "cyber": '(cyberattack OR ransomware OR hacking OR "data breach" OR APT)',
        "nuclear": '(nuclear OR uranium enrichment OR IAEA OR "nuclear weapon")',
        "sanctions": '(sanctions OR embargo OR "trade war" OR tariff)',
        "maritime": '(naval blockade OR piracy OR "strait of hormuz" OR warship)',
        "terrorism": '(terrorist attack OR bombing OR extremist OR jihad)',
    }

    def __init__(self):
        pass

    def search_documents(
        self,
        query: str,
        max_records: int = 20,
        timespan: str = "72h",
        sort: str = "DateDesc",
        tone_filter: Optional[str] = None,
    ) -> List[IntelligenceEvent]:
        """
        Search GDELT documents.

        Args:
            query: Search query (GDELT syntax)
            max_records: Maximum results (max 250)
            timespan: Time span (e.g., "24h", "72h", "1w")
            sort: Sort order (DateDesc, ToneDesc, etc.)
            tone_filter: Optional tone filter (e.g., "tone>5")

        Returns:
            List of IntelligenceEvent objects
        """
        cache_key = f"gdelt:doc:{hashlib.md5(query.encode()).hexdigest()[:8]}:{timespan}"
        if _cache.is_valid(cache_key):
            return _cache.get(cache_key)

        try:
            params = {
                "query": query,
                "mode": "ArtList",
                "maxrecords": min(max_records, 250),
                "timespan": timespan,
                "sort": sort,
                "format": "json",
            }

            if tone_filter:
                params["query"] += f" {tone_filter}"

            response = requests.get(self.DOC_API, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            events = []
            for article in data.get("articles", []):
                try:
                    # Parse GDELT date format: 20260111T093000Z
                    date_str = article.get("seendate", "")
                    if date_str:
                        timestamp = datetime.strptime(date_str, "%Y%m%dT%H%M%SZ")
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                    else:
                        timestamp = datetime.now(timezone.utc)

                    event = IntelligenceEvent(
                        event_id=hashlib.md5(article.get("url", "").encode()).hexdigest()[:12],
                        source="gdelt",
                        timestamp=timestamp,
                        title=article.get("title", ""),
                        description=None,
                        category=EventCategory.POLITICAL,
                        threat_level=classify_threat(article.get("title", "")),
                        url=article.get("url", ""),
                        tone=float(article.get("tone", 0)) if article.get("tone") else None,
                        source_domain=article.get("domain", ""),
                        raw_data=article,
                    )
                    events.append(event)
                except Exception as e:
                    logger.debug("Failed to parse GDELT article: %s", e)

            _cache.set(cache_key, events, CACHE_TTL["gdelt"])
            logger.info("GDELT returned %d articles for '%s'", len(events), query[:30])
            return events

        except Exception as e:
            logger.error("GDELT search failed: %s", e)
            return []

    def search_topic(
        self,
        topic: str,
        timespan: str = "24h",
        max_records: int = 20,
    ) -> List[IntelligenceEvent]:
        """
        Search for a predefined intelligence topic.

        Args:
            topic: Topic key (military, cyber, nuclear, etc.)
            timespan: Time span
            max_records: Maximum results

        Returns:
            List of IntelligenceEvent objects
        """
        query = self.INTEL_TOPICS.get(topic, topic)
        return self.search_documents(query, max_records, timespan)


class GDACSClient:
    """
    GDACS (Global Disaster Alert and Coordination System) client.

    API: https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP
    No API key required (public GeoJSON feed)

    Tracks: Earthquakes, Floods, Tropical Cyclones, Volcanoes, Wildfires, Droughts
    """

    API_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP"

    EVENT_TYPES = {
        "EQ": "Earthquake",
        "FL": "Flood",
        "TC": "Tropical Cyclone",
        "VO": "Volcano",
        "WF": "Wildfire",
        "DR": "Drought",
    }

    def __init__(self):
        pass

    def get_events(
        self,
        min_alert_level: str = "orange",
    ) -> List[DisasterEvent]:
        """
        Fetch disaster events from GDACS.

        Args:
            min_alert_level: Minimum alert level (red, orange, green)

        Returns:
            List of DisasterEvent objects
        """
        cache_key = f"gdacs:{min_alert_level}"
        if _cache.is_valid(cache_key):
            return _cache.get(cache_key)

        try:
            response = requests.get(self.API_URL, timeout=15)
            response.raise_for_status()
            data = response.json()

            # Alert level priority
            levels = {"red": 3, "orange": 2, "green": 1}
            min_level = levels.get(min_alert_level.lower(), 1)

            events = []
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                alert = props.get("alertlevel", "green").lower()

                # Filter by alert level
                if levels.get(alert, 0) < min_level:
                    continue

                try:
                    coords = feature.get("geometry", {}).get("coordinates", [0, 0])

                    # Parse date
                    date_str = props.get("fromdate", "")
                    if date_str:
                        timestamp = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        timestamp = datetime.now(timezone.utc)

                    event_type = props.get("eventtype", "")
                    disaster_name = self.EVENT_TYPES.get(event_type, event_type)

                    event = DisasterEvent(
                        event_id=str(props.get("eventid", "")),
                        source="gdacs",
                        timestamp=timestamp,
                        title=props.get("name", f"{disaster_name} Alert"),
                        description=props.get("description", ""),
                        category=EventCategory.DISASTER,
                        threat_level=ThreatLevel.HIGH if alert == "red" else ThreatLevel.MEDIUM,
                        latitude=float(coords[1]) if len(coords) > 1 else None,
                        longitude=float(coords[0]) if coords else None,
                        country=props.get("country", ""),
                        url=props.get("url", {}).get("report", ""),
                        disaster_type=disaster_name,
                        severity=alert,
                        raw_data=props,
                    )
                    events.append(event)
                except Exception as e:
                    logger.debug("Failed to parse GDACS event: %s", e)

            _cache.set(cache_key, events, CACHE_TTL["gdacs"])
            logger.info("Fetched %d GDACS events", len(events))
            return events

        except Exception as e:
            logger.error("GDACS query failed: %s", e)
            return []


class FIRMSClient:
    """
    NASA FIRMS (Fire Information for Resource Management System) client.

    API: https://firms.modaps.eosdis.nasa.gov/api
    Requires: NASA_FIRMS_API_KEY

    Provides near real-time fire detection via VIIRS satellite.
    """

    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
    SOURCE = "VIIRS_SNPP_NRT"

    # Monitored regions with bounding boxes (from worldmonitor)
    REGIONS = {
        "ukraine": {"name": "Ukraine", "west": 22.0, "south": 44.0, "east": 40.0, "north": 53.0},
        "israel_gaza": {"name": "Israel/Gaza", "west": 34.0, "south": 29.0, "east": 36.0, "north": 34.0},
        "iran": {"name": "Iran", "west": 44.0, "south": 25.0, "east": 63.0, "north": 40.0},
        "taiwan": {"name": "Taiwan", "west": 119.0, "south": 21.0, "east": 123.0, "north": 26.0},
        "north_korea": {"name": "North Korea", "west": 124.0, "south": 37.0, "east": 131.0, "north": 43.0},
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (
            api_key
            or os.getenv("NASA_FIRMS_API_KEY")
            or os.getenv("NASA_FIRMS_KEY")
        )

    def get_fires(
        self,
        region: Optional[str] = None,
        days: int = 1,
    ) -> List[DisasterEvent]:
        """
        Fetch fire detections.

        Args:
            region: Region key (ukraine, israel_gaza, etc.) or None for global
            days: Look back N days (1-10)

        Returns:
            List of DisasterEvent objects
        """
        if not self.api_key:
            logger.warning("NASA_FIRMS_API_KEY/NASA_FIRMS_KEY not set")
            return []

        days = max(1, min(days, 10))
        cache_key = f"firms:{region}:{days}"
        if _cache.is_valid(cache_key):
            return _cache.get(cache_key)

        regions_to_query = self.REGIONS
        if region:
            region_key = region.lower()
            if region_key not in self.REGIONS:
                logger.warning("Unknown FIRMS region '%s'", region)
                return []
            regions_to_query = {region_key: self.REGIONS[region_key]}

        events: List[DisasterEvent] = []
        for region_key, region_cfg in regions_to_query.items():
            bbox = ",".join(
                str(region_cfg[k]) for k in ("west", "south", "east", "north")
            )
            url = f"{self.BASE_URL}/{self.api_key}/{self.SOURCE}/{bbox}/{days}"
            try:
                response = requests.get(
                    url,
                    headers={"Accept": "text/csv"},
                    timeout=20,
                )
                response.raise_for_status()
            except Exception as e:
                logger.error("FIRMS request failed for %s: %s", region_key, e)
                continue

            events.extend(self._parse_firms_csv(response.text, region_cfg["name"]))

        _cache.set(cache_key, events, CACHE_TTL["firms"])
        logger.info("Fetched %d FIRMS fire detections", len(events))
        return events

    def _parse_firms_csv(self, csv_text: str, region_name: str) -> List[DisasterEvent]:
        """Parse FIRMS CSV into DisasterEvent objects."""
        if not csv_text.strip():
            return []

        events: List[DisasterEvent] = []
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            try:
                lat = float(row.get("latitude") or 0)
                lon = float(row.get("longitude") or 0)
                if lat == 0 and lon == 0:
                    continue

                acq_date = row.get("acq_date", "")
                acq_time = str(row.get("acq_time", "")).zfill(4)
                timestamp = datetime.strptime(
                    f"{acq_date} {acq_time}",
                    "%Y-%m-%d %H%M",
                ).replace(tzinfo=timezone.utc)

                brightness = float(row.get("bright_ti4") or row.get("brightness") or 0)
                confidence_raw = str(row.get("confidence", "")).strip()
                confidence_norm = confidence_raw.lower()
                if confidence_norm in {"h", "high"}:
                    severity = "high"
                    threat = ThreatLevel.HIGH
                elif confidence_norm in {"n", "nominal", "m", "medium"} or brightness >= 360:
                    severity = "medium"
                    threat = ThreatLevel.MEDIUM
                else:
                    severity = "low"
                    threat = ThreatLevel.LOW

                event = DisasterEvent(
                    event_id=hashlib.md5(
                        f"{lat}:{lon}:{acq_date}:{acq_time}:{region_name}".encode()
                    ).hexdigest()[:16],
                    source="firms",
                    timestamp=timestamp,
                    title=f"Satellite fire detection ({region_name})",
                    description=(
                        f"VIIRS hotspot detected. Brightness={brightness:.1f}K, "
                        f"confidence={confidence_raw or 'unknown'}."
                    ),
                    category=EventCategory.DISASTER,
                    threat_level=threat,
                    latitude=lat,
                    longitude=lon,
                    country=region_name,
                    disaster_type="wildfire",
                    severity=severity,
                    raw_data={**row, "region": region_name},
                )
                events.append(event)
            except Exception as e:
                logger.debug("Failed to parse FIRMS row: %s", e)

        return events


class OSINTAggregator:
    """
    Aggregates events from all OSINT sources.

    Provides unified interface for querying multiple intelligence sources
    and correlating events with prediction market timing.
    """

    def __init__(
        self,
        acled_token: Optional[str] = None,
        firms_key: Optional[str] = None,
    ):
        self.acled = ACLEDClient(acled_token)
        self.gdelt = GDELTClient()
        self.gdacs = GDACSClient()
        self.firms = FIRMSClient(firms_key)

    def search_all(
        self,
        query: str,
        days: int = 7,
        max_per_source: int = 20,
    ) -> List[OSINTEvent]:
        """
        Search all sources for a query.

        Args:
            query: Search query
            days: Look back N days
            max_per_source: Max results per source

        Returns:
            Combined list of events, sorted by timestamp
        """
        all_events: List[OSINTEvent] = []

        # GDELT (news)
        gdelt_events = self.gdelt.search_documents(
            query,
            max_records=max_per_source,
            timespan=f"{days * 24}h",
        )
        all_events.extend(gdelt_events)

        # ACLED (conflict events)
        acled_events = self.acled.get_events(days=days, limit=max_per_source * 5)
        all_events.extend([
            event for event in acled_events if self._event_matches_query(event, query)
        ][:max_per_source])

        # GDACS (disasters)
        gdacs_events = self.gdacs.get_events()
        all_events.extend([
            event for event in gdacs_events if self._event_matches_query(event, query)
        ][:max_per_source])

        # FIRMS (fire detections)
        firms_events = self.firms.get_fires(days=min(days, 10))
        all_events.extend([
            event for event in firms_events if self._event_matches_query(event, query)
        ][:max_per_source])

        # Sort by timestamp (most recent first)
        all_events.sort(key=lambda e: e.timestamp, reverse=True)

        return all_events[:max_per_source * 3]

    def get_events_in_window(
        self,
        start_time: datetime,
        end_time: datetime,
        categories: Optional[List[EventCategory]] = None,
    ) -> List[OSINTEvent]:
        """
        Get all events within a time window.

        Useful for temporal gap analysis in Sentinel.

        Args:
            start_time: Window start
            end_time: Window end
            categories: Filter by categories

        Returns:
            Events within the window
        """
        start_utc = self._to_utc(start_time)
        end_utc = self._to_utc(end_time)
        all_events: List[OSINTEvent] = []

        # GDELT (default search)
        days = max(1, (end_utc - start_utc).days + 1)
        gdelt_events = self.gdelt.search_documents(
            "*",  # All news
            max_records=100,
            timespan=f"{days * 24}h",
        )

        for event in gdelt_events:
            event_ts = self._to_utc(event.timestamp)
            if start_utc <= event_ts <= end_utc:
                if categories is None or event.category in categories:
                    all_events.append(event)

        # GDACS
        gdacs_events = self.gdacs.get_events()
        for event in gdacs_events:
            event_ts = self._to_utc(event.timestamp)
            if start_utc <= event_ts <= end_utc:
                if categories is None or event.category in categories:
                    all_events.append(event)

        # ACLED
        acled_events = self.acled.get_events(days=days, limit=500)
        for event in acled_events:
            event_ts = self._to_utc(event.timestamp)
            if start_utc <= event_ts <= end_utc:
                if categories is None or event.category in categories:
                    all_events.append(event)

        # FIRMS
        firms_events = self.firms.get_fires(days=min(days, 10))
        for event in firms_events:
            event_ts = self._to_utc(event.timestamp)
            if start_utc <= event_ts <= end_utc:
                if categories is None or event.category in categories:
                    all_events.append(event)

        # Sort by timestamp
        all_events.sort(key=lambda e: e.timestamp)

        return all_events

    def get_threat_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current threat levels across all sources.

        Returns:
            Summary dict with counts by threat level
        """
        all_events = []

        # Gather recent events
        all_events.extend(self.gdelt.search_topic("military", "24h", 50))
        all_events.extend(self.gdelt.search_topic("cyber", "24h", 30))
        all_events.extend(self.gdacs.get_events("orange"))

        # Count by threat level
        summary = {
            "total": len(all_events),
            "by_level": {},
            "by_category": {},
            "critical_events": [],
        }

        for event in all_events:
            level = event.threat_level.value
            summary["by_level"][level] = summary["by_level"].get(level, 0) + 1

            cat = event.category.value
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

            if event.threat_level == ThreatLevel.CRITICAL:
                summary["critical_events"].append({
                    "title": event.title,
                    "source": event.source,
                    "timestamp": event.timestamp.isoformat(),
                })

        return summary

    @staticmethod
    def _event_matches_query(event: OSINTEvent, query: str) -> bool:
        """Simple relevance filter for mixed-source search."""
        query_lower = query.lower().strip()
        if not query_lower or query_lower == "*":
            return True
        haystack = " ".join(
            [
                event.title or "",
                event.description or "",
                event.country or "",
                event.source or "",
            ]
        ).lower()
        return query_lower in haystack

    @staticmethod
    def _to_utc(value: datetime) -> datetime:
        """Normalize datetimes to UTC for safe comparisons."""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


if __name__ == "__main__":
    print("Testing OSINT Sources...")

    # Test GDELT (no API key needed)
    print("\n🌐 GDELT Test:")
    gdelt = GDELTClient()
    events = gdelt.search_documents("prediction market", max_records=5, timespan="72h")
    for event in events[:3]:
        print(f"  [{event.source}] {event.title[:60]}...")

    # Test GDELT topics
    print("\n🎯 GDELT Military Topic:")
    military_events = gdelt.search_topic("military", "24h", 5)
    for event in military_events[:3]:
        print(f"  [{event.threat_level.value}] {event.title[:60]}...")

    # Test GDACS (no API key needed)
    print("\n🌋 GDACS Test:")
    gdacs = GDACSClient()
    disasters = gdacs.get_events("orange")
    for event in disasters[:3]:
        print(f"  [{event.severity}] {event.disaster_type}: {event.title[:50]}...")

    # Test aggregator
    print("\n📊 Aggregator Test:")
    aggregator = OSINTAggregator()
    summary = aggregator.get_threat_summary()
    print(f"  Total events: {summary['total']}")
    print(f"  By level: {summary['by_level']}")
    print(f"  By category: {summary['by_category']}")
