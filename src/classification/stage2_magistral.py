"""
Stage 2: Deep Analysis with Magistral
Uses Mistral's reasoning model for chain-of-thought analysis with Fraud Triangle mapping.

This stage provides:
- Detailed XAI (Explainable AI) narratives
- Fraud Triangle analysis (Pressure, Opportunity, Rationalization)
- Temporal gap analysis
- Evidence synthesis
"""
import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MagistralResult:
    """Result from Stage 2 Magistral analysis."""
    classification: str
    confidence: float
    xai_narrative: str
    fraud_triangle: Dict[str, str]
    temporal_analysis: str
    evidence_summary: List[str]
    recommendation: str


SYSTEM_PROMPT = """You are Sentinel's Stage 2 Deep Analyst, powered by Magistral reasoning capabilities.

Your role is to perform comprehensive analysis of trading anomalies that have been flagged for deeper review.

For each case, you must provide:

1. **XAI Narrative**: A detailed, human-readable explanation of why this case received its classification. This should be understandable to regulators, journalists, and market participants.

2. **Fraud Triangle Analysis**: Apply the classic fraud framework:
   - **Pressure**: What motivation or incentive existed? (financial gain, market position, competitive advantage)
   - **Opportunity**: What access or circumstances enabled this? (information access, market structure, anonymity)
   - **Rationalization**: How might the actor justify this behavior? (everyone does it, victimless crime, deserved gain)

3. **Temporal Gap Analysis**: Detailed breakdown of the timing between:
   - The suspicious trade
   - Available public information (OSINT signals)
   - News/resolution event

4. **Evidence Summary**: Bullet points of key evidence supporting the classification.

5. **Recommendation**: What action, if any, should be taken?

Be thorough, objective, and evidence-based. Your analysis will be used to build the public Sentinel Index.
"""


def analyze_case(
    anomaly: Dict[str, Any],
    triage_result: Dict[str, Any],
    osint_context: Optional[List[Dict]] = None,
    api_key: Optional[str] = None,
    model: str = "mistral-large-latest"  # Using large as Magistral proxy
) -> MagistralResult:
    """
    Perform deep analysis on a flagged case.

    Args:
        anomaly: The anomaly event data
        triage_result: Stage 1 triage classification result
        osint_context: Relevant OSINT events for RAG context
        api_key: Mistral API key
        model: Model to use (Magistral or Mistral Large)

    Returns:
        MagistralResult with detailed analysis
    """
    api_key = api_key or os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return _analyze_with_template(anomaly, triage_result, osint_context)
    try:
        from mistralai import Mistral
    except ImportError:
        logger.warning("mistralai package not installed; falling back to template analysis")
        return _analyze_with_template(anomaly, triage_result, osint_context)

    client = Mistral(api_key=api_key)

    # Build the analysis prompt
    prompt = _build_analysis_prompt(anomaly, triage_result, osint_context)

    try:
        response = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        result_text = response.choices[0].message.content.strip()
        return _parse_magistral_response(result_text, triage_result)

    except Exception as e:
        logger.warning("Magistral API error; using template fallback: %s", e)
        return _analyze_with_template(anomaly, triage_result, osint_context)


def _build_analysis_prompt(
    anomaly: Dict[str, Any],
    triage_result: Dict[str, Any],
    osint_context: Optional[List[Dict]]
) -> str:
    """Build the analysis prompt with all context."""

    prompt = f"""Analyze this prediction market trading anomaly:

## Case Overview
- **Market**: {anomaly.get('market_name', 'Unknown')}
- **Market ID**: {anomaly.get('market_id', 'Unknown')}
- **Trade Time**: {anomaly.get('trade_timestamp', anomaly.get('timestamp', 'Unknown'))}

## Trade Details
- **Wallet**: {anomaly.get('wallet_address', 'Unknown')[:10]}...
- **Position**: {anomaly.get('position_side', 'YES')} at ${anomaly.get('price_before', 0):.2f}
- **Trade Size**: ${anomaly.get('trade_size', 0):,.0f}
- **Resolution Price**: ${anomaly.get('price_after', 0):.2f}
- **Z-Score**: {anomaly.get('z_score', 0):.2f}

## Wallet Profile
- **Wallet Age**: {anomaly.get('wallet_age_days', 'Unknown')} days
- **Total Trades**: {anomaly.get('wallet_trades', 'Unknown')}
- **Win Rate**: {anomaly.get('win_rate', 'Unknown')}

## Stage 1 Triage Result
- **Classification**: {triage_result.get('classification', 'Unknown')}
- **BSS Score**: {triage_result.get('bss_score', 50)}/100
- **PES Score**: {triage_result.get('pes_score', 50)}/100
- **Confidence**: {triage_result.get('confidence', 0):.0%}
- **Initial Reasoning**: {triage_result.get('reasoning', 'None')}

"""

    if osint_context:
        prompt += "\n## OSINT Context (signals found near trade time)\n"
        for signal in osint_context[:5]:  # Limit to 5 signals
            prompt += f"- [{signal.get('timestamp', 'Unknown')}] {signal.get('source', 'Unknown')}: {signal.get('headline', 'No headline')}\n"

    prompt += """
## Your Task
Provide a comprehensive analysis including:
1. XAI Narrative (detailed explanation)
2. Fraud Triangle Analysis
3. Temporal Gap Analysis
4. Evidence Summary (bullet points)
5. Recommendation

Format your response with clear section headers.
"""

    return prompt


