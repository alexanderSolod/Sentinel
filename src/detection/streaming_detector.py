"""Streaming anomaly detector for per-trade online scoring."""
from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any, Dict

import numpy as np


class StreamingAnomalyDetector:
    """
    Online anomaly detection using rolling market statistics.

    Designed to be O(1) state update per trade.
    """

    def __init__(
        self,
        baseline_window: int = 1000,
        z_threshold: float = 3.0,
        price_threshold: float = 0.15,
    ) -> None:
        self.baseline_window = baseline_window
        self.z_threshold = z_threshold
        self.price_threshold = price_threshold
        self.market_stats: Dict[str, Dict[str, deque]] = {}

    def _get_stats(self, market_id: str) -> Dict[str, deque]:
        if market_id not in self.market_stats:
            self.market_stats[market_id] = {
                "volumes": deque(maxlen=self.baseline_window),
                "prices": deque(maxlen=self.baseline_window),
                "timestamps": deque(maxlen=self.baseline_window),
                "trade_intervals": deque(maxlen=self.baseline_window),
            }
        return self.market_stats[market_id]

    def process_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        market_id = str(trade.get("market_id", "unknown"))
        stats = self._get_stats(market_id)

        amount = float(trade.get("amount_usd", trade.get("trade_size", 0)) or 0)
        price = float(trade.get("price", 0) or 0)
        timestamp = trade.get("timestamp")

        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except Exception:
                timestamp = None

        result = {
            "is_anomalous": False,
            "anomaly_types": [],
            "volume_z": 0.0,
            "price_move": 0.0,
            "interval_z": 0.0,
            "severity": "LOW",
            "score": 0.0,
        }

        if len(stats["volumes"]) >= 20:
            mean_vol = float(np.mean(stats["volumes"]))
            std_vol = float(np.std(stats["volumes"]))
            if std_vol > 0:
                result["volume_z"] = (amount - mean_vol) / std_vol
                if result["volume_z"] > self.z_threshold:
                    result["is_anomalous"] = True
                    result["anomaly_types"].append("VOLUME_SPIKE")

        if stats["prices"]:
            last_price = float(stats["prices"][-1])
            if last_price > 0:
                result["price_move"] = abs(price - last_price) / last_price
                if result["price_move"] > self.price_threshold:
                    result["is_anomalous"] = True
                    result["anomaly_types"].append("PRICE_DISLOCATION")

        if timestamp and stats["timestamps"]:
            interval = (timestamp - stats["timestamps"][-1]).total_seconds()
            stats["trade_intervals"].append(interval)

            if len(stats["trade_intervals"]) >= 20:
                mean_int = float(np.mean(stats["trade_intervals"]))
                std_int = float(np.std(stats["trade_intervals"]))
                if std_int > 0:
                    result["interval_z"] = (mean_int - interval) / std_int
                    if result["interval_z"] > self.z_threshold:
                        result["is_anomalous"] = True
                        result["anomaly_types"].append("TRADE_BURST")

        if result["is_anomalous"]:
            n_signals = len(result["anomaly_types"])
            max_z = max(abs(result["volume_z"]), abs(result["interval_z"]))
            if n_signals >= 2 and max_z > 5:
                result["severity"] = "CRITICAL"
            elif n_signals >= 2 or max_z > 4:
                result["severity"] = "HIGH"
            elif max_z > self.z_threshold:
                result["severity"] = "MEDIUM"

        score = 0.0
        score += min(1.0, max(0.0, result["volume_z"]) / 6.0) * 0.4
        score += min(1.0, result["price_move"] / 0.3) * 0.3
        score += min(1.0, max(0.0, result["interval_z"]) / 6.0) * 0.3
        result["score"] = round(min(1.0, score), 4)

        stats["volumes"].append(amount)
        stats["prices"].append(price)
        if timestamp:
            stats["timestamps"].append(timestamp)

        return result
