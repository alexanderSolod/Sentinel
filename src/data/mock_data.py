"""
Sentinel Mock Data Generator
Creates realistic demo cases for all 4 classification types.
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

from src.data.database import (
    get_connection,
    init_schema,
    insert_anomaly,
    insert_osint_event,
    insert_evidence_packet,
    upsert_wallet,
    insert_case,
)


def generate_uuid() -> str:
    return str(uuid.uuid4())[:8]


def random_date(days_ago_start: int = 30, days_ago_end: int = 1) -> datetime:
    """Generate a random datetime within the specified range."""
    days_ago = random.randint(days_ago_end, days_ago_start)
    hours_ago = random.randint(0, 23)
    return datetime.now() - timedelta(days=days_ago, hours=hours_ago)


def generate_wallet_address() -> str:
    """Generate a realistic-looking wallet address."""
    return "0x" + "".join(random.choices("0123456789abcdef", k=40))


# ============================================================
# Demo Case Definitions
# ============================================================

DEMO_CASES = [
    # INSIDER Cases - Trade happens BEFORE any public information
    {
        "classification": "INSIDER",
        "market_name": "Will the US announce new China tariffs before March 1?",
        "market_id": "tariff-china-march",
        "scenario": "Wallet bought YES shares 6 hours before White House announcement. No public signals existed.",
        "trade_before_news_hours": -6,  # Negative = trade happened BEFORE news
        "bss_score": 92,
        "pes_score": 8,
        "wallet_age_days": 3,
        "wallet_trades": 2,
        "trade_size_usd": 47500,
        "price_before": 0.35,
        "price_after": 0.89,
        "z_score": 4.2,
        "osint_signals": [],  # No signals before trade
        "news_headline": "White House announces 25% tariffs on Chinese goods",
        "xai_narrative": """**Classification: INSIDER**

This trade exhibits classic insider trading characteristics:

1. **Timing**: The wallet purchased 47,500 USDC worth of YES shares exactly 6 hours before the White House press release. No public information about the tariff decision existed at trade time.

2. **Wallet Profile**: Fresh wallet (3 days old, only 2 prior trades) - a common pattern for actors trying to obscure their trading history.

3. **Information Gap**: Zero OSINT signals were available before this trade. The first public indication came from the official announcement.

4. **Price Impact**: The trade was placed at 35 cents when the market resolved at 89 cents, representing a 154% return.

**Fraud Triangle Analysis:**
- **Pressure**: High-stakes trade ($47.5K) suggests strong conviction from non-public knowledge
- **Opportunity**: Fresh wallet suggests awareness of need to hide identity
- **Rationalization**: None evident - appears to be pure profit motive""",
        "fraud_triangle": {
            "pressure": "High conviction trade ($47.5K) with no public information to justify position",
            "opportunity": "Fresh wallet creation suggests intent to obscure trading history",
            "rationalization": "No evident rationalization - pure profit-seeking behavior"
        }
    },
    {
        "classification": "INSIDER",
        "market_name": "Will Company X announce acquisition before Q1?",
        "market_id": "compx-acquisition",
        "scenario": "Cluster of 5 wallets all bought within 30 minutes, 12 hours before deal announced.",
        "trade_before_news_hours": -12,
        "bss_score": 95,
        "pes_score": 5,
        "wallet_age_days": 1,
        "wallet_trades": 1,
        "trade_size_usd": 125000,
        "price_before": 0.22,
        "price_after": 0.95,
        "z_score": 5.8,
        "osint_signals": [],
        "news_headline": "Company X confirms $2.3B acquisition deal",
        "xai_narrative": """**Classification: INSIDER**

Coordinated trading activity strongly suggests insider knowledge:

1. **Cluster Detection**: DBSCAN analysis identified 5 wallets trading within a 30-minute window, all taking identical YES positions. Combined volume: $125,000.

2. **Timing**: All trades occurred 12 hours before Bloomberg broke the acquisition news. No rumors or leaks were detectable.

3. **Wallet Pattern**: All 5 wallets were created within 24 hours of the trade - classic "burn wallet" behavior.

4. **Return**: 332% profit realized when market resolved at 95 cents vs. 22 cent entry.

