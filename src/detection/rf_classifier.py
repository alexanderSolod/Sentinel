"""
Random Forest classifier wrapper for Sentinel.

Implements a paper-aligned interface while remaining robust when sklearn is
not available in the runtime. In fallback mode, it returns a calibrated
heuristic score based on the current feature vector.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
import pickle
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import numpy as np

from src.detection.features import FeatureVector

logger = logging.getLogger(__name__)

try:
    from sklearn.decomposition import PCA
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import StratifiedKFold
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover - defensive import fallback
    SKLEARN_AVAILABLE = False


@dataclass
class RFPrediction:
    rf_score: float
    rf_label: str
    confidence: float
    top_features: List[Dict[str, float]]
    source: str


class RFClassifier:
    """
    Random Forest wrapper with optional PCA and safe heuristic fallback.

    Expected binary target semantics:
      1 = suspicious
      0 = legitimate
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        *,
        threshold: float = 0.5,
        use_pca: bool = False,
        pca_variance: float = 0.95,
    ) -> None:
        self.threshold = threshold
        self.use_pca = use_pca
        self.pca_variance = pca_variance

        self.model: Any = None
        self.scaler: Any = None
        self.pca: Any = None
        self.feature_names: List[str] = FeatureVector.feature_names()
        self.is_trained = False

        self.model_path = (
            Path(model_path)
            if model_path
            else Path(os.getenv("SENTINEL_RF_MODEL_PATH", "./models/rf_classifier.pkl"))
        )

        if self.model_path.exists():
            try:
                self.load(str(self.model_path))
                logger.info("Loaded RF model from %s", self.model_path)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to load RF model at %s: %s", self.model_path, exc)

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[Sequence[str]] = None,
        *,
        n_estimators: int = 300,
        max_depth: Optional[int] = 12,
        min_samples_leaf: int = 2,
        cv_splits: int = 5,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """Train RF model and return quick validation metrics."""
        if not SKLEARN_AVAILABLE:
            raise RuntimeError("scikit-learn is not available; cannot train RF model")

        if X.ndim != 2:
            raise ValueError("X must be a 2D matrix")
        if len(X) != len(y):
            raise ValueError("X and y must have same number of rows")

        self.feature_names = list(feature_names or self.feature_names)

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        if self.use_pca:
            self.pca = PCA(n_components=self.pca_variance, svd_solver="full")
            X_model = self.pca.fit_transform(X_scaled)
        else:
            self.pca = None
            X_model = X_scaled

        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
        )
        self.model.fit(X_model, y)
        self.is_trained = True

        # Lightweight CV metrics for diagnostics.
        cv = StratifiedKFold(n_splits=max(2, cv_splits), shuffle=True, random_state=random_state)
        fold_acc: List[float] = []
        fold_f1: List[float] = []
        for train_idx, test_idx in cv.split(X_model, y):
            fold_model = RandomForestClassifier(
                n_estimators=max(100, n_estimators // 2),
                max_depth=max_depth,
                min_samples_leaf=min_samples_leaf,
                class_weight="balanced",
                random_state=random_state,
                n_jobs=-1,
            )
            fold_model.fit(X_model[train_idx], y[train_idx])
            pred = fold_model.predict(X_model[test_idx])
            fold_acc.append(float(accuracy_score(y[test_idx], pred)))
            fold_f1.append(float(f1_score(y[test_idx], pred, zero_division=0)))

        return {
            "trained": True,
            "samples": int(len(y)),
            "features": int(X.shape[1]),
            "used_pca": bool(self.pca is not None),
            "cv_accuracy_mean": float(np.mean(fold_acc)) if fold_acc else None,
            "cv_accuracy_std": float(np.std(fold_acc)) if fold_acc else None,
            "cv_f1_mean": float(np.mean(fold_f1)) if fold_f1 else None,
            "cv_f1_std": float(np.std(fold_f1)) if fold_f1 else None,
        }

    def predict(self, feature_vector: FeatureVector | Dict[str, Any]) -> Dict[str, Any]:
        """Predict suspicious probability for one feature vector."""
        vec = self._coerce_feature_vector(feature_vector)

        if self.is_trained and self.model is not None and SKLEARN_AVAILABLE:
            return self._predict_model(vec)

        return self._predict_heuristic(vec)

    def save(self, path: Optional[str] = None) -> str:
        target = Path(path) if path else self.model_path
        target.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "model": self.model,
            "scaler": self.scaler,
            "pca": self.pca,
            "feature_names": self.feature_names,
            "threshold": self.threshold,
            "use_pca": self.use_pca,
            "pca_variance": self.pca_variance,
            "is_trained": self.is_trained,
        }
        with open(target, "wb") as f:
            pickle.dump(payload, f)
        return str(target)

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            payload = pickle.load(f)

        self.model = payload.get("model")
        self.scaler = payload.get("scaler")
        self.pca = payload.get("pca")
        self.feature_names = list(payload.get("feature_names", FeatureVector.feature_names()))
        self.threshold = float(payload.get("threshold", 0.5))
        self.use_pca = bool(payload.get("use_pca", False))
        self.pca_variance = float(payload.get("pca_variance", 0.95))
        self.is_trained = bool(payload.get("is_trained", self.model is not None))

    def _predict_model(self, vec: FeatureVector) -> Dict[str, Any]:
        x = np.array([vec.to_array()], dtype=float)

        if self.scaler is not None:
            x = self.scaler.transform(x)
        if self.pca is not None:
            x = self.pca.transform(x)

        if hasattr(self.model, "predict_proba"):
            score = float(self.model.predict_proba(x)[0][1])
        else:  # pragma: no cover - defensive
            score = float(self.model.predict(x)[0])

        label = "SUSPICIOUS" if score >= self.threshold else "LEGITIMATE"
        confidence = abs(score - 0.5) * 2

        top_features: List[Dict[str, float]] = []
        if self.pca is None and hasattr(self.model, "feature_importances_"):
            importances = list(zip(self.feature_names, self.model.feature_importances_))
            importances.sort(key=lambda x: x[1], reverse=True)
            top_features = [
                {"feature": name, "importance": round(float(val), 4)}
                for name, val in importances[:5]
            ]

        return {
            "rf_score": round(score, 4),
            "rf_label": label,
            "confidence": round(float(confidence), 4),
            "top_features": top_features,
            "source": "random_forest",
        }

    def _predict_heuristic(self, vec: FeatureVector) -> Dict[str, Any]:
        # Map existing heuristic signal to a pseudo-probability with conservative
        # calibration and mild boosts from underutilized dimensions.
        base = vec.suspicion_heuristic / 100.0

        if vec.composite_risk_score > 0:
            base = 0.75 * base + 0.25 * min(max(vec.composite_risk_score, 0.0), 1.0)

        if vec.hours_before_news is not None and vec.hours_before_news < 0 and vec.osint_signal_count == 0:
            base = min(1.0, base + 0.10)

        score = float(min(1.0, max(0.0, base)))
        label = "SUSPICIOUS" if score >= self.threshold else "LEGITIMATE"
        confidence = abs(score - 0.5) * 2

        top_features = [
            {"feature": "suspicion_heuristic", "importance": round(vec.suspicion_heuristic / 100.0, 4)},
            {"feature": "hours_before_news", "importance": round(abs(vec.hours_before_news or 0.0) / 24.0, 4)},
            {"feature": "is_fresh_wallet", "importance": float(vec.is_fresh_wallet)},
            {"feature": "z_score", "importance": round(min(1.0, vec.z_score / 5.0), 4)},
            {"feature": "composite_risk_score", "importance": round(float(vec.composite_risk_score), 4)},
        ]

        return {
            "rf_score": round(score, 4),
            "rf_label": label,
            "confidence": round(float(confidence), 4),
            "top_features": top_features,
            "source": "heuristic_fallback",
        }

    @staticmethod
    def _coerce_feature_vector(feature_vector: FeatureVector | Dict[str, Any]) -> FeatureVector:
        if isinstance(feature_vector, FeatureVector):
            return feature_vector

        data = dict(feature_vector)
        vec = FeatureVector()
        for key in FeatureVector.feature_names():
            if key in data:
                setattr(vec, key, data[key])

        # Preserve fields that are not in feature_names list.
        vec.hours_before_news = data.get("hours_before_news", vec.hours_before_news)
        vec.osint_signal_count = int(data.get("osint_signal_count", data.get("osint_signals_before_trade", vec.osint_signal_count)))
        vec.suspicion_heuristic  # ensure property available
        return vec


__all__ = ["RFClassifier", "RFPrediction", "SKLEARN_AVAILABLE"]
