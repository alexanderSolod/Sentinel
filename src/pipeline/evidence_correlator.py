"""
Live Evidence Correlator Pipeline

Streams trades, enriches each trade with wallet + cluster + OSINT evidence,
classifies the anomaly, and persists one normalized evidence packet per case.
"""
import asyncio
import copy
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from src.classification.pipeline import SentinelPipeline
from src.data.database import get_db, insert_evidence_packet, upsert_wallet
from src.data.websocket_handler import MockTradeStream, TradeEvent, TradeStreamHandler
from src.detection.cluster_analysis import SniperDetector
from src.detection.wallet_profiler import WalletProfiler
from src.osint.sources import OSINTAggregator, OSINTEvent

logger = logging.getLogger(__name__)


class EvidenceCorrelator:
    """
    Real-time trade evidence correlator.

    For each trade:
    1) enrich with wallet + cluster + OSINT context
    2) run AI classification pipeline
    3) persist normalized evidence packet per generated case
    """

    def __init__(
        self,
        *,
        db_path: Optional[str] = None,
        api_key: Optional[str] = None,
        acled_token: Optional[str] = None,
        firms_key: Optional[str] = None,
        wallet_profiler: Optional[WalletProfiler] = None,
        sniper_detector: Optional[SniperDetector] = None,
        osint_aggregator: Optional[OSINTAggregator] = None,
        classifier_pipeline: Optional[SentinelPipeline] = None,
    ) -> None:
        self.db_path = db_path
        self.wallet_profiler = wallet_profiler or WalletProfiler()
        self.sniper_detector = sniper_detector or SniperDetector()
        self.osint = osint_aggregator or OSINTAggregator(acled_token, firms_key)
        self.classifier = classifier_pipeline or SentinelPipeline(
            api_key=api_key,
            db_path=db_path,
            skip_low_suspicion=False,
        )
        self._market_first_seen: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def process_trade(
        self,
        trade: TradeEvent,
        osint_events_override: Optional[List[OSINTEvent]] = None,
    ) -> Dict[str, Any]:
        """Process one trade into a persisted evidence packet."""
        trade_ts = self._to_utc(trade.timestamp)
        wallet = trade.wallet_address.lower()
        market_id = trade.market_id
        market_name = trade.market_slug or market_id

        async with self._lock:
            self.wallet_profiler.record_trade(
                wallet_address=wallet,
                market_id=market_id,
                side=trade.side,
                outcome=trade.outcome or ("yes" if trade.side == "buy" else "no"),
                size=trade.notional_value,
                price=trade.price,
                timestamp=trade_ts,
            )
            profile = self.wallet_profiler.get_profile(wallet)
            if profile is None:
                raise RuntimeError(f"Profile missing for wallet {wallet}")
            risk_flags = list(self.wallet_profiler.calculate_risk_flags(wallet))
            profile_snapshot = copy.deepcopy(profile)

            market_created_at = self._resolve_market_created_at(trade, trade_ts)
            self.sniper_detector.record_entry(
                wallet_address=wallet,
                market_id=market_id,
                entry_timestamp=trade_ts,
                market_created_at=market_created_at,
                position_size=trade.notional_value,
            )
            self.sniper_detector.run_clustering()
            cluster_info = self.sniper_detector.get_cluster_for_wallet(wallet)
            cluster_id = cluster_info.cluster_id if cluster_info else None
            cluster_size = len(cluster_info.wallet_addresses) if cluster_info else 0
            cluster_confidence = self._estimate_cluster_confidence(cluster_size)
        if osint_events_override is not None:
            osint_events = osint_events_override
        else:
            osint_events = await asyncio.to_thread(self._fetch_osint_events, trade)

        nearest_event, gap_minutes = self._nearest_osint_event(osint_events, trade_ts)
        temporal_gap_score = self.compute_temporal_gap_score(gap_minutes)
        osint_signals_before_trade = self._count_pre_trade_events(osint_events, trade_ts)

        anomaly = self._build_anomaly_input(
            trade=trade,
            market_name=market_name,
            profile=profile_snapshot,
            gap_minutes=gap_minutes,
            osint_signals_before_trade=osint_signals_before_trade,
        )

        result = await asyncio.to_thread(self.classifier.process_anomaly, anomaly, True)
        correlation_score = self._compute_correlation_score(
            wallet_risk=profile_snapshot.risk_score,
            cluster_confidence=cluster_confidence,
            temporal_gap_score=temporal_gap_score,
        )

        packet = {
            "packet_id": result.case_id,
            "case_id": result.case_id,
            "event_id": result.event_id,
            "market_id": market_id,
            "market_name": market_name,
            "market_slug": trade.market_slug,
            "wallet_address": wallet,
            "trade_timestamp": trade_ts.isoformat(),
            "side": trade.side,
            "outcome": trade.outcome,
            "trade_size": float(trade.notional_value),
            "trade_price": float(trade.price),
            "wallet_age_hours": profile_snapshot.age_hours,
            "wallet_trade_count": profile_snapshot.total_trades,
            "wallet_win_rate": profile_snapshot.win_rate,
            "wallet_risk_score": profile_snapshot.risk_score,
            "is_fresh_wallet": int(self._is_fresh_wallet(profile_snapshot)),
            "cluster_id": cluster_id,
            "cluster_size": cluster_size,
            "cluster_confidence": cluster_confidence,
            "osint_event_id": nearest_event.event_id if nearest_event else None,
            "osint_source": nearest_event.source if nearest_event else None,
            "osint_title": nearest_event.title if nearest_event else None,
            "osint_timestamp": nearest_event.timestamp.isoformat() if nearest_event else None,
            "temporal_gap_minutes": gap_minutes,
            "temporal_gap_score": temporal_gap_score,
            "correlation_score": correlation_score,
            "evidence_json": json.dumps(
                {
                    "risk_flags": risk_flags,
                    "wallet_profile": self._json_safe(asdict(profile_snapshot)),
                    "cluster": {
                        "id": cluster_id,
                        "size": cluster_size,
                        "confidence": cluster_confidence,
                    },
                    "nearest_osint_event": self._serialize_osint_event(nearest_event),
                    "osint_event_count": len(osint_events),
                    "osint_signals_before_trade": osint_signals_before_trade,
                    "temporal_gap_minutes": gap_minutes,
                    "temporal_gap_score": temporal_gap_score,
                    "classification": {
                        "case_id": result.case_id,
                        "event_id": result.event_id,
                        "classification": result.classification,
                        "bss_score": result.bss_score,
                        "pes_score": result.pes_score,
                        "confidence": result.confidence,
                    },
                }
            ),
        }

        await asyncio.gather(
            asyncio.to_thread(self._persist_wallet_profile, profile_snapshot, cluster_id),
            asyncio.to_thread(self._persist_evidence_packet, packet),
        )
        logger.info(
            "Persisted evidence packet case_id=%s market=%s wallet=%s corr=%.2f",
            result.case_id,
            market_id,
            wallet[:10],
            correlation_score,
        )
        return packet

    async def run_live(
        self,
        *,
        event_filter: Optional[str] = None,
        market_filter: Optional[str] = None,
    ) -> None:
        """Run live WebSocket stream and process trades indefinitely."""
        handler = TradeStreamHandler(
            on_trade=self.process_trade,
            event_filter=event_filter,
            market_filter=market_filter,
        )
        await handler.start()

    async def run_mock(self, num_trades: int = 20, delay_seconds: float = 0.25) -> None:
        """Run mock stream for local demo/testing."""
        mock = MockTradeStream()

        async def on_trade(trade: TradeEvent) -> None:
            # Keep mock runs deterministic and local-only.
            await self.process_trade(trade, osint_events_override=[])

        mock.add_callback(on_trade)
        for i in range(num_trades):
            trade = mock.create_mock_trade(
                market_id=f"mock-market-{i % 3}",
                wallet=f"0x{i:040x}",
                side="buy" if i % 2 == 0 else "sell",
                price=0.45 + ((i % 5) * 0.05),
                size=500 + (i * 50),
            )
            await mock.emit_trade(trade)
            await asyncio.sleep(delay_seconds)

    def _fetch_osint_events(self, trade: TradeEvent) -> List[OSINTEvent]:
        """Fetch candidate OSINT events for the trade's market context."""
        query = (trade.market_slug or trade.market_id or "").replace("-", " ").strip()
        if not query:
            return []
        return self.osint.search_all(query=query, days=2, max_per_source=15)

    def _resolve_market_created_at(self, trade: TradeEvent, trade_ts: datetime) -> datetime:
        """Resolve best-known market creation time for sniper entry analysis."""
        raw = trade.raw_data.get("market_created_at") or trade.raw_data.get("market_creation_time")
        parsed = self._parse_datetime(raw)
        if parsed:
            created_at = self._to_utc(parsed)
            self._market_first_seen[trade.market_id] = created_at
            return created_at

        if trade.market_id not in self._market_first_seen:
            # Conservative fallback: market first seen 2 minutes before first trade.
            self._market_first_seen[trade.market_id] = trade_ts - timedelta(minutes=2)
        return self._market_first_seen[trade.market_id]

    def _build_anomaly_input(
        self,
        *,
        trade: TradeEvent,
        market_name: str,
        profile: Any,
        gap_minutes: Optional[float],
        osint_signals_before_trade: int,
    ) -> Dict[str, Any]:
        """Construct anomaly payload for AI classification pipeline."""
        hours_before_news = None
        if gap_minutes is not None:
            # Positive = trade after public signal, negative = before.
            hours_before_news = gap_minutes / 60.0

        trade_size = float(trade.notional_value)

        return {
            "market_id": trade.market_id,
            "market_name": market_name,
            "wallet_address": trade.wallet_address,
            "wallet_age_days": (profile.age_hours or 0) / 24.0,
            "wallet_trades": profile.total_trades,
            "win_rate": profile.win_rate if profile.win_rate is not None else 0.5,
            "trade_size": trade_size,
            "price_before": float(trade.price),
            "price_after": float(trade.price),
            "position_side": (trade.outcome or "yes").upper(),
            "z_score": self._estimate_trade_z_score(trade_size, profile),
            "trade_timestamp": self._to_utc(trade.timestamp).isoformat(),
            "timestamp": self._to_utc(trade.timestamp).isoformat(),
            "hours_before_news": hours_before_news,
            "osint_signals_before_trade": osint_signals_before_trade,
            "volume_24h": float(trade.notional_value),
        }

    @staticmethod
    def _estimate_trade_z_score(trade_size: float, profile: Any) -> float:
        """Estimate a simple anomaly score from trade size vs wallet baseline."""
        avg_trade_size = getattr(profile, "avg_trade_size", None)
        if avg_trade_size is None:
            return 1.0

        try:
            baseline = float(avg_trade_size)
        except (TypeError, ValueError):
            return 1.0

        if baseline <= 0:
            return 1.0

        deviation = abs(trade_size - baseline) / baseline
        return round(min(8.0, 1.0 + deviation * 1.5), 3)

    def _persist_wallet_profile(self, profile: Any, cluster_id: Optional[str]) -> None:
        """Persist wallet profile snapshot to DB."""
        funding_chain_json = None
        if profile.funding_chain:
            funding_chain_json = json.dumps(self._json_safe(asdict(profile.funding_chain)))

        with self._db_context() as conn:
            upsert_wallet(
                conn,
                {
                    "address": profile.address,
                    "first_seen": profile.first_seen.isoformat() if profile.first_seen else None,
                    "last_seen": profile.last_seen.isoformat() if profile.last_seen else None,
                    "trade_count": profile.total_trades,
                    "win_count": profile.win_count,
                    "loss_count": profile.loss_count,
                    "win_rate": profile.win_rate,
                    "total_volume": float(profile.total_volume),
                    "avg_position_size": float(profile.avg_trade_size) if profile.avg_trade_size else None,
                    "is_fresh_wallet": int(self._is_fresh_wallet(profile)),
                    "cluster_id": cluster_id,
                    "funding_chain": funding_chain_json,
                    "suspicious_flags": json.dumps(profile.risk_flags),
                },
            )

    def _persist_evidence_packet(self, packet: Dict[str, Any]) -> None:
        with self._db_context() as conn:
            insert_evidence_packet(conn, packet)

    @staticmethod
    def compute_temporal_gap_score(gap_minutes: Optional[float]) -> float:
        """
        Compute temporal suspicion score from trade-vs-public-signal gap.

        Higher means more suspicious.
        """
        if gap_minutes is None:
            return 1.0

        if gap_minutes < 0:
            # Trade happened before public signal -> suspicious.
            return round(min(1.0, 0.6 + min(abs(gap_minutes), 360.0) / 360.0 * 0.4), 3)

        if gap_minutes <= 10:
            return 0.2
        if gap_minutes <= 60:
            return 0.1
        return 0.05

    @staticmethod
    def _compute_correlation_score(
        *,
        wallet_risk: float,
        cluster_confidence: float,
        temporal_gap_score: float,
    ) -> float:
        wallet_component = max(0.0, min(wallet_risk, 1.0))
        cluster_component = max(0.0, min(cluster_confidence, 1.0))
        temporal_component = max(0.0, min(temporal_gap_score, 1.0))
        score = 0.4 * wallet_component + 0.3 * cluster_component + 0.3 * temporal_component
        return round(min(score, 1.0), 3)

    @staticmethod
    def _estimate_cluster_confidence(cluster_size: int) -> float:
        if cluster_size <= 1:
            return 0.0
        return round(min(cluster_size / 10.0, 0.9), 3)

    @staticmethod
    def _count_pre_trade_events(events: List[OSINTEvent], trade_ts: datetime) -> int:
        return sum(1 for event in events if EvidenceCorrelator._to_utc(event.timestamp) <= trade_ts)

    @staticmethod
    def _nearest_osint_event(
        events: List[OSINTEvent],
        trade_ts: datetime,
    ) -> Tuple[Optional[OSINTEvent], Optional[float]]:
        if not events:
            return None, None

        def key(event: OSINTEvent) -> float:
            return abs((trade_ts - EvidenceCorrelator._to_utc(event.timestamp)).total_seconds())

        nearest = min(events, key=key)
        gap_minutes = (trade_ts - EvidenceCorrelator._to_utc(nearest.timestamp)).total_seconds() / 60.0
        return nearest, round(gap_minutes, 3)

    @staticmethod
    def _is_fresh_wallet(profile: Any) -> bool:
        age_hours = profile.age_hours or 0.0
        return profile.total_trades <= 5 and age_hours <= 24.0 * 7

    @staticmethod
    def _serialize_osint_event(event: Optional[OSINTEvent]) -> Optional[Dict[str, Any]]:
        if event is None:
            return None
        return {
            "event_id": event.event_id,
            "source": event.source,
            "title": event.title,
            "timestamp": event.timestamp.isoformat(),
            "category": event.category.value,
            "threat_level": event.threat_level.value,
            "country": event.country,
            "url": event.url,
        }

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    @staticmethod
    def _to_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _json_safe(value: Any) -> Any:
        """Convert dataclass dicts with Decimal/datetime values to JSON-safe values."""
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: EvidenceCorrelator._json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [EvidenceCorrelator._json_safe(v) for v in value]
        return value

    def _db_context(self):
        if self.db_path:
            return get_db(self.db_path)
        return get_db()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    correlator = EvidenceCorrelator()
    asyncio.run(correlator.run_mock(num_trades=10, delay_seconds=0.1))
    logger.info("Mock live evidence correlation complete")