**Fraud Triangle Analysis:**
- **Pressure**: Coordinated large position suggests organized effort
- **Opportunity**: Multiple fresh wallets indicate sophisticated actor
- **Rationalization**: N/A - clear profit motive""",
        "fraud_triangle": {
            "pressure": "Coordinated $125K position across 5 wallets indicates organized insider ring",
            "opportunity": "Fresh wallet cluster created specifically for this trade",
            "rationalization": "None - sophisticated actors aware of implications"
        }
    },
    {
        "classification": "INSIDER",
        "market_name": "Will Senator resign before ethics hearing?",
        "market_id": "senator-resign",
        "scenario": "Large YES position taken 8 hours before resignation announcement.",
        "trade_before_news_hours": -8,
        "bss_score": 88,
        "pes_score": 12,
        "wallet_age_days": 5,
        "wallet_trades": 3,
        "trade_size_usd": 32000,
        "price_before": 0.18,
        "price_after": 0.99,
        "z_score": 3.9,
        "osint_signals": [],
        "news_headline": "Senator announces surprise resignation citing family reasons",
        "xai_narrative": """**Classification: INSIDER**

This case shows strong indicators of advance knowledge:

1. **Timing Anomaly**: $32,000 YES position at 18% odds, 8 hours before surprise resignation. The resignation was genuinely unexpected - even political analysts were caught off guard.

2. **No Public Signals**: No OSINT sources showed any indication of resignation. Ethics hearing was scheduled but no resignation was anticipated.

3. **Wallet Behavior**: While not brand new (5 days), this wallet's pattern shows it was dormant until this specific trade.

4. **Return**: 450% profit on market resolution.

**Fraud Triangle Analysis:**
- **Pressure**: Political insider likely with access to staff communications
- **Opportunity**: Low public attention on this market made detection less likely
- **Rationalization**: May have rationalized as "everyone does it" in political circles""",
        "fraud_triangle": {
            "pressure": "Likely political insider with non-public access to staff decisions",
            "opportunity": "Obscure market with limited monitoring attention",
            "rationalization": "Political environment may normalize information asymmetry"
        }
    },

    # OSINT_EDGE Cases - Trade happens AFTER public signals (but before most noticed)
    {
        "classification": "OSINT_EDGE",
        "market_name": "Will Hurricane make landfall in Florida before Oct 15?",
        "market_id": "hurricane-florida",
        "scenario": "Trader bought YES after spotting obscure NOAA buoy data 18 hours before mainstream coverage.",
        "trade_before_news_hours": 2,  # Positive = trade happened AFTER some public info
        "bss_score": 35,
        "pes_score": 78,
        "wallet_age_days": 180,
        "wallet_trades": 47,
        "trade_size_usd": 15000,
        "price_before": 0.42,
        "price_after": 0.91,
        "z_score": 2.1,
        "osint_signals": [
            {"source": "NOAA", "headline": "Buoy #41047 reports pressure drop", "hours_before_trade": 2},
            {"source": "Weather Underground", "headline": "Tropical disturbance strengthening", "hours_before_trade": 4},
        ],
        "news_headline": "CNN: Category 3 Hurricane on direct path to Tampa",
        "xai_narrative": """**Classification: OSINT_EDGE**

This trade represents legitimate public intelligence gathering:

1. **OSINT Trail**: The trader acted on publicly available NOAA buoy data showing atmospheric pressure drops consistent with storm intensification. This data was public but required expertise to interpret.

2. **Established Wallet**: 180-day-old wallet with 47 prior trades and 68% win rate - consistent with a skilled research-based trader.

3. **Temporal Gap**: Trade occurred 2 hours AFTER the first public signals (NOAA buoy data) but 18 hours BEFORE mainstream media coverage.

4. **Skillful Research**: Connecting raw meteorological data to prediction market outcomes requires domain expertise - this is the definition of OSINT edge.

