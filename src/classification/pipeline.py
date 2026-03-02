"""
Sentinel Classification Pipeline Orchestrator
Wires together Stage 1 (Triage) → Stage 2 (Magistral) → Stage 3 (SAR)

This module provides the main entry point for classifying anomalies
and generating reports for the Sentinel Index.
"""
import os
import uuid
import json
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    import weave
    _has_weave = True
except Exception:
    _has_weave = False

from src.classification.stage1_triage import classify_anomaly, TriageResult
from src.classification.stage2_magistral import analyze_case, MagistralResult
from src.classification.stage3_sar import generate_sar, SARReport
from src.detection.features import FeatureExtractor
from src.detection.rf_classifier import RFClassifier
from src.detection.game_theory import GameTheoryEngine
from src.data.database import (
    get_connection,
    insert_anomaly,
    insert_case,
    get_osint_events_in_range,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Complete result from the classification pipeline."""
    case_id: str
    event_id: str
    classification: str
    bss_score: int
    pes_score: int
    confidence: float
    triage: Dict[str, Any]
    analysis: Dict[str, Any]
    sar_report: Optional[str]
    created_at: str


class SentinelPipeline:
    """
    Main classification pipeline orchestrator.

    Processes anomalies through:
    1. Stage 1: Fast triage classification
    2. Stage 2: Deep analysis (for INSIDER/OSINT_EDGE cases)
    3. Stage 3: SAR generation

    Results are stored in the database and Sentinel Index.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        skip_low_suspicion: bool = True,
        suspicion_threshold: int = 40,
        db_path: Optional[str] = None,
        enable_rf_gate: bool = True,
        rf_gate_threshold: float = 0.15,
    ):
        """
        Initialize the pipeline.

        Args:
            api_key: Mistral API key (uses env var if not provided)
            skip_low_suspicion: Skip Stage 2/3 for low-suspicion cases
            suspicion_threshold: BSS threshold for deep analysis
            db_path: Database path (uses default if not provided)
            enable_rf_gate: Enable early dismissal for low RF/game-theory cases
            rf_gate_threshold: RF score below this can trigger early dismissal
        """
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.skip_low_suspicion = skip_low_suspicion
        self.suspicion_threshold = suspicion_threshold
        self.db_path = db_path
        self.enable_rf_gate = enable_rf_gate
        self.rf_gate_threshold = rf_gate_threshold
        self.feature_extractor = FeatureExtractor()
        self.rf_classifier = RFClassifier()
        self.game_theory_engine = GameTheoryEngine()
        self._osint_cache: Dict[str, List[Dict]] = {}  # keyed by "start|end"

        # Initialize W&B Weave tracing if available and configured
        if _has_weave and os.getenv("WANDB_API_KEY"):
            try:
                weave.init("sentinel")
                logger.info("W&B Weave tracing initialized (project: sentinel)")
            except Exception as e:
                logger.debug("W&B Weave not initialized: %s", e)

    @(weave.op() if _has_weave else lambda f: f)
    def process_anomaly(
        self,
        anomaly: Dict[str, Any],
        save_to_db: bool = True
    ) -> PipelineResult:
        """
        Process a single anomaly through the full pipeline.

        Args:
            anomaly: Anomaly event data with:
                - market_id, market_name
                - wallet_address, wallet_age_days, wallet_trades
                - trade_size, price_before, price_after
                - z_score
                - timestamp or trade_timestamp
            save_to_db: Whether to save results to database

        Returns:
            PipelineResult with all classification data
        """
        # Generate IDs
        anomaly = self._normalize_anomaly_input(anomaly)
        event_id = anomaly.get("event_id", f"EVENT-{str(uuid.uuid4())[:8]}")
        case_id = f"CASE-{str(uuid.uuid4())[:8]}"
        anomaly["event_id"] = event_id

        # Ensure DB-required timestamp field is always present.
        if not anomaly.get("timestamp"):
            anomaly["timestamp"] = anomaly.get("trade_timestamp") or datetime.now(timezone.utc).isoformat()

        logger.info("Processing anomaly: %s", event_id)

        # ============================================
        # Feature Extraction
        # ============================================
        features = self.feature_extractor.extract(anomaly)
        logger.info(
            "Features: suspicion=%d fresh=%d cluster=%d sniper=%d",
            features.suspicion_heuristic,
            features.is_fresh_wallet,
            features.cluster_member,
            features.is_sniper,
        )

        # ============================================
        # Research Models: RF + Game Theory
        # ============================================
        rf_result = self.rf_classifier.predict(features)
        gt_analysis = self.game_theory_engine.analyze(
            anomaly=anomaly,
            feature_vector=features,
            wallet_trades=anomaly.get("wallet_trade_history"),
        )
        anomaly["rf_analysis"] = rf_result
        anomaly["game_theory_analysis"] = gt_analysis.to_dict()

        logger.info(
            "Research signals: rf_score=%.3f rf_source=%s gt_score=%.1f",
            rf_result.get("rf_score", 0.0),
            rf_result.get("source", "unknown"),
            gt_analysis.game_theory_suspicion_score,
        )

        # ============================================
        # Stage 1: Fast Triage
        # ============================================
        logger.info("Stage 1: Triage classification")
        triage_input = features.to_classifier_input()
        triage_input.update(
            {
                "rf_suspicion_score": rf_result.get("rf_score"),
                "rf_top_features": rf_result.get("top_features", []),
                "game_theory_score": gt_analysis.game_theory_suspicion_score,
                "best_fit_player_type": gt_analysis.best_fit_type,
                "entropy_anomaly": gt_analysis.entropy_anomaly,
                "pattern_confidence": gt_analysis.pattern_confidence,
            }
        )

        # Optional fast dismissal gate for obvious low-risk cases.
        gated_low_risk = (
            self.enable_rf_gate
            and self.skip_low_suspicion
            and rf_result.get("rf_score", 1.0) < self.rf_gate_threshold
            and gt_analysis.game_theory_suspicion_score < 20
            and features.suspicion_heuristic < 20
        )

        if gated_low_risk:
            triage_result = TriageResult(
                classification="SPECULATOR",
                bss_score=10,
                pes_score=85,
                confidence=0.95,
                reasoning=(
                    "Low-risk early dismissal: RF and game-theory scores are both low, "
                    "with no suspicious behavioral indicators."
                ),
            )
        else:
            triage_result = classify_anomaly(triage_input, api_key=self.api_key)

        logger.info(
            "Stage 1 result: classification=%s bss=%d pes=%d",
            triage_result.classification,
            triage_result.bss_score,
            triage_result.pes_score,
        )

        # Load OSINT context once for downstream stages and evidence packaging.
        osint_context = self._get_osint_context(anomaly)

        # Check if we should proceed to Stage 2
        needs_deep_analysis = (
            triage_result.classification in ["INSIDER", "OSINT_EDGE"]
            or triage_result.bss_score >= self.suspicion_threshold
        )

        # ============================================
        # Stage 2: Deep Analysis (conditional)
        # ============================================
        if needs_deep_analysis or not self.skip_low_suspicion:
            logger.info("Stage 2: Deep analysis")

            triage_dict = {
                "classification": triage_result.classification,
                "bss_score": triage_result.bss_score,
                "pes_score": triage_result.pes_score,
                "confidence": triage_result.confidence,
                "reasoning": triage_result.reasoning,
                "rf_suspicion_score": rf_result.get("rf_score"),
                "game_theory_score": gt_analysis.game_theory_suspicion_score,
            }

            magistral_result = analyze_case(
                anomaly,
                triage_dict,
                osint_context,
                api_key=self.api_key
            )
            logger.info("Stage 2 complete")
        else:
            logger.info("Stage 2 skipped (low suspicion)")
            magistral_result = MagistralResult(
                classification=triage_result.classification,
                confidence=triage_result.confidence,
                xai_narrative=triage_result.reasoning,
                fraud_triangle={"pressure": "N/A", "opportunity": "N/A", "rationalization": "N/A"},
                temporal_analysis="Not analyzed",
                evidence_summary=["Low suspicion case - deep analysis skipped"],
                recommendation="No further action"
            )

        # ============================================
        # Stage 3: SAR Generation (conditional)
        # ============================================
        if triage_result.classification == "INSIDER" or triage_result.bss_score >= 60:
            logger.info("Stage 3: Generating SAR")

            triage_dict = {
                "classification": triage_result.classification,
                "bss_score": triage_result.bss_score,
                "pes_score": triage_result.pes_score,
                "confidence": triage_result.confidence,
            }

            magistral_dict = {
                "xai_narrative": magistral_result.xai_narrative,
                "fraud_triangle": magistral_result.fraud_triangle,
            }

            sar_report = generate_sar(
                anomaly,
                triage_dict,
                magistral_dict,
                case_id,
                api_key=self.api_key
            )
            sar_text = sar_report.full_report
            logger.info("Stage 3 complete: severity=%s", sar_report.severity)
        else:
            logger.info("Stage 3 skipped (not flagged)")
            sar_text = None

        # ============================================
        # Build Result
        # ============================================
        result = PipelineResult(
            case_id=case_id,
            event_id=event_id,
            classification=triage_result.classification,
            bss_score=triage_result.bss_score,
            pes_score=triage_result.pes_score,
            confidence=triage_result.confidence,
            triage={
                "classification": triage_result.classification,
                "bss_score": triage_result.bss_score,
                "pes_score": triage_result.pes_score,
                "confidence": triage_result.confidence,
                "reasoning": triage_result.reasoning,
                "rf_suspicion_score": rf_result.get("rf_score"),
                "game_theory_score": gt_analysis.game_theory_suspicion_score,
                "gated_low_risk": gated_low_risk,
            },
            analysis={
                "xai_narrative": magistral_result.xai_narrative,
                "fraud_triangle": magistral_result.fraud_triangle,
                "temporal_analysis": magistral_result.temporal_analysis,
                "evidence_summary": magistral_result.evidence_summary,
                "recommendation": magistral_result.recommendation,
                "research_signals": {
                    "rf_analysis": rf_result,
                    "game_theory_analysis": gt_analysis.to_dict(),
                },
                "osint_context_count": len(osint_context),
            },
            sar_report=sar_text,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # ============================================
        # Save to Database
        # ============================================
        if save_to_db:
            self._save_to_db(anomaly, result, magistral_result, osint_context=osint_context)

        logger.info("Pipeline complete: %s", case_id)
        return result

    def _get_osint_context(self, anomaly: Dict[str, Any]) -> List[Dict]:
        """Get relevant OSINT events for the anomaly timeframe (cached)."""
        conn = None
        try:
            trade_time = anomaly.get("trade_timestamp", anomaly.get("timestamp"))
            if not trade_time:
                return []

            if isinstance(trade_time, str):
                trade_dt = datetime.fromisoformat(trade_time.replace("Z", "+00:00"))
            else:
                trade_dt = trade_time

            # Round to nearest hour for better cache hits across similar trades
            rounded = trade_dt.replace(minute=0, second=0, microsecond=0)
            start = (rounded - timedelta(hours=24)).isoformat()
            end = (rounded + timedelta(hours=24)).isoformat()

            cache_key = f"{start}|{end}"
            if cache_key in self._osint_cache:
                return self._osint_cache[cache_key]

            conn = self._open_connection()
            events = get_osint_events_in_range(conn, start, end, limit=10)
            self._osint_cache[cache_key] = events
            return events

        except Exception as e:
            logger.warning("Could not fetch OSINT context: %s", e)
            return []
        finally:
            if conn is not None:
                conn.close()

    def _save_to_db(
        self,
        anomaly: Dict[str, Any],
        result: PipelineResult,
        magistral: MagistralResult,
        *,
        osint_context: Optional[List[Dict[str, Any]]] = None,
    ):
        """Save results to the database."""
        conn = None
        try:
            conn = self._open_connection()

            timestamp = self._to_iso_timestamp(
                anomaly.get("timestamp") or anomaly.get("trade_timestamp")
            ) or datetime.now(timezone.utc).isoformat()
            trade_timestamp = self._to_iso_timestamp(anomaly.get("trade_timestamp"))
            osint_context = osint_context or []

            # Build timeline-friendly OSINT summary for dashboard rendering.
            trade_dt = None
            if trade_timestamp:
                try:
                    trade_dt = datetime.fromisoformat(trade_timestamp.replace("Z", "+00:00"))
                except Exception:
                    trade_dt = None

            osint_signals: List[Dict[str, Any]] = []
            news_timestamp = None
            news_headline = None
            earliest_ts = None
            for signal in osint_context[:10]:
                signal_ts = self._to_iso_timestamp(signal.get("timestamp"))
                if signal_ts and (earliest_ts is None or signal_ts < earliest_ts):
                    earliest_ts = signal_ts
                    news_timestamp = signal_ts
                    news_headline = signal.get("headline") or signal.get("title")

                hours_before_trade = None
                if trade_dt and signal_ts:
                    try:
                        sig_dt = datetime.fromisoformat(signal_ts.replace("Z", "+00:00"))
                        hours_before_trade = round((trade_dt - sig_dt).total_seconds() / 3600.0, 3)
                    except Exception:
                        hours_before_trade = None

                osint_signals.append(
                    {
                        "source": signal.get("source"),
                        "headline": signal.get("headline") or signal.get("title"),
                        "timestamp": signal_ts,
                        "hours_before_trade": hours_before_trade,
                    }
                )

            # Save anomaly event
            anomaly_record = {
                **anomaly,
                "event_id": result.event_id,
                "timestamp": timestamp,
                "trade_timestamp": trade_timestamp,
                "classification": result.classification,
                "bss_score": result.bss_score,
                "pes_score": result.pes_score,
                "confidence": result.confidence,
                "xai_narrative": magistral.xai_narrative,
                "fraud_triangle_json": json.dumps(magistral.fraud_triangle),
            }
            insert_anomaly(conn, anomaly_record)

            # Save to Sentinel Index
            case_record = {
                "case_id": result.case_id,
                "anomaly_event_id": result.event_id,
                "market_id": anomaly.get("market_id"),
                "market_name": anomaly.get("market_name"),
                "classification": result.classification,
                "bss_score": result.bss_score,
                "pes_score": result.pes_score,
                "temporal_gap_hours": anomaly.get("hours_before_news"),
                "status": "UNDER_REVIEW",
                "sar_report": result.sar_report,
                "xai_summary": magistral.xai_narrative[:500] if magistral.xai_narrative else None,
                "evidence_json": json.dumps(
                    {
                        "evidence_summary": magistral.evidence_summary,
                        "recommendation": magistral.recommendation,
                        "trade_timestamp": trade_timestamp or timestamp,
                        "trade_size_usd": anomaly.get("trade_size"),
                        "market_id": anomaly.get("market_id"),
                        "market_name": anomaly.get("market_name"),
                        "wallet_address": anomaly.get("wallet_address"),
                        "wallet_age_days": anomaly.get("wallet_age_days"),
                        "wallet_trades": anomaly.get("wallet_trades"),
                        "z_score": anomaly.get("z_score"),
                        "hours_before_news": anomaly.get("hours_before_news"),
                        "osint_signals_before_trade": anomaly.get("osint_signals_before_trade"),
                        "osint_context_count": len(osint_context),
                        "news_timestamp": news_timestamp,
                        "news_headline": news_headline,
                        "osint_signals": osint_signals[:5],
                        "rf_analysis": anomaly.get("rf_analysis", {}),
                        "game_theory_analysis": anomaly.get("game_theory_analysis", {}),
                        "classification": result.triage,
                    }
                ),
            }
            insert_case(conn, case_record)

            conn.commit()
            logger.info("Saved anomaly and case to database: case_id=%s", result.case_id)

        except Exception as e:
            logger.exception("Database save error: %s", e)
            raise
        finally:
            if conn is not None:
                conn.close()

    @staticmethod
    def _to_iso_timestamp(value: Any) -> Optional[str]:
        """Normalize timestamps to ISO-8601 strings."""
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc).isoformat()
            return value.astimezone(timezone.utc).isoformat()
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc).isoformat()
            except ValueError:
                return value
        return str(value)

    @staticmethod
    def _normalize_anomaly_input(anomaly: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize common alias fields and validate DB-required keys."""
        normalized = dict(anomaly)

        if not normalized.get("wallet_address") and normalized.get("wallet"):
            normalized["wallet_address"] = normalized.get("wallet")

        if normalized.get("trade_size") is None and normalized.get("trade_size_usd") is not None:
            normalized["trade_size"] = normalized.get("trade_size_usd")

        if not normalized.get("market_id"):
            alias_market = normalized.get("token") or normalized.get("market")
            if alias_market:
                market_id = str(alias_market).strip().lower().replace(" ", "-")
                normalized["market_id"] = market_id
                normalized.setdefault("market_name", str(alias_market))
            else:
                raise ValueError(
                    "Missing required field 'market_id'. "
                    "Provide market_id directly or alias via token/market."
                )

        if not normalized.get("market_name"):
            normalized["market_name"] = normalized.get("market_id")

        return normalized

    def _open_connection(self) -> sqlite3.Connection:
        """Open DB connection using configured path when provided."""
        if self.db_path:
            return get_connection(self.db_path)
        return get_connection()

    def process_batch(
        self,
        anomalies: List[Dict[str, Any]],
        save_to_db: bool = True,
        max_workers: int = 4,
    ) -> List[PipelineResult]:
        """
        Process multiple anomalies in parallel.

        Args:
            anomalies: List of anomaly dicts
            save_to_db: Whether to save to database
            max_workers: Maximum number of concurrent threads

        Returns:
            List of PipelineResults (preserves input order)
        """
        total = len(anomalies)
        if total == 0:
            return []

        # For a single anomaly, skip thread overhead
        if total == 1:
            print(f"\n[1/1] Processing...")
            try:
                return [self.process_anomaly(anomalies[0], save_to_db=save_to_db)]
            except Exception as e:
                print(f"  ❌ Error: {e}")
                return []

        print(f"\nProcessing {total} anomalies in parallel (max {max_workers} workers)...")
        # Use ordered slots to preserve input order
        results: List[Optional[PipelineResult]] = [None] * total

        def _process_one(idx: int, anomaly: Dict[str, Any]) -> None:
            print(f"  [{idx + 1}/{total}] Starting...")
            results[idx] = self.process_anomaly(anomaly, save_to_db=save_to_db)
            print(f"  [{idx + 1}/{total}] Done: {results[idx].classification}")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_process_one, i, a): i
                for i, a in enumerate(anomalies)
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"  [{idx + 1}/{total}] ❌ Error: {e}")

        return [r for r in results if r is not None]


def run_pipeline(
    anomaly: Dict[str, Any],
    api_key: Optional[str] = None,
    save_to_db: bool = False
) -> PipelineResult:
    """
    Convenience function to run the pipeline on a single anomaly.

    Args:
        anomaly: Anomaly data
        api_key: Mistral API key
        save_to_db: Whether to save results

    Returns:
        PipelineResult
    """
    pipeline = SentinelPipeline(api_key=api_key)
    return pipeline.process_anomaly(anomaly, save_to_db=save_to_db)


if __name__ == "__main__":
    # Test the pipeline
    print("=" * 60)
    print("Testing Sentinel Classification Pipeline")
    print("=" * 60)

    test_anomalies = [
        {
            "market_id": "tariff-test",
            "market_name": "Will the US announce new tariffs?",
            "wallet_address": "0x" + "a" * 40,
            "wallet_age_days": 2,
            "wallet_trades": 1,
            "trade_size": 50000,
            "price_before": 0.35,
            "price_after": 0.89,
            "z_score": 4.5,
            "hours_before_news": -8,
            "osint_signals_before_trade": 0,
            "timestamp": datetime.now().isoformat(),
        },
        {
            "market_id": "hurricane-test",
            "market_name": "Will hurricane make landfall?",
            "wallet_address": "0x" + "b" * 40,
            "wallet_age_days": 180,
            "wallet_trades": 45,
            "trade_size": 15000,
            "price_before": 0.42,
            "price_after": 0.91,
            "z_score": 2.1,
            "hours_before_news": 6,
            "osint_signals_before_trade": 3,
            "timestamp": datetime.now().isoformat(),
        },
        {
            "market_id": "random-test",
            "market_name": "Will it rain tomorrow?",
            "wallet_address": "0x" + "c" * 40,
            "wallet_age_days": 60,
            "wallet_trades": 12,
            "trade_size": 500,
            "price_before": 0.50,
            "price_after": 0.55,
            "z_score": 0.4,
            "hours_before_news": None,
            "osint_signals_before_trade": 0,
            "timestamp": datetime.now().isoformat(),
        },
    ]

    pipeline = SentinelPipeline(skip_low_suspicion=True)

    for anomaly in test_anomalies:
        print(f"\n{'=' * 60}")
        result = pipeline.process_anomaly(anomaly, save_to_db=False)
        print(f"\n📊 Result Summary:")
        print(f"   Case ID: {result.case_id}")
        print(f"   Classification: {result.classification}")
        print(f"   BSS: {result.bss_score}, PES: {result.pes_score}")
        print(f"   Confidence: {result.confidence:.0%}")
        if result.sar_report:
            print(f"   SAR: Generated")
        else:
            print(f"   SAR: Skipped")
