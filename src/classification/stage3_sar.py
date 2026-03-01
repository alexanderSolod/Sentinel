"""
Stage 3: SAR (Suspicious Activity Report) Generator
Uses Mistral Large to generate formal structured reports for the Sentinel Index.

SAR reports are the final output of the classification pipeline and are stored
in the Sentinel Index as permanent records of detected anomalies.
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SARReport:
    """Structured Suspicious Activity Report."""
    case_id: str
    generated_at: str
    classification: str
    severity: str  # HIGH, MEDIUM, LOW
    executive_summary: str
    timeline: str
    evidence: str
    fraud_analysis: str
    conclusion: str
    recommendations: str
    full_report: str  # Complete markdown report


SYSTEM_PROMPT = """You are Sentinel's SAR (Suspicious Activity Report) Generator. Your role is to produce formal, structured reports that document potential market manipulation cases.

Your reports will be:
1. Stored in the public Sentinel Index
2. Reviewed by compliance teams and regulators
3. Used to train future detection models
4. Referenced by journalists and researchers

Report Structure:
1. Executive Summary (2-3 sentences)
2. Evidence Timeline (chronological bullet points)
3. Fraud Analysis (applying the Fraud Triangle)
4. Classification Rationale
5. Confidence Assessment
6. Recommendations

Be formal, objective, and evidence-based. Avoid speculation beyond the evidence.
"""


def generate_sar(
    anomaly: Dict[str, Any],
    triage_result: Dict[str, Any],
    magistral_result: Dict[str, Any],
    case_id: str,
    api_key: Optional[str] = None,
    model: str = "mistral-large-latest"
) -> SARReport:
    """
    Generate a Suspicious Activity Report.

    Args:
        anomaly: The anomaly event data
        triage_result: Stage 1 classification result
        magistral_result: Stage 2 deep analysis result
        case_id: Unique identifier for this case
        api_key: Mistral API key
        model: Model to use

    Returns:
        SARReport with full documentation
    """
    api_key = api_key or os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return _generate_sar_template(anomaly, triage_result, magistral_result, case_id)
    try:
        from mistralai import Mistral
    except ImportError:
        logger.warning("mistralai package not installed; falling back to SAR template")
        return _generate_sar_template(anomaly, triage_result, magistral_result, case_id)

    client = Mistral(api_key=api_key)

    prompt = _build_sar_prompt(anomaly, triage_result, magistral_result, case_id)

    try:
        response = client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=3000,
        )

        report_text = response.choices[0].message.content.strip()
        return _parse_sar_response(report_text, anomaly, triage_result, case_id)

    except Exception as e:
        logger.warning("SAR generation API error; using template fallback: %s", e)
        return _generate_sar_template(anomaly, triage_result, magistral_result, case_id)


def _build_sar_prompt(
    anomaly: Dict[str, Any],
    triage_result: Dict[str, Any],
    magistral_result: Dict[str, Any],
    case_id: str
) -> str:
    """Build the SAR generation prompt."""

    return f"""Generate a formal Suspicious Activity Report for the following case:

## Case Information
- **Case ID**: {case_id}
- **Market**: {anomaly.get('market_name', 'Unknown')}
- **Classification**: {triage_result.get('classification', 'Unknown')}
- **BSS Score**: {triage_result.get('bss_score', 50)}/100
- **PES Score**: {triage_result.get('pes_score', 50)}/100

## Trade Details
- **Wallet**: {anomaly.get('wallet_address', 'Unknown')[:16]}...
- **Trade Time**: {anomaly.get('trade_timestamp', anomaly.get('timestamp', 'Unknown'))}
- **Position**: {anomaly.get('position_side', 'YES')}
- **Entry Price**: ${anomaly.get('price_before', 0):.2f}
- **Resolution Price**: ${anomaly.get('price_after', 0):.2f}
- **Trade Size**: ${anomaly.get('trade_size', 0):,.0f}
- **Z-Score**: {anomaly.get('z_score', 0):.2f}

## Stage 2 Analysis Summary
{magistral_result.get('xai_narrative', 'No detailed analysis available.')[:1000]}

