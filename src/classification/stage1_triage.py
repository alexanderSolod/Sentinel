"""
Stage 1: Fast Triage Classifier
Uses Mistral Small with few-shot prompting (or fine-tuned model) for rapid 4-class classification.

Classifications:
- INSIDER: Trade based on material non-public information
- OSINT_EDGE: Trade based on superior public intelligence gathering
- FAST_REACTOR: Quick reaction to breaking news
- SPECULATOR: Normal speculation with no edge
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TriageResult:
    """Result from Stage 1 triage classification."""
    classification: str
    bss_score: int  # Behavioral Suspicion Score 0-100
    pes_score: int  # Public Explainability Score 0-100
    confidence: float
    reasoning: str


# Few-shot examples for the classifier
FEW_SHOT_EXAMPLES = """
Example 1:
Input: {"wallet_age_days": 2, "wallet_trades": 1, "trade_size_usd": 50000, "hours_before_news": -8, "osint_signals_before_trade": 0, "z_score": 4.5}
Output: {"classification": "INSIDER", "bss_score": 95, "pes_score": 5, "confidence": 0.92, "reasoning": "Fresh wallet (2 days), single trade before major news with no public signals. Classic insider pattern."}

Example 2:
Input: {"wallet_age_days": 180, "wallet_trades": 45, "trade_size_usd": 15000, "hours_before_news": 6, "osint_signals_before_trade": 3, "z_score": 2.1}
Output: {"classification": "OSINT_EDGE", "bss_score": 30, "pes_score": 82, "confidence": 0.88, "reasoning": "Established trader with good track record. Multiple public signals existed before trade. Legitimate research edge."}

Example 3:
Input: {"wallet_age_days": 90, "wallet_trades": 20, "trade_size_usd": 5000, "hours_before_news": 0.05, "osint_signals_before_trade": 1, "z_score": 1.0}
Output: {"classification": "FAST_REACTOR", "bss_score": 15, "pes_score": 95, "confidence": 0.95, "reasoning": "Trade placed 3 minutes after breaking news. Normal fast reaction to public information."}

Example 4:
Input: {"wallet_age_days": 60, "wallet_trades": 12, "trade_size_usd": 800, "hours_before_news": null, "osint_signals_before_trade": 0, "z_score": 0.4}
Output: {"classification": "SPECULATOR", "bss_score": 18, "pes_score": 50, "confidence": 0.85, "reasoning": "Small position with no timing correlation to news. Pure speculation."}
"""

SYSTEM_PROMPT = """You are Sentinel's Stage 1 Triage Classifier. Your job is to rapidly classify trading anomalies into one of four categories based on the evidence.

CLASSIFICATIONS:
1. INSIDER - Material non-public information. Indicators: fresh wallet, trade BEFORE any public signals, high conviction.
2. OSINT_EDGE - Superior public intelligence. Indicators: established wallet, public signals BEFORE trade, research-based.
3. FAST_REACTOR - Quick reaction to news. Indicators: trade placed AFTER news breaks (minutes), normal behavior.
4. SPECULATOR - No edge. Indicators: no timing correlation, random outcomes, normal position sizes.

SCORING:
- BSS (Behavioral Suspicion Score, 0-100): How suspicious is the wallet's behavior? Higher = more suspicious.
- PES (Public Explainability Score, 0-100): Could public information explain this trade? Higher = more explainable.

IMPORTANT RULES:
- If hours_before_news is negative and > 2 hours, and osint_signals_before_trade is 0, lean toward INSIDER
- If hours_before_news is positive and osint_signals_before_trade > 0, lean toward OSINT_EDGE
- If hours_before_news is very small and positive (0 <= x < 0.1), it's likely FAST_REACTOR
- Fresh wallets (< 7 days, < 5 trades) are suspicious
- Always output valid JSON