def _parse_magistral_response(response_text: str, triage_result: Dict) -> MagistralResult:
    """Parse the Magistral response into structured result."""

    # Extract sections from the response
    sections = {}
    current_section = "intro"
    current_content = []

    for line in response_text.split("\n"):
        line_lower = line.lower().strip()
        if "xai narrative" in line_lower or "narrative" in line_lower and "##" in line:
            if current_content:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "xai_narrative"
            current_content = []
        elif "fraud triangle" in line_lower and "##" in line:
            if current_content:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "fraud_triangle"
            current_content = []
        elif "temporal" in line_lower and "##" in line:
            if current_content:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "temporal"
            current_content = []
        elif "evidence" in line_lower and "##" in line:
            if current_content:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "evidence"
            current_content = []
        elif "recommendation" in line_lower and "##" in line:
            if current_content:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "recommendation"
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        sections[current_section] = "\n".join(current_content).strip()

    # Parse fraud triangle
    fraud_triangle = {"pressure": "N/A", "opportunity": "N/A", "rationalization": "N/A"}
    ft_text = sections.get("fraud_triangle", "")
    if "pressure" in ft_text.lower():
        lines = ft_text.split("\n")
        for line in lines:
            line_lower = line.lower()
            if "pressure" in line_lower:
                fraud_triangle["pressure"] = line.split(":", 1)[-1].strip() if ":" in line else line
            elif "opportunity" in line_lower:
                fraud_triangle["opportunity"] = line.split(":", 1)[-1].strip() if ":" in line else line
            elif "rationalization" in line_lower:
                fraud_triangle["rationalization"] = line.split(":", 1)[-1].strip() if ":" in line else line

    # Parse evidence bullets
    evidence = []
    ev_text = sections.get("evidence", "")
    for line in ev_text.split("\n"):
        line = line.strip()
        if line.startswith("-") or line.startswith("*") or line.startswith("•"):
            evidence.append(line.lstrip("-*• "))

    return MagistralResult(
        classification=triage_result.get("classification", "SPECULATOR"),
        confidence=triage_result.get("confidence", 0.5),
        xai_narrative=sections.get("xai_narrative", response_text[:1000]),
        fraud_triangle=fraud_triangle,
        temporal_analysis=sections.get("temporal", "No temporal analysis provided."),
        evidence_summary=evidence if evidence else ["Analysis completed"],
        recommendation=sections.get("recommendation", "Further review recommended.")
    )


