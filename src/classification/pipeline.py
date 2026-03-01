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
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.classification.stage1_triage import classify_anomaly, TriageResult
from src.classification.stage2_magistral import analyze_case, MagistralResult
from src.classification.stage3_sar import generate_sar, SARReport
from src.detection.features import FeatureExtractor
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
        db_path: Optional[str] = None
    ):
        """
        Initialize the pipeline.

        Args:
            api_key: Mistral API key (uses env var if not provided)
            skip_low_suspicion: Skip Stage 2/3 for low-suspicion cases
            suspicion_threshold: BSS threshold for deep analysis
            db_path: Database path (uses default if not provided)
        """
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.skip_low_suspicion = skip_low_suspicion
        self.suspicion_threshold = suspicion_threshold
        self.db_path = db_path
        self.feature_extractor = FeatureExtractor()

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
        anomaly = dict(anomaly)
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
        # Stage 1: Fast Triage
        # ============================================
        logger.info("Stage 1: Triage classification")
        triage_input = features.to_classifier_input()

        triage_result = classify_anomaly(triage_input, api_key=self.api_key)
        logger.info(
            "Stage 1 result: classification=%s bss=%d pes=%d",
            triage_result.classification,
            triage_result.bss_score,
            triage_result.pes_score,
        )

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

            # Get OSINT context if available
            osint_context = self._get_osint_context(anomaly)

            triage_dict = {
                "classification": triage_result.classification,
                "bss_score": triage_result.bss_score,
                "pes_score": triage_result.pes_score,
                "confidence": triage_result.confidence,
                "reasoning": triage_result.reasoning,
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
            },
            analysis={
                "xai_narrative": magistral_result.xai_narrative,
                "fraud_triangle": magistral_result.fraud_triangle,
                "temporal_analysis": magistral_result.temporal_analysis,
                "evidence_summary": magistral_result.evidence_summary,
                "recommendation": magistral_result.recommendation,
            },
            sar_report=sar_text,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # ============================================
        # Save to Database
        # ============================================
        if save_to_db:
            self._save_to_db(anomaly, result, magistral_result)

        logger.info("Pipeline complete: %s", case_id)
        return result

    def _get_osint_context(self, anomaly: Dict[str, Any]) -> List[Dict]:
        """Get relevant OSINT events for the anomaly timeframe."""
        conn = None
        try:
            conn = self._open_connection()
            trade_time = anomaly.get("trade_timestamp", anomaly.get("timestamp"))

            if trade_time:
                # Get events in 24-hour window around trade
                if isinstance(trade_time, str):
                    trade_dt = datetime.fromisoformat(trade_time.replace("Z", "+00:00"))
                else:
                    trade_dt = trade_time

                start = (trade_dt - timedelta(hours=24)).isoformat()
                end = (trade_dt + timedelta(hours=24)).isoformat()

                events = get_osint_events_in_range(conn, start, end, limit=10)
                return events

            return []

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
        magistral: MagistralResult
    ):
        """Save results to the database."""
        conn = None
        try:
            conn = self._open_connection()

            timestamp = self._to_iso_timestamp(
                anomaly.get("timestamp") or anomaly.get("trade_timestamp")
            ) or datetime.now(timezone.utc).isoformat()
            trade_timestamp = self._to_iso_timestamp(anomaly.get("trade_timestamp"))

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
                "evidence_json": json.dumps({
                    "evidence_summary": magistral.evidence_summary,
                    "recommendation": magistral.recommendation,
                    "trade_timestamp": trade_timestamp or timestamp,
                    "trade_size_usd": anomaly.get("trade_size"),
                    "market_id": anomaly.get("market_id"),
                    "market_name": anomaly.get("market_name"),
                    "wallet_address": anomaly.get("wallet_address"),
                    "hours_before_news": anomaly.get("hours_before_news"),
                    "osint_signals_before_trade": anomaly.get("osint_signals_before_trade"),
                }),
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

    def _open_connection(self) -> sqlite3.Connection:
        """Open DB connection using configured path when provided."""
        if self.db_path:
            return get_connection(self.db_path)
        return get_connection()

    def process_batch(
        self,
        anomalies: List[Dict[str, Any]],
        save_to_db: bool = True
    ) -> List[PipelineResult]:
        """
        Process multiple anomalies.

        Args:
            anomalies: List of anomaly dicts
            save_to_db: Whether to save to database

        Returns:
            List of PipelineResults
        """
        results = []
        total = len(anomalies)

        for i, anomaly in enumerate(anomalies, 1):
            print(f"\n[{i}/{total}] Processing...")
            try:
                result = self.process_anomaly(anomaly, save_to_db=save_to_db)
                results.append(result)
            except Exception as e:
                print(f"  ❌ Error: {e}")
                continue

        return results


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