""" + FEW_SHOT_EXAMPLES


# Fine-tuned model ID (set after fine-tuning completes)
# Format: "ft:mistral-small-latest:sentinel-v1:xxx"
FINETUNED_MODEL_ID = os.getenv("SENTINEL_FINETUNED_MODEL", None)


def classify_anomaly(
    anomaly: Dict[str, Any],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    use_finetuned: bool = True,
) -> TriageResult:
    """
    Classify an anomaly using Mistral Small (or fine-tuned model).

    Args:
        anomaly: Dict with wallet_age_days, wallet_trades, trade_size_usd,
                 hours_before_news, osint_signals_before_trade, z_score
        api_key: Mistral API key (uses env var if not provided)
        model: Model to use (defaults to fine-tuned if available, else mistral-small-latest)
        use_finetuned: Whether to prefer the fine-tuned model (default True)

    Returns:
        TriageResult with classification and scores
    """
    api_key = api_key or os.getenv("MISTRAL_API_KEY")
    if not api_key:
        # Return a reasonable default for demo purposes
        return _classify_with_rules(anomaly)

    # Select model: prefer fine-tuned if available and requested
    if model is None:
        if use_finetuned and FINETUNED_MODEL_ID:
            model = FINETUNED_MODEL_ID
            logger.info(f"Using fine-tuned model: {model}")
        else:
            model = "mistral-small-latest"
    try:
        from mistralai import Mistral
    except ImportError:
        logger.warning("mistralai package not installed; falling back to rule-based classifier")
        return _classify_with_rules(anomaly)

    client = Mistral(api_key=api_key)

    # Prepare input
    input_data = {
        "wallet_age_days": anomaly.get("wallet_age_days", 30),
        "wallet_trades": anomaly.get("wallet_trades", 10),
        "trade_size_usd": anomaly.get("trade_size_usd", 1000),
        "hours_before_news": anomaly.get("hours_before_news"),
        "osint_signals_before_trade": anomaly.get("osint_signals_before_trade", 0),
        "z_score": anomaly.get("z_score", 1.0),
    }

    user_prompt = f"Classify this trading anomaly:\nInput: {json.dumps(input_data)}\nOutput:"

    try:
        response = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=500,
        )

        result_text = response.choices[0].message.content.strip()

        # Parse JSON from response
        # Handle potential markdown code blocks
        if "```" in result_text:
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()

        result = json.loads(result_text)

        return TriageResult(
            classification=result.get("classification", "SPECULATOR"),
            bss_score=result.get("bss_score", 50),
            pes_score=result.get("pes_score", 50),
            confidence=result.get("confidence", 0.5),
            reasoning=result.get("reasoning", "No reasoning provided"),
        )

    except Exception as e:
        logger.warning("Mistral API error; using rule fallback: %s", e)
        return _classify_with_rules(anomaly)


def _classify_with_rules(anomaly: Dict[str, Any]) -> TriageResult:
    """
    Rule-based fallback classifier when API is unavailable.

    Uses heuristics based on the classification criteria.
    """
    wallet_age = anomaly.get("wallet_age_days", 30)
    wallet_trades = anomaly.get("wallet_trades", 10)
    hours_before_news = anomaly.get("hours_before_news")
    osint_signals = anomaly.get("osint_signals_before_trade", 0)
    if hours_before_news is not None:
        try:
            hours_before_news = float(hours_before_news)
        except (TypeError, ValueError):
            hours_before_news = None
    # Fresh wallet indicators
    is_fresh_wallet = wallet_age < 7 and wallet_trades < 5

    # Determine classification
    if hours_before_news is None:
        # No news correlation
        classification = "SPECULATOR"
        bss_score = 20
        pes_score = 50
        confidence = 0.8
        reasoning = "No timing correlation with news events. Classified as speculation."

    elif hours_before_news < -2 and osint_signals == 0:
        # Trade significantly before news with no public signals
        classification = "INSIDER"
        bss_score = min(95, 60 + abs(hours_before_news) * 3 + (20 if is_fresh_wallet else 0))
        pes_score = max(5, 30 - abs(hours_before_news) * 2)
        confidence = 0.85 + (0.1 if is_fresh_wallet else 0)
        reasoning = f"Trade placed {abs(hours_before_news):.1f} hours before news with no public signals."
        if is_fresh_wallet:
            reasoning += " Fresh wallet increases suspicion."

    elif 0 <= hours_before_news < 0.1:
        # Trade very close after news (within ~6 minutes)
        classification = "FAST_REACTOR"
        bss_score = 15
        pes_score = 95
        confidence = 0.9
        reasoning = "Trade placed within minutes after news breaking. Normal fast reaction."

    elif hours_before_news > 0 and osint_signals > 0:
        # Trade after public signals available
        classification = "OSINT_EDGE"
        bss_score = max(10, 40 - osint_signals * 10)
        pes_score = min(95, 60 + osint_signals * 10)
        confidence = 0.85
        reasoning = f"Trade placed after {osint_signals} public signals. Legitimate research edge."

    else:
        # Edge cases
        if is_fresh_wallet and hours_before_news < 0:
            classification = "INSIDER"
            bss_score = 75
            pes_score = 25
            confidence = 0.7
            reasoning = "Fresh wallet with pre-news trading. Suspicious but not definitive."
        else:
            classification = "SPECULATOR"
            bss_score = 30
            pes_score = 45
            confidence = 0.6
            reasoning = "Mixed signals. Defaulting to speculation classification."

    return TriageResult(
        classification=classification,
        bss_score=int(bss_score),
        pes_score=int(pes_score),
        confidence=confidence,
        reasoning=reasoning,
    )


def batch_classify(anomalies: list[Dict[str, Any]], use_api: bool = True) -> list[TriageResult]:
    """
    Classify multiple anomalies.

    Args:
        anomalies: List of anomaly dicts
        use_api: Whether to use Mistral API (vs rule-based fallback)

    Returns:
        List of TriageResults
    """
    results = []
    for anomaly in anomalies:
        if use_api:
            result = classify_anomaly(anomaly)
        else:
            result = _classify_with_rules(anomaly)
        results.append(result)
    return results


if __name__ == "__main__":
    # Test the classifier
    print("Testing Stage 1 Triage Classifier...")

    test_cases = [
        {
            "name": "Classic Insider",
            "wallet_age_days": 2,
            "wallet_trades": 1,
            "trade_size_usd": 50000,
            "hours_before_news": -8,
            "osint_signals_before_trade": 0,
            "z_score": 4.5,
        },
        {
            "name": "OSINT Edge",
            "wallet_age_days": 180,
            "wallet_trades": 45,
            "trade_size_usd": 15000,
            "hours_before_news": 6,
            "osint_signals_before_trade": 3,
            "z_score": 2.1,
        },
        {
            "name": "Fast Reactor",
            "wallet_age_days": 90,
            "wallet_trades": 20,
            "trade_size_usd": 5000,
            "hours_before_news": -0.05,
            "osint_signals_before_trade": 1,
            "z_score": 1.0,
        },
        {
            "name": "Speculator",
            "wallet_age_days": 60,
            "wallet_trades": 12,
            "trade_size_usd": 800,
            "hours_before_news": None,
            "osint_signals_before_trade": 0,
            "z_score": 0.4,
        },
    ]

    print("\n📊 Rule-based classification (no API):")
    for case in test_cases:
        name = case.pop("name")
        result = _classify_with_rules(case)
        print(f"\n  {name}:")
        print(f"    Classification: {result.classification}")
        print(f"    BSS: {result.bss_score}, PES: {result.pes_score}")
        print(f"    Confidence: {result.confidence:.2f}")
        print(f"    Reasoning: {result.reasoning}")
        case["name"] = name  # Restore for next test

    # Test with API if key available
    if os.getenv("MISTRAL_API_KEY"):
        print("\n🤖 API-based classification:")
        for case in test_cases[:1]:  # Just test one to save API calls
            name = case.pop("name")
            result = classify_anomaly(case)
            print(f"\n  {name}:")
            print(f"    Classification: {result.classification}")
            print(f"    BSS: {result.bss_score}, PES: {result.pes_score}")
            print(f"    Reasoning: {result.reasoning}")
    else:
        print("\n⚠️ MISTRAL_API_KEY not set - skipping API test")
