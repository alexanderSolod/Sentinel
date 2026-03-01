"""NLP utilities for OSINT-to-market relevance and asymmetry analysis."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

import numpy as np


class OSINTTextAnalyzer:
    def __init__(self, embedding_model=None) -> None:
        self.embedding_model = embedding_model
        self._stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "that",
            "this", "these", "those", "it", "its", "and", "but", "or",
            "not", "no", "if", "then", "than", "so", "very", "just",
            "will", "would", "market", "markets", "prediction", "event",
        }

    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        words = re.findall(r"\b[a-zA-Z]{3,}\b", str(text).lower())
        filtered = [w for w in words if w not in self._stop_words]
        counts = Counter(filtered)
        return [word for word, _ in counts.most_common(top_n)]

    def compute_relevance_score(
        self,
        osint_text: str,
        market_description: str,
        market_keywords: Sequence[str],
    ) -> Dict[str, Any]:
        osint_keywords = set(self.extract_keywords(osint_text, top_n=30))
        market_kw_set = {k.lower() for k in market_keywords}

        matched = osint_keywords & market_kw_set
        keyword_overlap = len(matched) / max(len(market_kw_set), 1)

        result: Dict[str, Any] = {
            "keyword_overlap": keyword_overlap,
            "matched_keywords": sorted(matched),
            "semantic_similarity": None,
            "composite_relevance": keyword_overlap,
        }

        if self.embedding_model:
            try:
                osint_vec = self.embedding_model(osint_text)
                market_vec = self.embedding_model(market_description)
                similarity = self._cosine_similarity(osint_vec, market_vec)
                result["semantic_similarity"] = similarity
                result["composite_relevance"] = 0.4 * keyword_overlap + 0.6 * similarity
            except Exception:
                pass

        return result

    def classify_information_type(self, text: str) -> Dict[str, Any]:
        text_lower = str(text).lower()

        indicators = {
            "BREAKING_NEWS": [
                "breaking", "just in", "happening now", "confirmed",
                "sources say", "reuters", "ap", "exclusive", "developing",
            ],
            "OFFICIAL": [
                "announces", "announced", "statement", "press release",
                "official", "government", "white house", "ministry",
                "department", "federal", "regulation",
            ],
            "DATA_RELEASE": [
                "data shows", "report shows", "statistics", "quarterly",
                "earnings", "gdp", "inflation", "unemployment", "index",
            ],
            "RUMOR": [
                "reportedly", "alleged", "unconfirmed", "rumor",
                "sources claim", "may", "might", "could", "speculation",
            ],
            "ANALYSIS": [
                "analysis", "opinion", "editorial", "commentary",
                "experts say", "analysts", "forecast", "predict", "outlook",
            ],
        }

        scores: Dict[str, int] = {}
        for category, keywords in indicators.items():
            scores[category] = sum(1 for kw in keywords if kw in text_lower)

        best = max(scores, key=scores.get) if any(scores.values()) else "UNKNOWN"
        conf = scores.get(best, 0) / max(sum(scores.values()), 1)
        return {"category": best, "confidence": conf, "all_scores": scores}

    def compute_information_asymmetry_indicators(
        self,
        osint_text: str,
        trade_timestamp: Any,
        osint_timestamp: Any,
    ) -> Dict[str, Any]:
        trade_dt = self._parse_dt(trade_timestamp)
        osint_dt = self._parse_dt(osint_timestamp)
        info_type = self.classify_information_type(osint_text)

        if trade_dt is None or osint_dt is None:
            return {
                "info_type": info_type["category"],
                "temporal_gap_hours": None,
                "trade_before_info": False,
                "info_was_public": False,
                "asymmetry_class": "UNKNOWN",
                "asymmetry_score": 50,
            }

        gap_hours = (trade_dt - osint_dt).total_seconds() / 3600.0
        result = {
            "info_type": info_type["category"],
            "temporal_gap_hours": gap_hours,
            "trade_before_info": gap_hours < 0,
            "info_was_public": gap_hours > 0,
        }

        if gap_hours < -24:
            result["asymmetry_class"] = "STRONG_INSIDER_SIGNAL"
            result["asymmetry_score"] = 95
        elif gap_hours < -6:
            result["asymmetry_class"] = "MODERATE_INSIDER_SIGNAL"
            result["asymmetry_score"] = 75
        elif gap_hours < -1:
            result["asymmetry_class"] = "WEAK_INSIDER_SIGNAL"
            result["asymmetry_score"] = 55
        elif gap_hours < 0:
            result["asymmetry_class"] = "POSSIBLE_FAST_REACTOR"
            result["asymmetry_score"] = 35
        elif gap_hours < 1:
            result["asymmetry_class"] = "FAST_REACTOR"
            result["asymmetry_score"] = 15
        else:
            result["asymmetry_class"] = "POST_INFO_TRADE"
            result["asymmetry_score"] = 5

        if info_type["category"] == "RUMOR" and gap_hours > -6:
            result["asymmetry_score"] = max(0, result["asymmetry_score"] - 20)
            result["note"] = "OSINT signal was rumor-like and could be public chatter"

        return result

    @staticmethod
    def _cosine_similarity(a, b) -> float:
        a_arr = np.array(a)
        b_arr = np.array(b)
        denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        if denom == 0:
            return 0.0
        return float(np.dot(a_arr, b_arr) / denom)

    @staticmethod
    def _parse_dt(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                return None
        return None