## Fraud Triangle Analysis
- **Pressure**: {magistral_result.get('fraud_triangle', {}).get('pressure', 'N/A')}
- **Opportunity**: {magistral_result.get('fraud_triangle', {}).get('opportunity', 'N/A')}
- **Rationalization**: {magistral_result.get('fraud_triangle', {}).get('rationalization', 'N/A')}

Generate a complete SAR with all required sections. Use markdown formatting.
"""


def _parse_sar_response(
    report_text: str,
    anomaly: Dict[str, Any],
    triage_result: Dict[str, Any],
    case_id: str
) -> SARReport:
    """Parse API response into structured SAR."""

    classification = triage_result.get("classification", "SPECULATOR")

    # Determine severity
    bss = triage_result.get("bss_score", 50)
    if classification == "INSIDER" and bss > 80:
        severity = "HIGH"
    elif classification == "INSIDER" and bss > 60:
        severity = "MEDIUM"
    elif classification == "OSINT_EDGE":
        severity = "LOW"
    else:
        severity = "LOW"

    return SARReport(
        case_id=case_id,
        generated_at=datetime.now().isoformat(),
        classification=classification,
        severity=severity,
        executive_summary=_extract_section(report_text, "executive summary", report_text[:300]),
        timeline=_extract_section(report_text, "timeline", "Timeline not available"),
        evidence=_extract_section(report_text, "evidence", "Evidence summary not available"),
        fraud_analysis=_extract_section(report_text, "fraud", "Fraud analysis not available"),
        conclusion=_extract_section(report_text, "conclusion", "Classification: " + classification),
        recommendations=_extract_section(report_text, "recommendation", "Review recommended"),
        full_report=report_text
    )


def _extract_section(text: str, section_name: str, default: str) -> str:
    """Extract a section from the report text."""
    lines = text.split("\n")
    in_section = False
    section_content = []

    for line in lines:
        if section_name.lower() in line.lower() and ("#" in line or "**" in line):
            in_section = True
            continue
        elif in_section:
            if line.startswith("#") or line.startswith("**") and len(line) > 3:
                break
            section_content.append(line)

    if section_content:
        return "\n".join(section_content).strip()
    return default


def _generate_sar_template(
    anomaly: Dict[str, Any],
    triage_result: Dict[str, Any],
    magistral_result: Dict[str, Any],
    case_id: str
) -> SARReport:
    """
    Generate a template-based SAR when API is unavailable.
    """
    classification = triage_result.get("classification", "SPECULATOR")
    bss = triage_result.get("bss_score", 50)
    pes = triage_result.get("pes_score", 50)
    confidence = triage_result.get("confidence", 0.5)

    # Determine severity
    if classification == "INSIDER" and bss > 80:
        severity = "HIGH"
    elif classification == "INSIDER" and bss > 60:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    # Calculate return
    price_before = anomaly.get("price_before", 0)
    price_after = anomaly.get("price_after", 0)
    if price_before > 0:
        pct_return = ((price_after - price_before) / price_before) * 100
    else:
        pct_return = 0

    trade_time = anomaly.get("trade_timestamp", anomaly.get("timestamp", "Unknown"))

    # Build executive summary
    if classification == "INSIDER":
        executive_summary = f"This case involves a suspicious trade of ${anomaly.get('trade_size', 0):,.0f} placed before material information became public. The wallet profile and timing pattern are consistent with insider trading. BSS score of {bss}/100 indicates high behavioral suspicion."
    elif classification == "OSINT_EDGE":
        executive_summary = f"This case represents legitimate trading based on superior public intelligence gathering. The trader identified publicly available signals before acting. PES score of {pes}/100 indicates the trade is explainable by public information."
    elif classification == "FAST_REACTOR":
        executive_summary = f"This case involves a fast reaction to breaking news. The trade was executed within minutes of public information becoming available. No suspicious activity detected."
    else:
        executive_summary = f"This case represents standard market speculation with no detected edge or timing anomaly. No suspicious activity detected."

    # Build timeline
    timeline = f"""- **Trade Executed**: {trade_time}
- **Position**: {anomaly.get('position_side', 'YES')} at ${price_before:.2f}
- **Trade Size**: ${anomaly.get('trade_size', 0):,.0f}
- **Market Resolution**: ${price_after:.2f}
- **Return**: {pct_return:.0f}%"""

    # Build evidence
    evidence = f"""- Z-Score: {anomaly.get('z_score', 0):.2f} (standard deviations from normal)