**Verdict**: Legitimate alpha from superior public information processing.""",
        "fraud_triangle": {
            "pressure": "N/A - legitimate trading behavior",
            "opportunity": "N/A - public information was used",
            "rationalization": "N/A - ethical trading based on research"
        }
    },
    {
        "classification": "OSINT_EDGE",
        "market_name": "Will EU approve merger before deadline?",
        "market_id": "eu-merger",
        "scenario": "Trader identified positive signals in obscure EU Commission procedural filings.",
        "trade_before_news_hours": 6,
        "bss_score": 28,
        "pes_score": 85,
        "wallet_age_days": 365,
        "wallet_trades": 112,
        "trade_size_usd": 8500,
        "price_before": 0.55,
        "price_after": 0.88,
        "z_score": 1.8,
        "osint_signals": [
            {"source": "EU Commission Portal", "headline": "Phase II review timeline extended", "hours_before_trade": 8},
            {"source": "Reuters Brussels", "headline": "Sources: remedies package under review", "hours_before_trade": 6},
        ],
        "news_headline": "EU approves major tech merger with conditions",
        "xai_narrative": """**Classification: OSINT_EDGE**

Exemplary research-based trading:

1. **Document Analysis**: Trader identified signals in EU Commission procedural filings that indicated positive momentum - specifically the timeline extension and remedies discussion.

2. **Expert Profile**: This wallet (1+ year old, 112 trades) shows consistent activity in regulatory/merger markets with above-average success rate.

3. **Public Information**: All signals were from official EU channels and wire services - entirely public but requiring expertise to interpret.

4. **Reasonable Position**: $8.5K position size is consistent with confident but not reckless trading.

**Verdict**: This is what prediction markets are designed to reward - informed participants who do superior research.""",
        "fraud_triangle": {
            "pressure": "N/A",
            "opportunity": "N/A",
            "rationalization": "N/A"
        }
    },

    # FAST_REACTOR Cases - Trade happens shortly AFTER news breaks
    {
        "classification": "FAST_REACTOR",
        "market_name": "Will Fed raise rates in March meeting?",
        "market_id": "fed-rates-march",
        "scenario": "Trader reacted within 3 minutes of FOMC statement release.",
        "trade_before_news_hours": 0.05,  # ~3 minutes after news
        "bss_score": 15,
        "pes_score": 95,
        "wallet_age_days": 90,
        "wallet_trades": 28,
        "trade_size_usd": 5000,
        "price_before": 0.72,
        "price_after": 0.98,
        "z_score": 1.2,
        "osint_signals": [
            {"source": "Federal Reserve", "headline": "FOMC announces 25bp rate hike", "hours_before_trade": -0.05},
        ],
        "news_headline": "Fed raises rates by 25 basis points, signals more to come",
        "xai_narrative": """**Classification: FAST_REACTOR**

This is legitimate fast reaction to breaking news:

1. **Timing**: Trade executed 3 minutes after the FOMC statement was released. This is within normal human reaction time for a prepared trader watching the announcement.

2. **Public Event**: FOMC announcements are public, scheduled events. The trader simply acted faster than most market participants.

3. **Normal Profile**: 90-day wallet with moderate trading history - not indicative of suspicious behavior.

4. **Market Efficiency**: This type of fast reaction is expected and healthy for market efficiency.

**Verdict**: Normal market behavior. No suspicion warranted.""",
        "fraud_triangle": {
            "pressure": "N/A",
            "opportunity": "N/A",
            "rationalization": "N/A"
        }
    },
    {
        "classification": "FAST_REACTOR",
        "market_name": "Will team win championship game?",
        "market_id": "championship-game",
        "scenario": "Trader bet on winner 2 minutes after injury was shown on live TV.",
        "trade_before_news_hours": 0.03,  # ~2 minutes after news
        "bss_score": 12,
        "pes_score": 98,
        "wallet_age_days": 200,
        "wallet_trades": 65,
        "trade_size_usd": 2500,
        "price_before": 0.45,
        "price_after": 0.78,
        "z_score": 1.0,
        "osint_signals": [
            {"source": "ESPN Live", "headline": "Star player leaves game with apparent injury", "hours_before_trade": -0.03},
        ],
        "news_headline": "Underdog wins after opponent's star player injured",
        "xai_narrative": """**Classification: FAST_REACTOR**

Legitimate live event trading:

1. **Live Information**: The injury was broadcast on live television to millions of viewers. The trader simply acted on this public information faster than the market adjusted.

