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

import numpy as np

from src.classification.pipeline import SentinelPipeline
from src.data.fusion_engine import DataFusionEngine, DataSourceType, FusedDataPoint
from src.data.database import get_db, insert_evidence_packet, upsert_wallet
from src.detection.autoencoder import TradingAutoencoder
from src.data.websocket_handler import MockTradeStream, TradeEvent, TradeStreamHandler
from src.detection.fp_gate import FalsePositiveGate
from src.detection.streaming_detector import StreamingAnomalyDetector
from src.detection.cluster_analysis import SniperDetector
from src.detection.wallet_profiler import WalletProfiler
from src.osint.sources import OSINTAggregator, OSINTEvent
from src.osint.text_analyzer import OSINTTextAnalyzer

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
        self.streaming_detector = StreamingAnomalyDetector()
        self.fusion_engine = DataFusionEngine(window_hours=72)
        self.text_analyzer = OSINTTextAnalyzer()
        self.fp_gate = FalsePositiveGate()
        self.autoencoder = TradingAutoencoder(input_dim=8, encoding_dim=4, learning_rate=0.002)
        self._autoencoder_buffer: List[List[float]] = []
        self._autoencoder_min_samples = 64
        self._autoencoder_max_samples = 2000
        self._autoencoder_new_since_train = 0
        self._autoencoder_retrain_every = 200
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

        streaming_result = self.streaming_detector.process_trade(
            {
                "market_id": market_id,
                "amount_usd": float(trade.notional_value),
                "price": float(trade.price),
                "timestamp": trade_ts,
            }
        )
        self.fusion_engine.ingest(
            FusedDataPoint(
                timestamp=trade_ts,
                source_type=DataSourceType.POLYMARKET_TRADE,
                market_id=market_id,
                wallet_address=wallet,
                trade_amount_usd=float(trade.notional_value),
                trade_direction=trade.side,
                price_after=float(trade.price),
            )
        )
        if osint_events_override is not None:
            osint_events = osint_events_override
        else:
            osint_events = await asyncio.to_thread(self._fetch_osint_events, trade)

        nlp_relevance = self._analyze_osint_relevance(osint_events, market_name)
        relevant_event_ids = {
            r["event_id"] for r in nlp_relevance if r.get("composite_relevance", 0.0) >= 0.2
        }
        relevant_osint_events = [
            event for event in osint_events if event.event_id in relevant_event_ids
        ] or osint_events

        for event in relevant_osint_events:
            self.fusion_engine.ingest(
                FusedDataPoint(
                    timestamp=self._to_utc(event.timestamp),
                    source_type=self._map_osint_source(event.source),
                    market_id=market_id,
                    osint_headline=event.title,
                    osint_source=event.source,
                    osint_severity=getattr(event.threat_level, "value", "INFO"),
                    raw_data=self._serialize_osint_event(event),
                )
            )

        nearest_event, gap_minutes = self._nearest_osint_event(relevant_osint_events, trade_ts)
        temporal_gap_score = self.compute_temporal_gap_score(gap_minutes)
        osint_signals_before_trade = self._count_pre_trade_events(relevant_osint_events, trade_ts)
        fusion_signals = self.fusion_engine.compute_cross_source_signals(market_id)

        anomaly = self._build_anomaly_input(
            trade=trade,
            market_name=market_name,
            profile=profile_snapshot,
            gap_minutes=gap_minutes,
            osint_signals_before_trade=osint_signals_before_trade,
            streaming_result=streaming_result,
            fusion_signals=fusion_signals,
            nlp_relevance=nlp_relevance,
        )

        result = await asyncio.to_thread(self.classifier.process_anomaly, anomaly, True)
        research = result.analysis.get("research_signals", {})
        rf_score = float(research.get("rf_analysis", {}).get("rf_score", 0.0) or 0.0)
        gt_score = float(
            research.get("game_theory_analysis", {}).get("game_theory_suspicion_score", 0.0) or 0.0
        )
        autoencoder_input = self._build_autoencoder_vector(
            trade=trade,
            profile=profile_snapshot,
            streaming_result=streaming_result,
            fusion_signals=fusion_signals,
            osint_signals_before_trade=osint_signals_before_trade,
        )
        autoencoder_result = self._score_autoencoder(
            vector=autoencoder_input,
            rf_score=rf_score,
            gt_score=gt_score,
        )
        gate_result = self.fp_gate.evaluate(
            trade=anomaly,
            features={
                "statistical_score": streaming_result.get("score", 0.0),
                "rf_score": rf_score,
                "autoencoder_score": autoencoder_result["normalized_score"],
                "game_theory_score": gt_score,
                "bss_score": result.bss_score,
            },
        )

        top_relevance = max((r.get("composite_relevance", 0.0) for r in nlp_relevance), default=0.0)
        correlation_score = self._compute_correlation_score(
            wallet_risk=profile_snapshot.risk_score,
            cluster_confidence=cluster_confidence,
            temporal_gap_score=temporal_gap_score,
            nlp_relevance=top_relevance,
            statistical_score=streaming_result.get("score", 0.0),
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
                    "streaming_anomaly": streaming_result,
                    "autoencoder": autoencoder_result,
                    "fusion_signals": fusion_signals,
                    "cluster": {
                        "id": cluster_id,
                        "size": cluster_size,
                        "confidence": cluster_confidence,
                    },
                    "nearest_osint_event": self._serialize_osint_event(nearest_event),
                    "osint_event_count": len(relevant_osint_events),
                    "osint_signals_before_trade": osint_signals_before_trade,
                    "temporal_gap_minutes": gap_minutes,
                    "temporal_gap_score": temporal_gap_score,
                    "nlp_relevance": nlp_relevance[:10],
                    "gate_evaluation": gate_result,
                    "classification": {
                        "case_id": result.case_id,
                        "event_id": result.event_id,
                        "classification": result.classification,
                        "bss_score": result.bss_score,
                        "pes_score": result.pes_score,
                        "confidence": result.confidence,
                        "rf_score": rf_score,
                        "game_theory_score": gt_score,
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

    def _analyze_osint_relevance(
        self,
        events: List[OSINTEvent],
        market_name: str,
    ) -> List[Dict[str, Any]]:
        market_keywords = self.text_analyzer.extract_keywords(market_name, top_n=15)
        analyses: List[Dict[str, Any]] = []

        for event in events:
            text = f"{event.title} {event.description or ''}".strip()
            relevance = self.text_analyzer.compute_relevance_score(
                osint_text=text,
                market_description=market_name,
                market_keywords=market_keywords,
            )
            analyses.append(
                {
                    "event_id": event.event_id,
                    "source": event.source,
                    "title": event.title,
                    "timestamp": self._to_utc(event.timestamp).isoformat(),
                    **relevance,
                }
            )

        analyses.sort(key=lambda x: x.get("composite_relevance", 0.0), reverse=True)
        return analyses

    @staticmethod
    def _map_osint_source(source: str) -> DataSourceType:
        s = str(source or "").lower()
        if "rss" in s:
            return DataSourceType.OSINT_RSS
        if "gdelt" in s:
            return DataSourceType.OSINT_GDELT
        if "gdacs" in s:
            return DataSourceType.OSINT_GDACS
        if "acled" in s:
            return DataSourceType.OSINT_ACLED
        if "firms" in s or "nasa" in s:
            return DataSourceType.OSINT_FIRMS
        return DataSourceType.OSINT_RSS

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
        streaming_result: Optional[Dict[str, Any]] = None,
        fusion_signals: Optional[Dict[str, float]] = None,
        nlp_relevance: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Construct anomaly payload for AI classification pipeline."""
        hours_before_news = None
        if gap_minutes is not None:
            # Positive = trade after public signal, negative = before.
            hours_before_news = gap_minutes / 60.0

        trade_size = float(trade.notional_value)
        streaming_result = streaming_result or {}
        fusion_signals = fusion_signals or {}
        nlp_relevance = nlp_relevance or []

        z_score_est = self._estimate_trade_z_score(trade_size, profile)
        if streaming_result.get("volume_z") is not None:
            z_score_est = max(z_score_est, float(streaming_result.get("volume_z") or 0.0))

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
            "z_score": round(z_score_est, 3),
            "trade_timestamp": self._to_utc(trade.timestamp).isoformat(),
            "timestamp": self._to_utc(trade.timestamp).isoformat(),
            "hours_before_news": hours_before_news,
            "osint_signals_before_trade": osint_signals_before_trade,
            "volume_24h": float(trade.notional_value),
            "market_volume_24h": float(trade.notional_value),
            "streaming_signals": streaming_result,
            "fusion_signals": fusion_signals,
            "nlp_top_relevance": max((r.get("composite_relevance", 0.0) for r in nlp_relevance), default=0.0),
            "nlp_relevance_details": nlp_relevance[:10],
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

    def _build_autoencoder_vector(
        self,
        *,
        trade: TradeEvent,
        profile: Any,
        streaming_result: Dict[str, Any],
        fusion_signals: Dict[str, float],
        osint_signals_before_trade: int,
    ) -> List[float]:
        trade_size = float(trade.notional_value or 0.0)
        avg_trade_size = getattr(profile, "avg_trade_size", None)
        try:
            baseline = float(avg_trade_size) if avg_trade_size is not None else trade_size
        except (TypeError, ValueError):
            baseline = trade_size
        baseline = max(1.0, baseline)
        size_ratio = trade_size / baseline

        volume_z = float(streaming_result.get("volume_z", 0.0) or 0.0)
        price_move = float(streaming_result.get("price_move", 0.0) or 0.0)
        interval_z = float(streaming_result.get("interval_z", 0.0) or 0.0)
        top_wallet_concentration = float(fusion_signals.get("top_wallet_concentration", 0.0) or 0.0)
        osint_count = float(fusion_signals.get("osint_event_count", osint_signals_before_trade) or 0.0)
        win_rate = float(getattr(profile, "win_rate", 0.5) or 0.5)

        # Autoencoder output layer is sigmoid, so keep feature values in [0, 1].
        return [
            min(1.0, np.log1p(max(trade_size, 0.0)) / 12.0),
            min(1.0, np.log1p(max(size_ratio, 0.0)) / 4.0),
            min(1.0, max(0.0, volume_z) / 6.0),
            min(1.0, max(0.0, price_move) / 0.3),
            min(1.0, max(0.0, interval_z) / 6.0),
            min(1.0, max(0.0, top_wallet_concentration)),
            min(1.0, max(0.0, osint_count) / 10.0),
            min(1.0, max(0.0, win_rate)),
        ]

    def _score_autoencoder(
        self,
        *,
        vector: List[float],
        rf_score: float,
        gt_score: float,
    ) -> Dict[str, Any]:
        vector_arr = np.asarray(vector, dtype=float).reshape(1, -1)

        # Build a mostly-legitimate baseline to avoid learning suspicious regimes.
        likely_legit = rf_score < 0.5 and gt_score < 50.0
        if likely_legit or len(self._autoencoder_buffer) < self._autoencoder_min_samples:
            self._autoencoder_buffer.append(vector)
            if len(self._autoencoder_buffer) > self._autoencoder_max_samples:
                self._autoencoder_buffer = self._autoencoder_buffer[-self._autoencoder_max_samples :]
            self._autoencoder_new_since_train += 1

        if len(self._autoencoder_buffer) >= self._autoencoder_min_samples:
            needs_initial_fit = not self.autoencoder.is_fitted
            needs_refresh = self._autoencoder_new_since_train >= self._autoencoder_retrain_every
            if needs_initial_fit or needs_refresh:
                baseline = np.asarray(self._autoencoder_buffer, dtype=float)
                self.autoencoder.train(baseline, epochs=40, batch_size=16, percentile_threshold=95)
                self._autoencoder_new_since_train = 0

        if not self.autoencoder.is_fitted:
            return {
                "fitted": False,
                "normalized_score": 0.5,
                "raw_score": None,
                "threshold": None,
            }

        scored = self.autoencoder.score_anomaly(vector_arr)
        raw_score = float(scored["anomaly_scores"][0])
        normalized = max(0.0, min(1.0, raw_score / 2.0))
        return {
            "fitted": True,
            "normalized_score": round(normalized, 4),
            "raw_score": round(raw_score, 4),
            "threshold": round(float(scored["threshold"]), 8),
            "is_anomalous": bool(scored["is_anomalous"][0]),
        }

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
        nlp_relevance: float = 0.0,
        statistical_score: float = 0.0,
    ) -> float:
        wallet_component = max(0.0, min(wallet_risk, 1.0))
        cluster_component = max(0.0, min(cluster_confidence, 1.0))
        temporal_component = max(0.0, min(temporal_gap_score, 1.0))
        nlp_component = max(0.0, min(nlp_relevance, 1.0))
        statistical_component = max(0.0, min(statistical_score, 1.0))
        score = (
            0.30 * wallet_component
            + 0.20 * cluster_component
            + 0.25 * temporal_component
            + 0.15 * nlp_component
            + 0.10 * statistical_component
        )
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