- Wallet Age: {anomaly.get('wallet_age_days', 'Unknown')} days
- Total Wallet Trades: {anomaly.get('wallet_trades', 'Unknown')}
- BSS Score: {bss}/100
- PES Score: {pes}/100
- Classification Confidence: {confidence:.0%}"""

    # Build fraud analysis
    fraud = magistral_result.get("fraud_triangle", {})
    fraud_analysis = f"""**Fraud Triangle Assessment:**

- **Pressure**: {fraud.get('pressure', 'Not analyzed')}
- **Opportunity**: {fraud.get('opportunity', 'Not analyzed')}
- **Rationalization**: {fraud.get('rationalization', 'Not analyzed')}"""

    # Build conclusion
    if classification == "INSIDER":
        conclusion = f"Based on the evidence, this trade is classified as **{classification}** with {confidence:.0%} confidence. The timing pattern, wallet profile, and information gap strongly suggest access to material non-public information."
    else:
        conclusion = f"Based on the evidence, this trade is classified as **{classification}** with {confidence:.0%} confidence. No indicators of insider trading were detected."

    # Build recommendations
    if classification == "INSIDER" and bss > 80:
        recommendations = """1. Flag this wallet for ongoing monitoring
2. Cross-reference with other markets for pattern detection
3. Consider referral to compliance for further investigation
4. Add to the Sentinel Index as a confirmed high-severity case"""
    elif classification == "INSIDER":
        recommendations = """1. Add to the Sentinel Index for community review
2. Monitor wallet for similar patterns
3. Queue for Arena validation"""
    else:
        recommendations = "No action required. This case does not warrant further investigation."

    # Build full report
    full_report = f"""# Suspicious Activity Report

## Case Information
- **Case ID**: {case_id}
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
- **Classification**: {classification}
- **Severity**: {severity}
- **Market**: {anomaly.get('market_name', 'Unknown')}

## Executive Summary
{executive_summary}

## Evidence Timeline
{timeline}

## Key Evidence
{evidence}

## Fraud Triangle Analysis
{fraud_analysis}

## Conclusion
{conclusion}

## Recommendations
{recommendations}

---
*This report was generated by Sentinel, an AI-powered surveillance system for prediction market integrity.*
"""

    return SARReport(
        case_id=case_id,
        generated_at=datetime.now().isoformat(),
        classification=classification,
        severity=severity,
        executive_summary=executive_summary,
        timeline=timeline,
        evidence=evidence,
        fraud_analysis=fraud_analysis,
        conclusion=conclusion,
        recommendations=recommendations,
        full_report=full_report
    )


if __name__ == "__main__":
    # Test the SAR generator
    print("Testing Stage 3 SAR Generator...")

    test_anomaly = {
        "market_name": "Will the US announce new tariffs?",
        "market_id": "test-market-123",
        "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        "trade_timestamp": "2025-02-15T10:30:00Z",
        "position_side": "YES",
        "price_before": 0.35,
        "price_after": 0.89,
        "trade_size": 47500,
        "z_score": 4.2,
        "wallet_age_days": 3,
        "wallet_trades": 2,
    }

    test_triage = {
        "classification": "INSIDER",
        "bss_score": 92,
        "pes_score": 8,
        "confidence": 0.92,
        "reasoning": "Fresh wallet, trade before news, no public signals."
    }

    test_magistral = {
        "xai_narrative": "This case exhibits classic insider trading characteristics...",
        "fraud_triangle": {
            "pressure": "Financial incentive to capitalize on advance knowledge",
            "opportunity": "Fresh wallet obscures trading history",
            "rationalization": "Potential 'victimless crime' mentality"
        }
    }

    sar = _generate_sar_template(test_anomaly, test_triage, test_magistral, "CASE-TEST-001")

    print(f"\n📋 SAR Report Generated:")
    print(f"Case ID: {sar.case_id}")
    print(f"Classification: {sar.classification}")
    print(f"Severity: {sar.severity}")
    print(f"\n📄 Full Report:\n")
    print(sar.full_report)
