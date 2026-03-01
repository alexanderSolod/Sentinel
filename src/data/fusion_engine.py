"""Data fusion engine for cross-source market timelines."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


class DataSourceType(Enum):
    POLYMARKET_TRADE = "polymarket_trade"
    POLYMARKET_PRICE = "polymarket_price"
    OSINT_RSS = "osint_rss"
    OSINT_GDELT = "osint_gdelt"
    OSINT_GDACS = "osint_gdacs"
    OSINT_ACLED = "osint_acled"
    OSINT_FIRMS = "osint_firms"
    WALLET_PROFILE = "wallet_profile"
    CLUSTER_ANALYSIS = "cluster_analysis"
    ARENA_VOTE = "arena_vote"


@dataclass
class FusedDataPoint:
    timestamp: datetime
    source_type: DataSourceType
    market_id: Optional[str] = None
    wallet_address: Optional[str] = None
    trade_amount_usd: Optional[float] = None
    trade_direction: Optional[str] = None
    price_before: Optional[float] = None
    price_after: Optional[float] = None
    osint_headline: Optional[str] = None
    osint_source: Optional[str] = None
    osint_severity: Optional[str] = None
    osint_keywords: List[str] = field(default_factory=list)
    volume_z_score: Optional[float] = None
    price_move_pct: Optional[float] = None
    temporal_gap_hours: Optional[float] = None
    raw_data: Optional[dict] = None


class DataFusionEngine:
    """Rolling event-buffer fusion to compute cross-source signals."""

    def __init__(self, window_hours: int = 72) -> None:
        self.window_hours = window_hours
        self.event_buffer: Dict[str, List[FusedDataPoint]] = {}

    def ingest(self, data_point: FusedDataPoint) -> None:
        if not data_point.market_id:
            return

        if data_point.market_id not in self.event_buffer:
            self.event_buffer[data_point.market_id] = []

        self.event_buffer[data_point.market_id].append(data_point)
        self._prune_old_events(data_point.market_id)

    def get_market_timeline(self, market_id: str) -> List[FusedDataPoint]:
        return sorted(self.event_buffer.get(market_id, []), key=lambda e: e.timestamp)

    def compute_cross_source_signals(self, market_id: str) -> Dict[str, float]:
        timeline = self.get_market_timeline(market_id)
        if not timeline:
            return {}

        trades = [e for e in timeline if e.source_type == DataSourceType.POLYMARKET_TRADE]
        osint = [e for e in timeline if e.source_type.value.startswith("osint")]

        signals: Dict[str, float] = {}

        if trades and osint:
            earliest_osint = min(e.timestamp for e in osint)
            trades_before = [t for t in trades if t.timestamp < earliest_osint]
            signals["trades_before_osint_pct"] = len(trades_before) / max(len(trades), 1)
            if trades_before:
                earliest_trade = min(t.timestamp for t in trades)
                signals["earliest_osint_gap_hours"] = max(
                    0.0,
                    (earliest_osint - earliest_trade).total_seconds() / 3600.0,
                )
            else:
                signals["earliest_osint_gap_hours"] = 0.0

        if len(trades) >= 5:
            volumes = [float(t.trade_amount_usd or 0.0) for t in trades]
            half = len(volumes) // 2
            first_half_avg = sum(volumes[:half]) / max(half, 1)
            second_half_avg = sum(volumes[half:]) / max(len(volumes) - half, 1)
            signals["volume_acceleration"] = second_half_avg / max(first_half_avg, 1.0)

        wallets = {t.wallet_address for t in trades if t.wallet_address}
        signals["unique_wallets"] = float(len(wallets))
        if trades and wallets:
            top_wallet_trades = max(sum(1 for t in trades if t.wallet_address == w) for w in wallets)
            signals["top_wallet_concentration"] = top_wallet_trades / len(trades)

        severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
        if osint:
            severities = [severity_order.get((e.osint_severity or "INFO").upper(), 0) for e in osint]
            signals["max_osint_severity"] = float(max(severities))
            signals["osint_event_count"] = float(len(osint))

        return signals

    def _prune_old_events(self, market_id: str) -> None:
        cutoff = datetime.utcnow() - timedelta(hours=self.window_hours)
        self.event_buffer[market_id] = [
            e for e in self.event_buffer[market_id]
            if e.timestamp.replace(tzinfo=None) > cutoff
        ]