2. **Normal Behavior**: This is exactly how sports betting markets are supposed to work - prices adjust as new information becomes available.

3. **Established Trader**: Long wallet history with sports market focus.

**Verdict**: Standard fast reaction trading. No concerns.""",
        "fraud_triangle": {
            "pressure": "N/A",
            "opportunity": "N/A",
            "rationalization": "N/A"
        }
    },

    # SPECULATOR Cases - Random trading with no edge
    {
        "classification": "SPECULATOR",
        "market_name": "Will it rain in London on New Year's Day?",
        "market_id": "london-rain-ny",
        "scenario": "Random bet with no apparent research or timing correlation.",
        "trade_before_news_hours": None,  # No news correlation
        "bss_score": 20,
        "pes_score": 45,
        "wallet_age_days": 60,
        "wallet_trades": 15,
        "trade_size_usd": 500,
        "price_before": 0.65,
        "price_after": 0.70,
        "z_score": 0.5,
        "osint_signals": [],
        "news_headline": None,
        "xai_narrative": """**Classification: SPECULATOR**

Standard speculative trading:

1. **No Edge Detected**: This trade shows no correlation with any news events or OSINT signals. It appears to be a pure speculation based on personal belief.

2. **Normal Profile**: Moderate wallet age and trading history with mixed results.

3. **Small Position**: $500 trade size is consistent with casual speculation.

**Verdict**: Normal speculative behavior. No flags.""",
        "fraud_triangle": {
            "pressure": "N/A",
            "opportunity": "N/A",
            "rationalization": "N/A"
        }
    },
    {
        "classification": "SPECULATOR",
        "market_name": "Will Bitcoin exceed $100K before June?",
        "market_id": "btc-100k",
        "scenario": "Contrarian bet against market consensus.",
        "trade_before_news_hours": None,
        "bss_score": 18,
        "pes_score": 40,
        "wallet_age_days": 120,
        "wallet_trades": 22,
        "trade_size_usd": 1200,
        "price_before": 0.28,
        "price_after": 0.25,
        "z_score": 0.3,
        "osint_signals": [],
        "news_headline": None,
        "xai_narrative": """**Classification: SPECULATOR**

Pure speculation on price prediction:

1. **Contrarian Bet**: Taking a minority position (YES at 28%) without any detected edge.

2. **No Timing Anomaly**: Trade timing shows no correlation with news or events.

3. **Reasonable Size**: Position size consistent with speculative risk-taking.

**Verdict**: Normal market speculation.""",
        "fraud_triangle": {
            "pressure": "N/A",
            "opportunity": "N/A",
            "rationalization": "N/A"
        }
    },
    {
        "classification": "SPECULATOR",
        "market_name": "Will next iPhone have satellite connectivity?",
        "market_id": "iphone-satellite",
        "scenario": "Tech enthusiast speculation based on public rumors.",
        "trade_before_news_hours": None,
        "bss_score": 22,
        "pes_score": 55,
        "wallet_age_days": 45,
        "wallet_trades": 8,
        "trade_size_usd": 750,
        "price_before": 0.40,
        "price_after": 0.42,
        "z_score": 0.4,
        "osint_signals": [
            {"source": "9to5Mac", "headline": "Rumor: Apple testing satellite features", "hours_before_trade": 48},
        ],
        "news_headline": None,
        "xai_narrative": """**Classification: SPECULATOR**

Speculation based on public rumors:

1. **Public Speculation**: Trade follows widely-circulated rumors about Apple's satellite plans - not proprietary information.

2. **No Timing Edge**: The rumor was public for 48+ hours before this trade, giving no informational advantage.

3. **Casual Position**: Small bet consistent with hobbyist interest in tech markets.

