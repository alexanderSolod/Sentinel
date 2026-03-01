"""Continuous learning utilities for Arena-driven retraining triggers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from src.data.database import get_connection


@dataclass
class DriftReport:
    samples: int
    accuracy: float
    drift_detected: bool


class ContinuousLearningManager:
    """
    Minimal manager for deciding when retraining should run.

    This implementation avoids hard coupling to external trainers while still
    providing robust drift/retrain trigger logic that can be scheduled.
    """

    def __init__(
        self,
        *,
        db_path: Optional[str] = None,
        retrain_interval_hours: int = 24,
        min_new_labels: int = 10,
        min_votes: int = 5,
        drift_threshold: float = 0.70,
    ) -> None:
        self.db_path = db_path
        self.retrain_interval = timedelta(hours=retrain_interval_hours)
        self.min_new_labels = min_new_labels
        self.min_votes = min_votes
        self.drift_threshold = drift_threshold
        self.last_retrain: Optional[datetime] = None

    def check_and_retrain_needed(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        if self.last_retrain and now - self.last_retrain < self.retrain_interval:
            return {
                "should_retrain": False,
                "reason": "interval_not_elapsed",
                "next_check_after": (self.last_retrain + self.retrain_interval).isoformat(),
            }

        labeled = self._get_consensus_cases(since=self.last_retrain)
        if len(labeled) < self.min_new_labels:
            return {
                "should_retrain": False,
                "reason": "insufficient_new_labels",
                "new_labels": len(labeled),
                "required": self.min_new_labels,
            }

        drift = self._detect_drift(labeled)
        if drift.drift_detected or len(labeled) >= self.min_new_labels * 3:
            return {
                "should_retrain": True,
                "reason": "drift_detected" if drift.drift_detected else "label_volume_trigger",
                "drift": {
                    "samples": drift.samples,
                    "accuracy": drift.accuracy,
                    "threshold": self.drift_threshold,
                },
                "new_labels": len(labeled),
            }

        return {
            "should_retrain": False,
            "reason": "stable_performance",
            "drift": {
                "samples": drift.samples,
                "accuracy": drift.accuracy,
                "threshold": self.drift_threshold,
            },
        }

    def mark_retrained(self) -> None:
        self.last_retrain = datetime.now(timezone.utc)

    def _get_consensus_cases(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path) if self.db_path else get_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT case_id, classification, status, vote_count, updated_at
                FROM sentinel_index
                WHERE vote_count >= ? AND status IN ('CONFIRMED', 'DISPUTED')
            """
            params: List[Any] = [self.min_votes]

            if since is not None:
                query += " AND updated_at >= ?"
                params.append(since.isoformat())

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def _detect_drift(self, labeled_cases: List[Dict[str, Any]]) -> DriftReport:
        if not labeled_cases:
            return DriftReport(samples=0, accuracy=1.0, drift_detected=False)

        correct = 0
        total = 0
        for case in labeled_cases:
            classification = str(case.get("classification", "")).upper()
            status = str(case.get("status", "")).upper()

            if status not in {"CONFIRMED", "DISPUTED"}:
                continue

            total += 1
            if status == "CONFIRMED":
                correct += 1

        if total == 0:
            return DriftReport(samples=0, accuracy=1.0, drift_detected=False)

        accuracy = correct / total
        return DriftReport(samples=total, accuracy=accuracy, drift_detected=accuracy < self.drift_threshold)
