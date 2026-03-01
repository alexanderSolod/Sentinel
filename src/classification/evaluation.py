"""
Evaluation metrics for Sentinel classification quality.

Current data model does not store an explicit human-assigned true class label.
So metrics are computed against Arena consensus outcomes:
  - CONFIRMED -> arena agreed with model classification
  - DISPUTED  -> arena disagreed with model classification

For binary metrics (FPR/FNR/confusion matrix), we evaluate "suspicious" detection:
  - Predicted positive: classification in positive_classes (default: {"INSIDER"})
  - True label:
      * CONFIRMED -> same as predicted
      * DISPUTED  -> inverse of predicted
"""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any, Dict, Sequence, Set


@dataclass
class BinaryConfusion:
    """Binary confusion matrix counts."""

    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn


def _safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _normalize_positive_classes(classes: Sequence[str] | None) -> Set[str]:
    if not classes:
        return {"INSIDER"}
    return {cls.upper() for cls in classes}


def compute_evaluation_metrics(
    conn: sqlite3.Connection,
    *,
    min_votes: int = 5,
    positive_classes: Sequence[str] | None = None,
) -> Dict[str, Any]:
    """
    Compute evaluation metrics from Sentinel index + Arena consensus.

    Returns:
        Dict containing:
          - fpr/fnr and related binary metrics
          - binary confusion matrix
          - arena consensus accuracy
          - evaluation coverage counts
    """
    positive = _normalize_positive_classes(positive_classes)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            case_id, classification, status, vote_count,
            votes_agree, votes_disagree, votes_uncertain
        FROM sentinel_index
        WHERE vote_count >= ?
        """,
        (min_votes,),
    )
    rows = [dict(row) for row in cursor.fetchall()]

    confusion = BinaryConfusion()
    confirmed = 0
    disputed = 0
    unresolved = 0

    for row in rows:
        status = (row.get("status") or "").upper()
        predicted_positive = (row.get("classification") or "").upper() in positive

        if status == "CONFIRMED":
            confirmed += 1
            true_positive = predicted_positive
        elif status == "DISPUTED":
            disputed += 1
            true_positive = not predicted_positive
        else:
            unresolved += 1
            continue

        if predicted_positive and true_positive:
            confusion.tp += 1
        elif predicted_positive and not true_positive:
            confusion.fp += 1
        elif (not predicted_positive) and (not true_positive):
            confusion.tn += 1
        else:
            confusion.fn += 1

    evaluated = confusion.total
    fpr = _safe_div(confusion.fp, confusion.fp + confusion.tn)
    fnr = _safe_div(confusion.fn, confusion.fn + confusion.tp)
    accuracy = _safe_div(confusion.tp + confusion.tn, evaluated)
    precision = _safe_div(confusion.tp, confusion.tp + confusion.fp)
    recall = _safe_div(confusion.tp, confusion.tp + confusion.fn)
    specificity = _safe_div(confusion.tn, confusion.tn + confusion.fp)

    consensus_denominator = confirmed + disputed
    consensus_accuracy = _safe_div(confirmed, consensus_denominator)

    return {
        "coverage": {
            "min_votes": min_votes,
            "total_cases_with_min_votes": len(rows),
            "evaluated_cases": evaluated,
            "unresolved_cases": unresolved,
        },
        "positive_classes": sorted(positive),
        "arena_consensus": {
            "confirmed_cases": confirmed,
            "disputed_cases": disputed,
            "consensus_accuracy": consensus_accuracy,
        },
        "binary_confusion_matrix": {
            "labels": {
                "actual": ["POSITIVE", "NEGATIVE"],
                "predicted": ["POSITIVE", "NEGATIVE"],
            },
            # Row-major by actual class.
            "matrix": [
                [confusion.tp, confusion.fn],
                [confusion.fp, confusion.tn],
            ],
            "counts": {
                "tp": confusion.tp,
                "fp": confusion.fp,
                "tn": confusion.tn,
                "fn": confusion.fn,
            },
        },
        "metrics": {
            "fpr": fpr,
            "fnr": fnr,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "specificity": specificity,
        },
        "assumptions": [
            "Ground truth is inferred from Arena status (CONFIRMED/DISPUTED).",
            "Binary positive class is configurable via positive_classes.",
            "UNDER_REVIEW cases are excluded from FPR/FNR and confusion matrix.",
        ],
    }