**Verdict**: Normal speculation on public rumors.""",
        "fraud_triangle": {
            "pressure": "N/A",
            "opportunity": "N/A",
            "rationalization": "N/A"
        }
    },
]


def seed_demo_data(db_path: str = None):
    """Seed the database with demo cases."""
    conn = get_connection(db_path) if db_path else get_connection()

    print(f"Seeding {len(DEMO_CASES)} demo cases...")

    for i, case_data in enumerate(DEMO_CASES):
        case_id = f"CASE-{generate_uuid()}"
        event_id = f"EVENT-{generate_uuid()}"
        wallet_address = generate_wallet_address()

        # Generate timestamps
        base_time = random_date(30, 5)

        if case_data["trade_before_news_hours"] is not None:
            trade_time = base_time
            # If negative, trade was before news (INSIDER)
            # If positive, trade was after some signal (OSINT_EDGE, FAST_REACTOR)
            news_time = base_time + timedelta(hours=abs(case_data["trade_before_news_hours"]))
            if case_data["trade_before_news_hours"] < 0:
                temporal_gap = abs(case_data["trade_before_news_hours"])
            else:
                temporal_gap = -case_data["trade_before_news_hours"]  # Negative means trade was AFTER signal
        else:
            trade_time = base_time
            news_time = None
            temporal_gap = None

        # Create wallet profile
        wallet = {
            "address": wallet_address,
            "first_seen": (datetime.now() - timedelta(days=case_data["wallet_age_days"])).isoformat(),
            "last_seen": trade_time.isoformat(),
            "trade_count": case_data["wallet_trades"],
            "win_count": int(case_data["wallet_trades"] * 0.6),
            "loss_count": int(case_data["wallet_trades"] * 0.4),
            "win_rate": 0.6,
            "total_volume": case_data["trade_size_usd"] * case_data["wallet_trades"],
            "avg_position_size": case_data["trade_size_usd"],
            "is_fresh_wallet": 1 if case_data["wallet_age_days"] < 7 else 0,
            "cluster_id": f"CLUSTER-{generate_uuid()}" if case_data["bss_score"] > 90 else None,
            "funding_chain": json.dumps(["tornado.cash" if case_data["bss_score"] > 85 else "coinbase"]),
            "suspicious_flags": json.dumps(["fresh_wallet"] if case_data["wallet_age_days"] < 7 else []),
        }
        upsert_wallet(conn, wallet)

        # Create OSINT events
        osint_event_ids = []
        for signal in case_data["osint_signals"]:
            osint_id = f"OSINT-{generate_uuid()}"
            signal_time = trade_time - timedelta(hours=signal["hours_before_trade"])
            osint_event = {
                "event_id": osint_id,
                "timestamp": signal_time.isoformat(),
                "source": signal["source"].lower().replace(" ", "_"),
                "source_url": f"https://{signal['source'].lower().replace(' ', '')}.com/article",
                "headline": signal["headline"],
                "content": f"Full article content for: {signal['headline']}",
                "category": "news",
                "geolocation": None,
                "relevance_score": 0.8,
                "embedding_id": f"emb-{generate_uuid()}",
                "related_market_ids": json.dumps([case_data["market_id"]]),
            }
            insert_osint_event(conn, osint_event)
            osint_event_ids.append(osint_id)

        # Create news event (if applicable)
        if news_time and case_data["news_headline"]:
            news_id = f"OSINT-{generate_uuid()}"
            news_event = {
                "event_id": news_id,
                "timestamp": news_time.isoformat(),
                "source": "major_news",
                "source_url": "https://news.example.com/breaking",
                "headline": case_data["news_headline"],
                "content": f"Breaking: {case_data['news_headline']}",
                "category": "breaking_news",
                "geolocation": None,
                "relevance_score": 1.0,
                "embedding_id": f"emb-{generate_uuid()}",
                "related_market_ids": json.dumps([case_data["market_id"]]),
            }
            insert_osint_event(conn, news_event)
            osint_event_ids.append(news_id)

        # Create anomaly event
        anomaly = {
            "event_id": event_id,
            "market_id": case_data["market_id"],
            "market_name": case_data["market_name"],
            "timestamp": trade_time.isoformat(),
            "trade_timestamp": trade_time.isoformat(),
            "wallet_address": wallet_address,
            "trade_size": case_data["trade_size_usd"],
            "position_side": "YES",
            "price_before": case_data["price_before"],
            "price_after": case_data["price_after"],
            "price_change": case_data["price_after"] - case_data["price_before"],
            "volume_24h": case_data["trade_size_usd"] * random.uniform(2, 5),
            "volume_spike_ratio": case_data["z_score"] + 1,
            "z_score": case_data["z_score"],
            "classification": case_data["classification"],
            "bss_score": case_data["bss_score"],
            "pes_score": case_data["pes_score"],
            "confidence": 0.85 + random.uniform(0, 0.14),
            "xai_narrative": case_data["xai_narrative"],
            "fraud_triangle_json": json.dumps(case_data["fraud_triangle"]),
        }
        insert_anomaly(conn, anomaly)

        # Create sentinel index case
        evidence = {
            "wallet_address": wallet_address,
            "wallet_age_days": case_data["wallet_age_days"],
            "wallet_trades": case_data["wallet_trades"],
            "trade_size_usd": case_data["trade_size_usd"],
            "price_before": case_data["price_before"],
            "price_after": case_data["price_after"],
            "z_score": case_data["z_score"],
            "osint_signals": case_data["osint_signals"],
            "osint_event_ids": osint_event_ids,
            "trade_timestamp": trade_time.isoformat(),
            "news_timestamp": news_time.isoformat() if news_time else None,
            "news_headline": case_data["news_headline"],
            "scenario": case_data["scenario"],
        }

        sentinel_case = {
            "case_id": case_id,
            "anomaly_event_id": event_id,
            "market_id": case_data["market_id"],
            "market_name": case_data["market_name"],
            "classification": case_data["classification"],
            "bss_score": case_data["bss_score"],
            "pes_score": case_data["pes_score"],
            "temporal_gap_hours": temporal_gap,
            "consensus_score": random.randint(60, 95) if case_data["classification"] == "INSIDER" else None,
            "status": "CONFIRMED" if case_data["classification"] == "INSIDER" and random.random() > 0.5 else "UNDER_REVIEW",
            "sar_report": generate_sar_report(case_data, wallet_address, trade_time, news_time),
            "xai_summary": case_data["xai_narrative"][:500] + "...",
            "evidence_json": json.dumps(evidence),
        }
        insert_case(conn, sentinel_case)

        # Create evidence packet for the case
        gap_minutes = abs(case_data["trade_before_news_hours"]) * 60 if case_data["trade_before_news_hours"] else None
        # Compute temporal gap score: higher = more suspicious (trade before signals)
        if gap_minutes is None:
            tg_score = 0.5
        elif case_data["trade_before_news_hours"] and case_data["trade_before_news_hours"] < 0:
            tg_score = round(min(1.0, 0.6 + min(gap_minutes, 360.0) / 360.0 * 0.4), 3)
        else:
            tg_score = round(max(0.05, 0.2 - gap_minutes / 600.0), 3)

        wallet_risk = round(case_data["bss_score"] / 100, 3)
        corr_score = round(0.3 * wallet_risk + 0.25 * tg_score + 0.2 * (1 if wallet.get("cluster_id") else 0) + 0.25 * (case_data["bss_score"] / 100), 3)

        first_osint_time = (trade_time - timedelta(hours=case_data["osint_signals"][0]["hours_before_trade"])).isoformat() if case_data["osint_signals"] else None

        evidence_packet = {
            "packet_id": f"PKT-{generate_uuid()}",
            "case_id": case_id,
            "event_id": event_id,
            "market_id": case_data["market_id"],
            "market_name": case_data["market_name"],
            "market_slug": case_data["market_id"],
            "wallet_address": wallet_address,
            "trade_timestamp": trade_time.isoformat(),
            "side": "buy",
            "outcome": "yes",
            "trade_size": float(case_data["trade_size_usd"]),
            "trade_price": case_data["price_before"],
            "wallet_age_hours": float(case_data["wallet_age_days"] * 24),
            "wallet_trade_count": case_data["wallet_trades"],
            "wallet_win_rate": 0.6,
            "wallet_risk_score": wallet_risk,
            "is_fresh_wallet": 1 if case_data["wallet_age_days"] < 7 else 0,
            "cluster_id": wallet.get("cluster_id"),
            "cluster_size": 6 if wallet.get("cluster_id") else 0,
            "cluster_confidence": 0.85 if wallet.get("cluster_id") else 0.0,
            "osint_event_id": osint_event_ids[0] if osint_event_ids else None,
            "osint_source": case_data["osint_signals"][0]["source"].lower().replace(" ", "_") if case_data["osint_signals"] else None,
            "osint_title": case_data["osint_signals"][0]["headline"] if case_data["osint_signals"] else None,
            "osint_timestamp": first_osint_time,
            "temporal_gap_minutes": gap_minutes,
            "temporal_gap_score": tg_score,
            "correlation_score": corr_score,
            "evidence_json": json.dumps({
                "risk_flags": json.loads(wallet.get("suspicious_flags", "[]")),
                "wallet_profile": {
                    "address": wallet_address,
                    "age_days": case_data["wallet_age_days"],
                    "trade_count": case_data["wallet_trades"],
                    "win_rate": 0.6,
                },
                "osint_event_count": len(osint_event_ids),
                "osint_signals_before_trade": len(case_data["osint_signals"]),
                "temporal_gap_minutes": gap_minutes,
                "temporal_gap_score": tg_score,
                "classification": {
                    "case_id": case_id,
                    "classification": case_data["classification"],
                    "bss_score": case_data["bss_score"],
                    "pes_score": case_data["pes_score"],
                },
            }),
        }
        insert_evidence_packet(conn, evidence_packet)

        print(f"  [{i+1}/{len(DEMO_CASES)}] Created {case_data['classification']} case: {case_data['market_name'][:50]}...")

    conn.commit()
    conn.close()
    print(f"\nSuccessfully seeded {len(DEMO_CASES)} demo cases!")


def generate_sar_report(case_data: Dict, wallet: str, trade_time: datetime, news_time: datetime) -> str:
    """Generate a Suspicious Activity Report for a case."""
    report = f"""# Suspicious Activity Report