def _analyze_with_template(
    anomaly: Dict[str, Any],
    triage_result: Dict[str, Any],
    osint_context: Optional[List[Dict]]
) -> MagistralResult:
    """
    Template-based analysis fallback when API is unavailable.
    """
    classification = triage_result.get("classification", "SPECULATOR")
    bss = triage_result.get("bss_score", 50)
    pes = triage_result.get("pes_score", 50)

    # Generate narrative based on classification
    if classification == "INSIDER":
        xai_narrative = f"""**Classification: INSIDER**

This case exhibits strong indicators of insider trading:

1. **Timing Anomaly**: The trade was placed before any public information about the outcome was available. With a BSS score of {bss}/100 and PES score of {pes}/100, the behavioral pattern is highly suspicious while public information cannot explain the trade.

2. **Wallet Profile**: {'Fresh wallet with minimal trading history - a common pattern for hiding insider activity.' if anomaly.get('wallet_age_days', 30) < 7 else 'Wallet profile analysis indicates deliberate positioning.'}

3. **Position Sizing**: The trade size of ${anomaly.get('trade_size', 0):,.0f} represents significant conviction without any publicly available justification.

4. **Z-Score**: A statistical z-score of {anomaly.get('z_score', 0):.1f} indicates this trading activity was {anomaly.get('z_score', 0):.1f} standard deviations from normal behavior.

**Conclusion**: This case warrants serious investigation and should be flagged in the Sentinel Index as potential insider trading."""

        fraud_triangle = {
            "pressure": f"Financial pressure to capitalize on non-public information. Trade size of ${anomaly.get('trade_size', 0):,.0f} suggests strong conviction.",
            "opportunity": f"Access to material non-public information. {'Fresh wallet suggests awareness of need to obscure identity.' if anomaly.get('wallet_age_days', 30) < 7 else 'Timing indicates advance knowledge.'}",
            "rationalization": "Potential rationalization: 'The market will find out anyway' or 'I deserve this for my access'"
        }

        recommendation = "This case should be flagged for further investigation. Recommend wallet monitoring and potential referral to compliance."

    elif classification == "OSINT_EDGE":
        xai_narrative = f"""**Classification: OSINT_EDGE**

This case represents legitimate public intelligence gathering:

1. **OSINT Trail**: Public signals were available before this trade was placed. The trader acted on publicly accessible information, albeit requiring skill to identify and interpret.

2. **Wallet Profile**: {'Established wallet with trading history suggests a research-based trading approach.' if anomaly.get('wallet_age_days', 30) > 30 else 'Wallet profile is consistent with active research trader.'}

3. **Timing**: Trade was placed AFTER public signals became available, demonstrating skill in identifying information rather than accessing non-public sources.

4. **Scores**: BSS {bss}/100 (low suspicion) and PES {pes}/100 (high explainability) confirm legitimate research edge.

**Conclusion**: This represents the market working as intended - rewarding superior research and information processing."""

        fraud_triangle = {
            "pressure": "N/A - Legitimate trading behavior",
            "opportunity": "N/A - Used publicly available information",
            "rationalization": "N/A - No ethical concerns"
        }

        recommendation = "No action required. This represents legitimate alpha from superior public information processing."

    elif classification == "FAST_REACTOR":
        xai_narrative = f"""**Classification: FAST_REACTOR**

This case represents normal fast reaction to breaking news:

1. **Timing**: Trade was executed within minutes of the news breaking, consistent with a prepared trader watching for announcements.

2. **Public Information**: The trade followed publicly available news. Speed of execution indicates preparedness, not advance knowledge.

3. **Wallet Profile**: Trading history is consistent with active market participant.

**Conclusion**: Normal market behavior. No suspicion warranted."""

        fraud_triangle = {
            "pressure": "N/A",
            "opportunity": "N/A",
            "rationalization": "N/A"
        }

        recommendation = "No action required. Fast reaction to public news is expected market behavior."

    else:  # SPECULATOR
        xai_narrative = f"""**Classification: SPECULATOR**

This case represents standard market speculation:

1. **No Edge Detected**: No timing correlation with news events or OSINT signals was detected.

2. **Normal Behavior**: Trading pattern is consistent with speculative market participation.

3. **Position Size**: Trade size of ${anomaly.get('trade_size', 0):,.0f} is within normal range.

**Conclusion**: Standard speculation with no indicators of information asymmetry."""

        fraud_triangle = {
            "pressure": "N/A",
            "opportunity": "N/A",
            "rationalization": "N/A"
        }

        recommendation = "No action required. Normal market speculation."

    # Build evidence summary
    evidence = [
        f"Classification: {classification} (Confidence: {triage_result.get('confidence', 0):.0%})",
        f"BSS Score: {bss}/100, PES Score: {pes}/100",
        f"Trade Size: ${anomaly.get('trade_size', 0):,.0f}",
        f"Z-Score: {anomaly.get('z_score', 0):.2f}",
    ]

    if osint_context:
        evidence.append(f"OSINT Signals: {len(osint_context)} related signals found")

    return MagistralResult(
        classification=classification,
        confidence=triage_result.get("confidence", 0.5),
        xai_narrative=xai_narrative,
        fraud_triangle=fraud_triangle,
        temporal_analysis=f"Trade timing analysis completed. Key metric: trade occurred with z-score {anomaly.get('z_score', 0):.2f}",
        evidence_summary=evidence,
        recommendation=recommendation
    )


if __name__ == "__main__":
    # Test the analyzer
    print("Testing Stage 2 Magistral Analyzer...")

    test_anomaly = {
        "market_name": "Will the US announce new tariffs?",
        "market_id": "test-market-123",
        "wallet_address": "0x1234567890abcdef",
        "trade_timestamp": "2025-02-15T10:30:00Z",
        "position_side": "YES",
        "price_before": 0.35,
        "price_after": 0.89,
        "trade_size": 47500,
        "z_score": 4.2,
        "wallet_age_days": 3,
        "wallet_trades": 2,
        "win_rate": 1.0,
    }

    test_triage = {
        "classification": "INSIDER",
        "bss_score": 92,
        "pes_score": 8,
        "confidence": 0.92,
        "reasoning": "Fresh wallet, trade before news, no public signals."
    }

    result = _analyze_with_template(test_anomaly, test_triage, None)

    print(f"\n📊 Analysis Result:")
    print(f"Classification: {result.classification}")
    print(f"\n🔍 XAI Narrative:\n{result.xai_narrative[:500]}...")
    print(f"\n🔺 Fraud Triangle:")
    for key, value in result.fraud_triangle.items():
        print(f"  {key.capitalize()}: {value[:100]}...")
    print(f"\n📋 Evidence:")
    for e in result.evidence_summary:
        print(f"  - {e}")
    print(f"\n💡 Recommendation: {result.recommendation}")