## Executive Summary
**Classification**: {case_data['classification']}
**Market**: {case_data['market_name']}
**BSS Score**: {case_data['bss_score']}/100
**PES Score**: {case_data['pes_score']}/100

## Trade Details
- **Wallet**: `{wallet[:10]}...{wallet[-6:]}`
- **Trade Time**: {trade_time.strftime('%Y-%m-%d %H:%M UTC')}
- **Position**: YES @ ${case_data['price_before']:.2f}
- **Size**: ${case_data['trade_size_usd']:,.0f}
- **Resolution Price**: ${case_data['price_after']:.2f}
- **Return**: {((case_data['price_after'] - case_data['price_before']) / case_data['price_before'] * 100):.0f}%

## Scenario
{case_data['scenario']}

## Evidence Timeline
"""
    if news_time:
        report += f"- **Trade Placed**: {trade_time.strftime('%Y-%m-%d %H:%M UTC')}\n"
        report += f"- **News Broke**: {news_time.strftime('%Y-%m-%d %H:%M UTC')}\n"
        if case_data['trade_before_news_hours'] and case_data['trade_before_news_hours'] < 0:
            report += f"- **Temporal Gap**: Trade was {abs(case_data['trade_before_news_hours'])} hours BEFORE any public information\n"

    report += f"""
## Fraud Triangle Analysis
- **Pressure**: {case_data['fraud_triangle']['pressure']}
- **Opportunity**: {case_data['fraud_triangle']['opportunity']}
- **Rationalization**: {case_data['fraud_triangle']['rationalization']}

## Recommendation
"""
    if case_data['classification'] == 'INSIDER':
        report += "This case warrants further investigation. Recommend flagging wallet for monitoring and potential referral to compliance."
    elif case_data['classification'] == 'OSINT_EDGE':
        report += "No further action required. This represents legitimate research-based trading."
    else:
        report += "No action required. Normal market behavior."

    return report


if __name__ == "__main__":
    print("Initializing database schema...")
    init_schema()

    print("\nSeeding demo data...")
    seed_demo_data()

    # Verify
    from src.data.database import get_stats
    conn = get_connection()
    stats = get_stats(conn)
    conn.close()

    print("\nDatabase stats after seeding:")
    print(f"  Total anomalies: {stats['total_anomalies']}")
    print(f"  Total OSINT events: {stats['total_osint_events']}")
    print(f"  Total wallets: {stats['total_wallets']}")
    print(f"  Total cases: {stats['total_cases']}")
    print(f"  Cases by classification: {stats['cases_by_classification']}")
