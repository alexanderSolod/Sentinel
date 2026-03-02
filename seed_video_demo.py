"""
Sentinel Video Demo Seeder
Populates the database with the Iran strike case and supporting data
to match every screen shown in the launch video (script.md).

Usage:
    python seed_video_demo.py
"""
import json
import uuid
import random
from datetime import datetime, timedelta

from src.data.database import (
    get_connection,
    init_schema,
    insert_anomaly,
    insert_osint_event,
    insert_evidence_packet,
    upsert_wallet,
    insert_case,
    insert_vote,
    get_stats,
)


def uid() -> str:
    return str(uuid.uuid4())[:8]


def wallet_addr() -> str:
    return "0x" + "".join(random.choices("0123456789abcdef", k=40))


# ============================================================
# Constants — Iran Strike Case (matches script.md exactly)
# ============================================================

MARKET_ID = "us-iran-strike-feb28-2026"
MARKET_NAME = "Will the US conduct a military strike on Iran on February 28, 2025?"

# Trade at 02:00 UTC, news breaks at 08:00 UTC — 6-hour gap
TRADE_TIME = datetime(2025, 2, 28, 2, 0, 0)
NEWS_TIME = datetime(2025, 2, 28, 8, 0, 0)
TEMPORAL_GAP_HOURS = 6.0

# 6 wallets, $10K each = $60K total, resolved to $1.2M
NUM_WALLETS = 6
TRADE_SIZE_PER_WALLET = 10000.0
TOTAL_TRADE = 60000.0
TOTAL_PAYOUT = 1200000.0
PRICE_BEFORE = 0.05  # 5 cents (long-shot odds)
PRICE_AFTER = 1.00   # resolved YES

# Shared cluster — all 6 on same funding path
CLUSTER_ID = f"CLUSTER-iran6-{uid()}"
FUNDING_SOURCE = "0x" + "".join(random.choices("0123456789abcdef", k=40))  # common funder

# Primary case ID
CASE_ID = f"CASE-iran-{uid()}"
PRIMARY_EVENT_ID = f"EVENT-iran-{uid()}"


# ============================================================
# Iran Case: XAI Narrative (shown in Case Detail AI Analysis)
# ============================================================

XAI_NARRATIVE = """**Classification: INSIDER — High Confidence**

This case represents one of the most clear-cut examples of insider trading detected by Sentinel.

## Summary

Six brand-new wallets, all funded within hours of each other from the same origin address, placed coordinated bets totaling $60,000 on "YES — US strikes Iran on February 28" at 5-cent odds. Six hours later, the US launched airstrikes on Iranian military targets. The wallets collectively realized $1.2 million in profit.

## Evidence Chain

1. **Coordinated Fresh Wallets**: All six wallets were created on February 28, 2026, funded from a single source within a 45-minute window. None had any prior trading history on Polymarket.

2. **Extreme Specificity**: The wallets did not bet on "US-Iran conflict eventually" or "Iran strike in February." They purchased YES shares on the exact date — February 28 — at odds that implied the market considered this a 5% probability event.

3. **Temporal Gap**: The trades were placed at approximately 02:00 UTC. The first public report of the strikes appeared at 08:00 UTC. No publicly available intelligence — across news wires, GDELT, ACLED conflict data, NASA FIRMS satellite imagery, or GDACS disaster alerts — indicated an imminent strike prior to the trades.

4. **Behavioral Clustering**: DBSCAN analysis confirms all six wallets cluster together with 0.94 confidence. Identical funding chain, identical timing, identical target.

5. **Z-Score**: The combined volume anomaly registered at 4.7 standard deviations above baseline for this market.

## Conclusion

The combination of fresh wallets, coordinated funding, exact-date specificity, and a six-hour lead on public information constitutes overwhelming evidence of trading on material non-public information."""

FRAUD_TRIANGLE = {
    "pressure": "Financial incentive of $1.2 million across six coordinated wallets. The scale of the bet ($60,000 at 5-cent odds) indicates high conviction that could only come from material non-public information about the planned military operation.",
    "opportunity": "Six freshly created wallets funded from a single source on the same day, designed to distribute the position and avoid detection thresholds. The use of a prediction market — which lacks the surveillance infrastructure of traditional financial markets — provided the mechanism.",
    "rationalization": "The actor(s) likely viewed prediction markets as an unregulated grey area where insider trading enforcement does not apply. The use of multiple wallets suggests awareness that the activity was improper and an active attempt to obscure the trail."
}


# ============================================================
# Iran Case: SAR Report (shown in Case Detail expandable)
# ============================================================

SAR_REPORT = f"""# Suspicious Activity Report

## Case ID
{CASE_ID}

## Executive Summary
**Classification**: INSIDER
**Severity**: HIGH
**Market**: {MARKET_NAME}
**BSS Score**: 96/100
**PES Score**: 4/100

On February 28, 2025, six previously unseen wallets placed coordinated YES bets totaling $60,000 on the exact date of a US military strike on Iran. The strike occurred six hours after the trades were placed. No public intelligence sources contained advance warning. The wallets realized a combined profit of approximately $1.2 million.

## Timeline
- **2025-02-28 01:15 UTC** — First wallet funded from common origin address
- **2025-02-28 01:45 UTC** — All six wallets funded (45-minute window)
- **2025-02-28 02:00 UTC** — First trade placed: 200,000 YES shares @ $0.05
- **2025-02-28 02:03 UTC** — All six trades completed within 3-minute window
- **2025-02-28 02:05 UTC** — Sentinel triage flags anomaly (4.7σ, BSS 96)
- **2025-02-28 02:06 UTC** — Magistral escalation: INSIDER classification
- **2025-02-28 08:00 UTC** — Reuters reports US airstrikes on Iranian military sites
- **2025-02-28 08:15 UTC** — Market resolves YES, wallets begin claiming winnings

## Evidence
- **Wallet Cluster**: 6 wallets, DBSCAN confidence 0.94, identical funding path
- **Funding Chain**: All trace to single origin → Tornado Cash → individual wallets
- **OSINT Gap**: Zero relevant signals across 4 intelligence feeds prior to trade
- **Temporal Gap**: 6 hours between trade execution and first public report
- **Volume Anomaly**: 4.7 standard deviations above market baseline
- **Date Specificity**: Bets placed on exact date, not a date range

## Fraud Triangle Analysis
- **Pressure (Motive)**: {FRAUD_TRIANGLE['pressure']}
- **Opportunity (Means)**: {FRAUD_TRIANGLE['opportunity']}
- **Rationalization**: {FRAUD_TRIANGLE['rationalization']}

## Conclusion
This case meets all criteria for insider trading classification with high confidence. The combination of coordinated fresh wallets, exact-date specificity, tornado cash funding, six-hour advance positioning, and zero public intelligence constitutes a pattern that cannot be explained by speculation, research, or coincidence.

## Recommendations
1. Flag all six wallet addresses for permanent monitoring
2. Trace funding chain origin through Tornado Cash (requires on-chain forensics)
3. Cross-reference trade timing with known government personnel access patterns
4. Publish case to Sentinel Index for community review
5. Refer to relevant regulatory bodies if jurisdiction applies"""


# ============================================================
# Background OSINT Events (populates System Health OSINT feed)
# ============================================================

BACKGROUND_OSINT = [
    # Recent events across all 4 source types — makes the feed look alive
    {"source": "gdelt", "headline": "NATO allies discuss joint response to Middle East tensions", "category": "politics", "hours_ago": 2},
    {"source": "gdelt", "headline": "Oil prices surge 4% on geopolitical uncertainty", "category": "business", "hours_ago": 3},
    {"source": "gdelt", "headline": "US Defense Secretary holds press briefing on regional security", "category": "politics", "hours_ago": 5},
    {"source": "gdelt", "headline": "Iran foreign minister denies nuclear program escalation", "category": "politics", "hours_ago": 8},
    {"source": "gdelt", "headline": "Treasury yields rise amid global risk-off sentiment", "category": "business", "hours_ago": 10},
    {"source": "acled", "headline": "Houthi drone strike reported near Strait of Hormuz shipping lane", "category": "conflict", "hours_ago": 4},
    {"source": "acled", "headline": "Israeli military conducts overnight operation in southern Lebanon", "category": "conflict", "hours_ago": 7},
    {"source": "acled", "headline": "Protests in Baghdad over electricity shortages enter third day", "category": "conflict", "hours_ago": 12},
    {"source": "gdacs", "headline": "Magnitude 5.2 earthquake detected near Turkey-Iran border", "category": "disaster", "hours_ago": 6},
    {"source": "gdacs", "headline": "Flood warning issued for southeastern Pakistan", "category": "disaster", "hours_ago": 14},
    {"source": "nasa_firms", "headline": "Thermal anomaly detected: industrial fire near Bandar Abbas, Iran", "category": "satellite", "hours_ago": 9},
    {"source": "nasa_firms", "headline": "Agricultural burn activity elevated in Tigris river valley", "category": "satellite", "hours_ago": 16},
    {"source": "rss", "headline": "Polymarket volume hits record $45M in 24 hours on geopolitical markets", "category": "crypto", "hours_ago": 1},
    {"source": "rss", "headline": "Senator introduces bill to regulate prediction market platforms", "category": "politics", "hours_ago": 11},
    {"source": "gdelt", "headline": "Pentagon spokesperson declines to comment on troop movements", "category": "politics", "hours_ago": 15},
    {"source": "gdelt", "headline": "European markets open lower on Middle East escalation fears", "category": "business", "hours_ago": 18},
]

# The actual news that broke 6 hours after the trades
IRAN_NEWS_EVENT = {
    "source": "major_news",
    "headline": "BREAKING: US conducts airstrikes on Iranian military targets — Reuters",
    "content": "The United States launched a series of precision airstrikes against Iranian military installations in the early hours of February 28, according to Pentagon officials. The strikes targeted missile production facilities and command-and-control sites. Iran's foreign ministry condemned the attack as 'an act of aggression.' Oil futures spiked 8% in immediate aftermath.",
    "category": "breaking_news",
}


# ============================================================
# Background Cases (gives Sentinel Index depth)
# ============================================================

BACKGROUND_CASES = [
    {
        "classification": "OSINT_EDGE",
        "market_name": "Will Hurricane make landfall in Florida before March 15?",
        "market_id": "hurricane-florida-mar",
        "bss_score": 32,
        "pes_score": 81,
        "wallet_age_days": 210,
        "wallet_trades": 53,
        "trade_size_usd": 18000,
        "price_before": 0.38,
        "price_after": 0.92,
        "z_score": 2.3,
        "trade_before_news_hours": 3,
        "status": "CONFIRMED",
        "osint_signals": [
            {"source": "NOAA", "headline": "Buoy #41047 pressure drop consistent with rapid intensification", "hours_before_trade": 3},
            {"source": "Weather Underground", "headline": "Tropical Storm upgraded to Category 2", "hours_before_trade": 5},
        ],
        "news_headline": "Category 4 Hurricane makes landfall near Tampa Bay",
        "xai_narrative": "**Classification: OSINT_EDGE**\n\nThis trader acted on publicly available NOAA buoy data and Weather Underground forecasts showing rapid tropical storm intensification. The information was public but required meteorological expertise to interpret as a prediction market signal. Established wallet (210 days, 53 trades) with a strong track record in weather-related markets. This is legitimate alpha from superior public information processing.",
        "fraud_triangle": {"pressure": "N/A — legitimate trading", "opportunity": "N/A — public information", "rationalization": "N/A — ethical research-based trading"},
    },
    {
        "classification": "FAST_REACTOR",
        "market_name": "Will Fed announce emergency rate cut in February?",
        "market_id": "fed-emergency-cut",
        "bss_score": 14,
        "pes_score": 96,
        "wallet_age_days": 145,
        "wallet_trades": 31,
        "trade_size_usd": 6500,
        "price_before": 0.68,
        "price_after": 0.99,
        "z_score": 1.4,
        "trade_before_news_hours": 0.05,
        "status": "CONFIRMED",
        "osint_signals": [
            {"source": "Federal Reserve", "headline": "FOMC emergency session convened — rate cut 50bp", "hours_before_trade": -0.05},
        ],
        "news_headline": "Fed cuts rates 50bp in emergency session, citing financial stability",
        "xai_narrative": "**Classification: FAST_REACTOR**\n\nTrade executed approximately 3 minutes after the Federal Reserve published its emergency rate cut decision. This is within normal human reaction time for a trader actively monitoring the FOMC feed. No advance knowledge indicated — this is standard fast-reaction trading on a public, scheduled event.",
        "fraud_triangle": {"pressure": "N/A", "opportunity": "N/A", "rationalization": "N/A"},
    },
    {
        "classification": "SPECULATOR",
        "market_name": "Will Bitcoin exceed $150K before April?",
        "market_id": "btc-150k-apr",
        "bss_score": 16,
        "pes_score": 42,
        "wallet_age_days": 90,
        "wallet_trades": 19,
        "trade_size_usd": 1500,
        "price_before": 0.22,
        "price_after": 0.19,
        "z_score": 0.4,
        "trade_before_news_hours": None,
        "status": "UNDER_REVIEW",
        "osint_signals": [],
        "news_headline": None,
        "xai_narrative": "**Classification: SPECULATOR**\n\nPure speculation on Bitcoin price prediction with no detected informational edge. No timing correlation with any news or OSINT signals. Small position size ($1,500) consistent with casual speculation. Normal market behavior.",
        "fraud_triangle": {"pressure": "N/A", "opportunity": "N/A", "rationalization": "N/A"},
    },
    {
        "classification": "INSIDER",
        "market_name": "Will CEO of TechCorp resign before earnings?",
        "market_id": "techcorp-ceo-resign",
        "bss_score": 89,
        "pes_score": 10,
        "wallet_age_days": 4,
        "wallet_trades": 1,
        "trade_size_usd": 28000,
        "price_before": 0.12,
        "price_after": 0.98,
        "z_score": 3.6,
        "trade_before_news_hours": -10,
        "status": "UNDER_REVIEW",
        "osint_signals": [],
        "news_headline": "TechCorp CEO steps down in surprise announcement ahead of Q4 earnings",
        "xai_narrative": "**Classification: INSIDER**\n\nA 4-day-old wallet with a single prior trade placed $28,000 on YES at 12-cent odds, 10 hours before the surprise CEO resignation. No public signals — no analyst reports, no board leaks, no social media chatter — preceded this trade. The wallet's youth and the trade's precision timing strongly indicate access to material non-public information, likely from someone within the company or its advisors.",
        "fraud_triangle": {
            "pressure": "Potential corporate insider with advance knowledge of CEO departure. $28K bet at 12-cent odds implies near-certainty — a 717% return.",
            "opportunity": "Fresh wallet created days before the trade to avoid linking to an identifiable account. Single trade executed with no prior history to establish a pattern.",
            "rationalization": "May have viewed prediction markets as outside traditional insider trading enforcement scope."
        },
    },
    {
        "classification": "OSINT_EDGE",
        "market_name": "Will EU approve semiconductor subsidy package in Q1?",
        "market_id": "eu-chips-subsidy",
        "bss_score": 25,
        "pes_score": 88,
        "wallet_age_days": 400,
        "wallet_trades": 87,
        "trade_size_usd": 12000,
        "price_before": 0.51,
        "price_after": 0.90,
        "z_score": 1.9,
        "trade_before_news_hours": 8,
        "status": "CONFIRMED",
        "osint_signals": [
            {"source": "EU Commission Portal", "headline": "Committee vote scheduled on semiconductor investment framework", "hours_before_trade": 10},
            {"source": "Reuters Brussels", "headline": "Sources: broad political consensus forming on chips package", "hours_before_trade": 8},
        ],
        "news_headline": "EU Parliament approves landmark semiconductor subsidy package",
        "xai_narrative": "**Classification: OSINT_EDGE**\n\nHighly experienced trader (400-day wallet, 87 trades) identified positive signals in EU Commission procedural filings and Brussels wire reports. All sources were publicly available — the edge came from the expertise required to connect regulatory process signals to a prediction market outcome. This is exactly the kind of informed participation prediction markets are designed to reward.",
        "fraud_triangle": {"pressure": "N/A", "opportunity": "N/A", "rationalization": "N/A"},
    },
]


# ============================================================
# Arena Votes for Iran Case
# ============================================================

IRAN_VOTES = [
    {"vote": "agree", "confidence": 5, "comment": "Six fresh wallets, same funding path, exact date — this is textbook insider trading."},
    {"vote": "agree", "confidence": 5, "comment": "The 6-hour gap with zero public signals is damning. No other explanation fits."},
    {"vote": "agree", "confidence": 4, "comment": "Coordinated wallets + date specificity + tornado cash funding = clear insider case."},
    {"vote": "agree", "confidence": 5, "comment": "4.7 sigma volume anomaly from brand new wallets. Not a coincidence."},
    {"vote": "agree", "confidence": 4, "comment": "The fraud triangle analysis is spot on. Motive, means, and opportunity all present."},
    {"vote": "agree", "confidence": 3, "comment": "Highly suspicious but would want to see the full on-chain funding trace before 100% certainty."},
    {"vote": "uncertain", "confidence": 2, "comment": "Could geopolitical analysts have predicted the strike date from troop movements?"},
    {"vote": "agree", "confidence": 5, "comment": "Nobody predicts an exact strike date from open source. This is insider knowledge, period."},
]


# ============================================================
# Seed Functions
# ============================================================

def seed_iran_case(conn):
    """Seed the primary Iran strike case with all 6 wallets."""
    print("\n=== Seeding Iran Strike Case ===")

    wallets = []
    event_ids = []
    wallet_trade_times = []

    # Phase 1: Create wallets and anomaly events
    for i in range(NUM_WALLETS):
        addr = wallet_addr()
        wallets.append(addr)

        wallet = {
            "address": addr,
            "first_seen": (TRADE_TIME - timedelta(hours=random.uniform(1, 3))).isoformat(),
            "last_seen": TRADE_TIME.isoformat(),
            "trade_count": 1,
            "win_count": 1,
            "loss_count": 0,
            "win_rate": 1.0,
            "total_volume": TRADE_SIZE_PER_WALLET,
            "avg_position_size": TRADE_SIZE_PER_WALLET,
            "is_fresh_wallet": 1,
            "cluster_id": CLUSTER_ID,
            "funding_chain": json.dumps(["tornado.cash", FUNDING_SOURCE]),
            "suspicious_flags": json.dumps(["fresh_wallet", "high_win_rate", "mixer_funded", "cluster_member"]),
        }
        upsert_wallet(conn, wallet)

        eid = PRIMARY_EVENT_ID if i == 0 else f"EVENT-iran-w{i}-{uid()}"
        event_ids.append(eid)

        trade_offset = timedelta(seconds=random.randint(0, 180))
        wallet_trade_time = TRADE_TIME + trade_offset
        wallet_trade_times.append(wallet_trade_time)

        anomaly = {
            "event_id": eid,
            "market_id": MARKET_ID,
            "market_name": MARKET_NAME,
            "timestamp": wallet_trade_time.isoformat(),
            "trade_timestamp": wallet_trade_time.isoformat(),
            "wallet_address": addr,
            "trade_size": TRADE_SIZE_PER_WALLET,
            "position_side": "YES",
            "price_before": PRICE_BEFORE,
            "price_after": PRICE_AFTER,
            "price_change": PRICE_AFTER - PRICE_BEFORE,
            "volume_24h": TOTAL_TRADE * 2.5,
            "volume_spike_ratio": 5.7,
            "z_score": 4.7,
            "classification": "INSIDER",
            "bss_score": 96,
            "pes_score": 4,
            "confidence": 0.94,
            "xai_narrative": XAI_NARRATIVE if i == 0 else f"Wallet {i+1} of 6 in coordinated cluster {CLUSTER_ID}. See primary case {CASE_ID} for full analysis.",
            "fraud_triangle_json": json.dumps(FRAUD_TRIANGLE),
        }
        insert_anomaly(conn, anomaly)
        print(f"  Wallet {i+1}/{NUM_WALLETS}: {addr[:10]}...{addr[-6:]}")

    # Phase 2: Create the news event
    news_osint_id = f"OSINT-iran-news-{uid()}"
    insert_osint_event(conn, {
        "event_id": news_osint_id,
        "timestamp": NEWS_TIME.isoformat(),
        "source": IRAN_NEWS_EVENT["source"],
        "source_url": "https://reuters.com/world/us-conducts-airstrikes-iran",
        "headline": IRAN_NEWS_EVENT["headline"],
        "content": IRAN_NEWS_EVENT["content"],
        "category": IRAN_NEWS_EVENT["category"],
        "geolocation": json.dumps({"country": "Iran", "lat": 32.4279, "lng": 53.6880}),
        "relevance_score": 1.0,
        "embedding_id": f"emb-{uid()}",
        "related_market_ids": json.dumps([MARKET_ID]),
    })

    # Evidence JSON for the sentinel_index case
    evidence = {
        "wallet_address": wallets[0],
        "all_wallet_addresses": wallets,
        "wallet_age_days": 0,
        "wallet_trades": 1,
        "trade_size_usd": TOTAL_TRADE,
        "price_before": PRICE_BEFORE,
        "price_after": PRICE_AFTER,
        "z_score": 4.7,
        "osint_signals": [],  # No signals before trade — this is the point
        "osint_event_ids": [news_osint_id],
        "trade_timestamp": TRADE_TIME.isoformat(),
        "news_timestamp": NEWS_TIME.isoformat(),
        "news_headline": IRAN_NEWS_EVENT["headline"],
        "hours_before_news": -6.0,
        "scenario": "Six brand-new wallets, funded the same day through Tornado Cash, placed $60,000 on the exact date of a US military strike on Iran. Six hours before it happened. They walked away with $1.2 million.",
        "cluster_id": CLUSTER_ID,
        "cluster_size": NUM_WALLETS,
        "total_payout": TOTAL_PAYOUT,
        "rf_analysis": {
            "rf_score": 0.91,
            "source": "RandomForest",
            "top_features": [
                "is_fresh_wallet",
                "cluster_member",
                "hours_before_news",
                "z_score",
                "wallet_age_days",
            ],
        },
        "game_theory_analysis": {
            "game_theory_suspicion_score": 88,
            "best_fit_player_type": "InsiderTrader",
            "entropy_anomaly": 0.42,
            "pattern_confidence": 0.94,
        },
    }

    # Create the sentinel_index case
    sentinel_case = {
        "case_id": CASE_ID,
        "anomaly_event_id": PRIMARY_EVENT_ID,
        "market_id": MARKET_ID,
        "market_name": MARKET_NAME,
        "classification": "INSIDER",
        "bss_score": 96,
        "pes_score": 4,
        "temporal_gap_hours": TEMPORAL_GAP_HOURS,
        "consensus_score": None,  # Will be computed from votes
        "status": "UNDER_REVIEW",
        "sar_report": SAR_REPORT,
        "xai_summary": XAI_NARRATIVE,
        "evidence_json": json.dumps(evidence),
    }
    insert_case(conn, sentinel_case)
    conn.commit()

    # Phase 3: Create evidence packets (after case exists for FK constraint)
    for i in range(NUM_WALLETS):
        packet = {
            "packet_id": f"PKT-iran-w{i}-{uid()}",
            "case_id": CASE_ID,
            "event_id": event_ids[i],
            "market_id": MARKET_ID,
            "market_name": MARKET_NAME,
            "market_slug": MARKET_ID,
            "wallet_address": wallets[i],
            "trade_timestamp": wallet_trade_times[i].isoformat(),
            "side": "buy",
            "outcome": "yes",
            "trade_size": TRADE_SIZE_PER_WALLET,
            "trade_price": PRICE_BEFORE,
            "wallet_age_hours": random.uniform(1, 3),
            "wallet_trade_count": 1,
            "wallet_win_rate": 1.0,
            "wallet_risk_score": 0.96,
            "is_fresh_wallet": 1,
            "cluster_id": CLUSTER_ID,
            "cluster_size": NUM_WALLETS,
            "cluster_confidence": 0.94,
            "osint_event_id": None,
            "osint_source": None,
            "osint_title": None,
            "osint_timestamp": None,
            "temporal_gap_minutes": TEMPORAL_GAP_HOURS * 60,
            "temporal_gap_score": 0.97,
            "correlation_score": 0.95,
            "evidence_json": json.dumps({
                "risk_flags": ["fresh_wallet", "high_win_rate", "mixer_funded", "cluster_member"],
                "wallet_profile": {
                    "address": wallets[i],
                    "age_days": 0,
                    "trade_count": 1,
                    "win_rate": 1.0,
                    "total_volume": TRADE_SIZE_PER_WALLET,
                    "avg_trade_size": TRADE_SIZE_PER_WALLET,
                },
                "streaming_anomaly": {
                    "score": 0.92,
                    "volume_z": 4.7,
                    "price_move": 0.95,
                    "interval_z": 3.8,
                },
                "cluster": {
                    "id": CLUSTER_ID,
                    "size": NUM_WALLETS,
                    "confidence": 0.94,
                },
                "nearest_osint_event": None,
                "osint_event_count": 0,
                "osint_signals_before_trade": 0,
                "temporal_gap_minutes": TEMPORAL_GAP_HOURS * 60,
                "temporal_gap_score": 0.97,
                "gate_evaluation": {
                    "statistical_score": 0.92,
                    "rf_score": 0.91,
                    "autoencoder_score": 0.89,
                    "game_theory_score": 88,
                    "bss_score": 96,
                    "passed": True,
                },
                "classification": {
                    "case_id": CASE_ID,
                    "classification": "INSIDER",
                    "bss_score": 96,
                    "pes_score": 4,
                },
            }),
        }
        insert_evidence_packet(conn, packet)
    conn.commit()

    print(f"  Case created: {CASE_ID}")
    print(f"  Market: {MARKET_NAME}")
    print(f"  6 wallets, $60K total, 4.7σ, BSS 96, PES 4")

    # Add arena votes
    print("\n  Adding arena votes...")
    for i, v in enumerate(IRAN_VOTES):
        vote = {
            "vote_id": f"VOTE-iran-{i}-{uid()}",
            "case_id": CASE_ID,
            "voter_id": f"anon-{uid()}",
            "vote": v["vote"],
            "confidence": v["confidence"],
            "comment": v["comment"],
        }
        insert_vote(conn, vote)
    conn.commit()
    print(f"  {len(IRAN_VOTES)} votes added (7 agree, 1 uncertain)")


def seed_background_osint(conn):
    """Seed background OSINT events for the System Health feed."""
    print("\n=== Seeding Background OSINT Events ===")
    now = datetime(2025, 2, 28, 10, 0, 0)  # Shortly after news broke

    for ev in BACKGROUND_OSINT:
        ts = now - timedelta(hours=ev["hours_ago"])
        osint = {
            "event_id": f"OSINT-bg-{uid()}",
            "timestamp": ts.isoformat(),
            "source": ev["source"],
            "source_url": f"https://{ev['source']}.example.com/event/{uid()}",
            "headline": ev["headline"],
            "content": f"Full content: {ev['headline']}",
            "category": ev["category"],
            "geolocation": json.dumps({"country": "Global"}),
            "relevance_score": round(random.uniform(0.3, 0.8), 2),
            "embedding_id": f"emb-{uid()}",
            "related_market_ids": json.dumps([]),
        }
        insert_osint_event(conn, osint)

    conn.commit()
    print(f"  {len(BACKGROUND_OSINT)} OSINT events seeded across gdelt/acled/gdacs/nasa_firms/rss")


def seed_background_cases(conn):
    """Seed background cases for Sentinel Index depth."""
    print("\n=== Seeding Background Cases ===")

    for i, cd in enumerate(BACKGROUND_CASES):
        case_id = f"CASE-bg{i}-{uid()}"
        event_id = f"EVENT-bg{i}-{uid()}"
        addr = wallet_addr()

        base_time = datetime(2025, 2, 28, 10, 0, 0) - timedelta(days=random.randint(2, 20))

        if cd["trade_before_news_hours"] is not None:
            trade_time = base_time
            if cd["trade_before_news_hours"] < 0:
                news_time = base_time + timedelta(hours=abs(cd["trade_before_news_hours"]))
                temporal_gap = abs(cd["trade_before_news_hours"])
            else:
                news_time = base_time - timedelta(hours=cd["trade_before_news_hours"])
                temporal_gap = -cd["trade_before_news_hours"]
        else:
            trade_time = base_time
            news_time = None
            temporal_gap = None

        # Wallet
        upsert_wallet(conn, {
            "address": addr,
            "first_seen": (datetime.now() - timedelta(days=cd["wallet_age_days"])).isoformat(),
            "last_seen": trade_time.isoformat(),
            "trade_count": cd["wallet_trades"],
            "win_count": int(cd["wallet_trades"] * 0.62),
            "loss_count": int(cd["wallet_trades"] * 0.38),
            "win_rate": 0.62,
            "total_volume": cd["trade_size_usd"] * cd["wallet_trades"],
            "avg_position_size": cd["trade_size_usd"],
            "is_fresh_wallet": 1 if cd["wallet_age_days"] < 7 else 0,
            "cluster_id": None,
            "funding_chain": json.dumps(["coinbase"]),
            "suspicious_flags": json.dumps(["fresh_wallet"] if cd["wallet_age_days"] < 7 else []),
        })

        # OSINT signals
        osint_ids = []
        for sig in cd.get("osint_signals", []):
            oid = f"OSINT-bg{i}-{uid()}"
            sig_time = trade_time - timedelta(hours=sig["hours_before_trade"])
            insert_osint_event(conn, {
                "event_id": oid,
                "timestamp": sig_time.isoformat(),
                "source": sig["source"].lower().replace(" ", "_"),
                "source_url": f"https://{sig['source'].lower().replace(' ', '')}.com/article/{uid()}",
                "headline": sig["headline"],
                "content": f"Full content: {sig['headline']}",
                "category": "news",
                "geolocation": None,
                "relevance_score": 0.85,
                "embedding_id": f"emb-{uid()}",
                "related_market_ids": json.dumps([cd["market_id"]]),
            })
            osint_ids.append(oid)

        # News event
        if news_time and cd.get("news_headline"):
            nid = f"OSINT-news-bg{i}-{uid()}"
            insert_osint_event(conn, {
                "event_id": nid,
                "timestamp": news_time.isoformat(),
                "source": "major_news",
                "source_url": "https://news.example.com/breaking",
                "headline": cd["news_headline"],
                "content": f"Breaking: {cd['news_headline']}",
                "category": "breaking_news",
                "geolocation": None,
                "relevance_score": 1.0,
                "embedding_id": f"emb-{uid()}",
                "related_market_ids": json.dumps([cd["market_id"]]),
            })
            osint_ids.append(nid)

        # Anomaly
        insert_anomaly(conn, {
            "event_id": event_id,
            "market_id": cd["market_id"],
            "market_name": cd["market_name"],
            "timestamp": trade_time.isoformat(),
            "trade_timestamp": trade_time.isoformat(),
            "wallet_address": addr,
            "trade_size": cd["trade_size_usd"],
            "position_side": "YES",
            "price_before": cd["price_before"],
            "price_after": cd["price_after"],
            "price_change": cd["price_after"] - cd["price_before"],
            "volume_24h": cd["trade_size_usd"] * random.uniform(2, 5),
            "volume_spike_ratio": cd["z_score"] + 1,
            "z_score": cd["z_score"],
            "classification": cd["classification"],
            "bss_score": cd["bss_score"],
            "pes_score": cd["pes_score"],
            "confidence": round(random.uniform(0.82, 0.96), 2),
            "xai_narrative": cd["xai_narrative"],
            "fraud_triangle_json": json.dumps(cd["fraud_triangle"]),
        })

        # Evidence
        evidence = {
            "wallet_address": addr,
            "wallet_age_days": cd["wallet_age_days"],
            "wallet_trades": cd["wallet_trades"],
            "trade_size_usd": cd["trade_size_usd"],
            "price_before": cd["price_before"],
            "price_after": cd["price_after"],
            "z_score": cd["z_score"],
            "osint_signals": cd.get("osint_signals", []),
            "osint_event_ids": osint_ids,
            "trade_timestamp": trade_time.isoformat(),
            "news_timestamp": news_time.isoformat() if news_time else None,
            "news_headline": cd.get("news_headline"),
            "scenario": cd["market_name"],
            "hours_before_news": cd["trade_before_news_hours"],
        }

        insert_case(conn, {
            "case_id": case_id,
            "anomaly_event_id": event_id,
            "market_id": cd["market_id"],
            "market_name": cd["market_name"],
            "classification": cd["classification"],
            "bss_score": cd["bss_score"],
            "pes_score": cd["pes_score"],
            "temporal_gap_hours": temporal_gap,
            "consensus_score": random.randint(65, 90) if cd["status"] == "CONFIRMED" else None,
            "status": cd["status"],
            "sar_report": generate_bg_sar(cd, addr, trade_time, news_time) if cd["classification"] == "INSIDER" else None,
            "xai_summary": cd["xai_narrative"],
            "evidence_json": json.dumps(evidence),
        })

        # Evidence packet
        gap_minutes = abs(cd["trade_before_news_hours"]) * 60 if cd["trade_before_news_hours"] else None
        if gap_minutes and cd["trade_before_news_hours"] < 0:
            tg_score = round(min(1.0, 0.6 + min(gap_minutes, 360.0) / 360.0 * 0.4), 3)
        elif gap_minutes:
            tg_score = round(max(0.05, 0.3 - gap_minutes / 600.0), 3)
        else:
            tg_score = 0.5

        wallet_risk = round(cd["bss_score"] / 100, 3)
        first_osint_time = (trade_time - timedelta(hours=cd["osint_signals"][0]["hours_before_trade"])).isoformat() if cd.get("osint_signals") else None

        insert_evidence_packet(conn, {
            "packet_id": f"PKT-bg{i}-{uid()}",
            "case_id": case_id,
            "event_id": event_id,
            "market_id": cd["market_id"],
            "market_name": cd["market_name"],
            "market_slug": cd["market_id"],
            "wallet_address": addr,
            "trade_timestamp": trade_time.isoformat(),
            "side": "buy",
            "outcome": "yes",
            "trade_size": float(cd["trade_size_usd"]),
            "trade_price": cd["price_before"],
            "wallet_age_hours": float(cd["wallet_age_days"] * 24),
            "wallet_trade_count": cd["wallet_trades"],
            "wallet_win_rate": 0.62,
            "wallet_risk_score": wallet_risk,
            "is_fresh_wallet": 1 if cd["wallet_age_days"] < 7 else 0,
            "cluster_id": None,
            "cluster_size": 0,
            "cluster_confidence": 0.0,
            "osint_event_id": osint_ids[0] if osint_ids else None,
            "osint_source": cd["osint_signals"][0]["source"].lower().replace(" ", "_") if cd.get("osint_signals") else None,
            "osint_title": cd["osint_signals"][0]["headline"] if cd.get("osint_signals") else None,
            "osint_timestamp": first_osint_time,
            "temporal_gap_minutes": gap_minutes,
            "temporal_gap_score": tg_score,
            "correlation_score": round(0.3 * wallet_risk + 0.4 * tg_score + 0.3 * (cd["bss_score"] / 100), 3),
            "evidence_json": json.dumps({
                "risk_flags": ["fresh_wallet"] if cd["wallet_age_days"] < 7 else [],
                "wallet_profile": {"address": addr, "age_days": cd["wallet_age_days"], "trade_count": cd["wallet_trades"], "win_rate": 0.62},
                "osint_event_count": len(osint_ids),
                "classification": {"case_id": case_id, "classification": cd["classification"], "bss_score": cd["bss_score"], "pes_score": cd["pes_score"]},
            }),
        })

        # Add a few votes to background INSIDER/OSINT_EDGE cases
        if cd["classification"] in ("INSIDER", "OSINT_EDGE"):
            for j in range(random.randint(2, 5)):
                vote_type = "agree" if random.random() > 0.2 else random.choice(["disagree", "uncertain"])
                insert_vote(conn, {
                    "vote_id": f"VOTE-bg{i}-{j}-{uid()}",
                    "case_id": case_id,
                    "voter_id": f"anon-{uid()}",
                    "vote": vote_type,
                    "confidence": random.randint(2, 5),
                    "comment": None,
                })

        print(f"  [{i+1}/{len(BACKGROUND_CASES)}] {cd['classification']}: {cd['market_name'][:50]}")

    conn.commit()


def generate_bg_sar(cd, wallet, trade_time, news_time):
    """Generate a SAR for a background INSIDER case."""
    return f"""# Suspicious Activity Report

## Executive Summary
**Classification**: {cd['classification']}
**Market**: {cd['market_name']}
**BSS Score**: {cd['bss_score']}/100

## Trade Details
- **Wallet**: `{wallet[:10]}...{wallet[-6:]}`
- **Trade Time**: {trade_time.strftime('%Y-%m-%d %H:%M UTC')}
- **Position**: YES @ ${cd['price_before']:.2f}
- **Size**: ${cd['trade_size_usd']:,.0f}

## Fraud Triangle
- **Pressure**: {cd['fraud_triangle']['pressure']}
- **Opportunity**: {cd['fraud_triangle']['opportunity']}
- **Rationalization**: {cd['fraud_triangle']['rationalization']}

## Recommendation
Flag wallet for monitoring and potential referral to compliance."""


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("  SENTINEL VIDEO DEMO SEEDER")
    print("  Populating database to match script.md")
    print("=" * 60)

    # Wipe and reinitialize
    import os
    db_path = os.getenv("DATABASE_PATH", "./data/sentinel.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"\nRemoved existing database: {db_path}")

    init_schema()
    print("Database schema initialized.")

    conn = get_connection()

    seed_iran_case(conn)
    seed_background_osint(conn)
    seed_background_cases(conn)

    # Print final stats
    stats = get_stats(conn)
    conn.close()

    print("\n" + "=" * 60)
    print("  DATABASE READY FOR VIDEO")
    print("=" * 60)
    print(f"  Total anomalies:       {stats['total_anomalies']}")
    print(f"  Total OSINT events:    {stats['total_osint_events']}")
    print(f"  Total wallets:         {stats['total_wallets']}")
    print(f"  Total cases:           {stats['total_cases']}")
    print(f"  Evidence packets:      {stats['total_evidence_packets']}")
    print(f"  Cases by class:        {stats['cases_by_classification']}")
    print(f"  Cases by status:       {stats['cases_by_status']}")
    print(f"\n  Iran case ID: {CASE_ID}")
    print(f"  (use this to navigate to /case/{CASE_ID} in the dashboard)")
    print()
    print("  Run the dashboard:")
    print("    cd ui && npm run dev")
    print("    cd .. && python -m src.api.main")
    print()


# ============================================================
# Live Feed Streamer — keeps both feeds updating forever
# ============================================================

# Rotating pool of realistic trade headlines
STREAM_MARKETS = [
    {"market_id": "us-iran-strike-feb28-2026", "market_name": "Will the US conduct a military strike on Iran on February 28, 2025?", "base_price": 0.92},
    {"market_id": "tariff-china-march-2026", "market_name": "Will the US announce new China tariffs before March 15?", "base_price": 0.64},
    {"market_id": "hurricane-fl-2026", "market_name": "Will a Category 4+ hurricane hit Florida before November?", "base_price": 0.38},
    {"market_id": "btc-150k-2026", "market_name": "Will Bitcoin exceed $150K before July?", "base_price": 0.31},
    {"market_id": "fed-rate-cut-mar", "market_name": "Will the Fed cut rates at the March meeting?", "base_price": 0.72},
    {"market_id": "eu-chips-subsidy-q1", "market_name": "Will EU approve semiconductor subsidy package in Q1?", "base_price": 0.81},
    {"market_id": "trump-executive-order", "market_name": "Will Trump sign executive order on AI regulation before April?", "base_price": 0.55},
    {"market_id": "spacex-starship-launch", "market_name": "Will SpaceX Starship complete orbital flight before June?", "base_price": 0.67},
    {"market_id": "ukraine-ceasefire-2026", "market_name": "Will Ukraine-Russia ceasefire be announced in Q1 2026?", "base_price": 0.22},
    {"market_id": "apple-ai-device", "market_name": "Will Apple announce dedicated AI hardware at WWDC?", "base_price": 0.44},
    {"market_id": "oil-price-100", "market_name": "Will crude oil exceed $100/barrel before May?", "base_price": 0.48},
    {"market_id": "senate-vote-immigration", "market_name": "Will the Senate pass immigration reform bill in March?", "base_price": 0.29},
]

STREAM_OSINT_POOL = [
    # GDELT — news intelligence
    {"source": "gdelt", "category": "politics", "headlines": [
        "Pentagon confirms additional carrier strike group deployment to Persian Gulf",
        "State Department issues updated travel advisory for Middle East region",
        "EU foreign ministers convene emergency session on Iran situation",
        "Chinese foreign ministry calls for restraint amid rising tensions",
        "NATO Secretary General briefed on latest intelligence assessments",
        "Congressional leaders receive classified briefing on Iran operations",
        "G7 nations issue joint statement on Middle East stability",
        "Russian foreign ministry warns against further escalation",
        "UN Security Council emergency session called for Thursday",
        "Oil market analysts predict sustained price volatility through Q2",
        "Defense stocks surge as geopolitical risk premium rises",
        "Diplomatic sources report back-channel negotiations underway",
        "White House National Security Council meets for third time this week",
        "European allies weigh sanctions options against Iran",
        "Intelligence community assesses Iran retaliation timeline",
    ]},
    # ACLED — conflict data
    {"source": "acled", "category": "conflict", "headlines": [
        "Houthi forces launch anti-ship missile near Bab el-Mandeb strait",
        "Israeli Air Force conducts operations over southern Lebanon",
        "Pro-Iranian militia activity reported near US base in eastern Syria",
        "Turkish military operations continue in northern Iraq border region",
        "Armed clashes reported between rival factions in eastern Libya",
        "Hezbollah rocket fire detected from southern Lebanon positions",
        "IED incident reported on supply route near Kirkuk, Iraq",
        "Egyptian military reinforces Sinai border positions",
        "Saudi-led coalition reports drone interception over Riyadh",
        "Kurdish forces report ceasefire violations in Deir ez-Zor province",
    ]},
    # GDACS — disaster alerts
    {"source": "gdacs", "category": "disaster", "headlines": [
        "Magnitude 4.8 earthquake detected near Strait of Hormuz",
        "Tropical disturbance developing in western Caribbean Sea",
        "Flood warning extended for Tigris-Euphrates river basin",
        "Volcanic activity alert raised for Mount Etna, Sicily",
        "Severe weather system tracking across central Mediterranean",
        "Tsunami advisory issued for coastal regions following undersea quake",
        "Drought conditions worsening across Horn of Africa",
        "Cyclone formation possible in Bay of Bengal within 48 hours",
    ]},
    # NASA FIRMS — satellite/fire detection
    {"source": "nasa_firms", "category": "satellite", "headlines": [
        "Thermal anomaly cluster detected near Isfahan, Iran",
        "Significant heat signature observed at Bandar Abbas port facility",
        "Agricultural burn patterns elevated across Mesopotamian plain",
        "Industrial fire signature detected near Abadan refinery complex",
        "Anomalous thermal activity near Bushehr nuclear power plant perimeter",
        "Large-scale fire event detected in southern Iraq marshlands",
        "Heat signature spike at Iranian military testing facility",
    ]},
    # RSS — general feeds
    {"source": "rss", "category": "crypto", "headlines": [
        "Polymarket daily volume crosses $52M — new all-time high",
        "On-chain analysts flag suspicious wallet cluster on Polymarket Iran market",
        "Prediction market liquidity surges 180% amid geopolitical volatility",
        "CFTC commissioner comments on prediction market oversight framework",
        "DeFi protocols see record TVL as users hedge geopolitical exposure",
        "Major market maker adjusts spreads on Middle East prediction markets",
        "Wallet forensics firm publishes report on Polymarket insider patterns",
    ]},
]


def stream_live_feeds(conn, interval: float = 3.0):
    """
    Continuously insert new trades and OSINT events into the DB.
    The dashboard polls every 5s, so new items appear in near-real-time.
    """
    import time
    import itertools

    print("\n" + "=" * 60)
    print("  LIVE FEED STREAMER")
    print(f"  Inserting new trades + OSINT every {interval}s")
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    trade_counter = 0
    osint_counter = 0

    # Build a flat list of all OSINT headlines with their metadata
    osint_flat = []
    for pool in STREAM_OSINT_POOL:
        for h in pool["headlines"]:
            osint_flat.append({"source": pool["source"], "category": pool["category"], "headline": h})
    osint_cycle = itertools.cycle(osint_flat)

    # Wallet pool — mix of fresh and established
    established_wallets = [wallet_addr() for _ in range(20)]

    try:
        while True:
            now = datetime.utcnow()

            # ---- Insert a trade ----
            market = random.choice(STREAM_MARKETS)
            is_suspicious = random.random() < 0.08  # ~8% of trades look suspicious
            is_fresh = is_suspicious or random.random() < 0.15

            if is_fresh:
                addr = wallet_addr()
                age_days = random.randint(0, 5)
                trades = random.randint(0, 3)
            else:
                addr = random.choice(established_wallets)
                age_days = random.randint(30, 500)
                trades = random.randint(10, 200)

            side = random.choice(["YES", "YES", "YES", "NO"])  # Bias toward YES
            price = market["base_price"] + random.uniform(-0.08, 0.08)
            price = max(0.02, min(0.98, price))
            trade_size = random.choice([200, 500, 800, 1500, 3000, 5000, 8000])
            if is_suspicious:
                trade_size = random.choice([15000, 25000, 40000, 60000])

            z = round(random.gauss(1.2, 0.8), 2)
            if is_suspicious:
                z = round(random.uniform(3.0, 5.5), 2)
            z = max(0.1, z)

            bss = random.randint(5, 30)
            pes = random.randint(40, 80)
            classification = "SPECULATOR"
            if is_suspicious:
                bss = random.randint(70, 96)
                pes = random.randint(3, 15)
                classification = random.choice(["INSIDER", "INSIDER", "OSINT_EDGE"])

            trade_counter += 1
            eid = f"EVENT-stream-{trade_counter}-{uid()}"

            insert_anomaly(conn, {
                "event_id": eid,
                "market_id": market["market_id"],
                "market_name": market["market_name"],
                "timestamp": now.isoformat(),
                "trade_timestamp": now.isoformat(),
                "wallet_address": addr,
                "trade_size": float(trade_size),
                "position_side": side,
                "price_before": round(price, 4),
                "price_after": round(price + random.uniform(-0.03, 0.15), 4),
                "price_change": round(random.uniform(-0.03, 0.15), 4),
                "volume_24h": float(trade_size * random.uniform(5, 20)),
                "volume_spike_ratio": round(z + 1, 2),
                "z_score": z,
                "classification": classification,
                "bss_score": bss,
                "pes_score": pes,
                "confidence": round(random.uniform(0.6, 0.95), 2),
                "xai_narrative": None,
                "fraud_triangle_json": None,
            })

            flag = " ** FLAGGED **" if is_suspicious else ""
            print(f"  TRADE #{trade_counter:4d}  {side:3s}  ${trade_size:>8,}  z={z:.1f}  {market['market_name'][:45]}{flag}")

            # ---- Insert an OSINT event every ~2 trades ----
            if random.random() < 0.55:
                osint_item = next(osint_cycle)
                osint_counter += 1
                insert_osint_event(conn, {
                    "event_id": f"OSINT-stream-{osint_counter}-{uid()}",
                    "timestamp": now.isoformat(),
                    "source": osint_item["source"],
                    "source_url": f"https://{osint_item['source']}.example.com/{uid()}",
                    "headline": osint_item["headline"],
                    "content": f"Full report: {osint_item['headline']}",
                    "category": osint_item["category"],
                    "geolocation": json.dumps({"country": "Global"}),
                    "relevance_score": round(random.uniform(0.3, 0.95), 2),
                    "embedding_id": f"emb-{uid()}",
                    "related_market_ids": json.dumps([]),
                })
                src = osint_item["source"].upper()
                print(f"  OSINT #{osint_counter:4d}  [{src:10s}]  {osint_item['headline'][:55]}")

            conn.commit()
            time.sleep(interval)

    except KeyboardInterrupt:
        conn.commit()
        print(f"\n\nStreamer stopped. Inserted {trade_counter} trades, {osint_counter} OSINT events.")


# ============================================================
# Main
# ============================================================

def main():
    import sys

    stream_mode = "--stream" in sys.argv
    seed_only = "--seed-only" in sys.argv

    print("=" * 60)
    print("  SENTINEL VIDEO DEMO SEEDER")
    print("  Populating database to match script.md")
    print("=" * 60)

    if not stream_mode or not seed_only:
        # Wipe and reinitialize
        import os
        db_path = os.getenv("DATABASE_PATH", "./data/sentinel.db")
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"\nRemoved existing database: {db_path}")

        init_schema()
        print("Database schema initialized.")

        conn = get_connection()

        seed_iran_case(conn)
        seed_background_osint(conn)
        seed_background_cases(conn)

        stats = get_stats(conn)

        print("\n" + "=" * 60)
        print("  DATABASE READY FOR VIDEO")
        print("=" * 60)
        print(f"  Total anomalies:       {stats['total_anomalies']}")
        print(f"  Total OSINT events:    {stats['total_osint_events']}")
        print(f"  Total wallets:         {stats['total_wallets']}")
        print(f"  Total cases:           {stats['total_cases']}")
        print(f"  Evidence packets:      {stats['total_evidence_packets']}")
        print(f"  Cases by class:        {stats['cases_by_classification']}")
        print(f"  Cases by status:       {stats['cases_by_status']}")
        print(f"\n  Iran case ID: {CASE_ID}")
        print(f"  (use this to navigate to /case/{CASE_ID} in the dashboard)")

        if not stream_mode:
            print()
            print("  Run the dashboard:")
            print("    cd ui && npm run dev")
            print("    python -m src.api.main")
            print()
            print("  To also stream live feed data:")
            print("    python seed_video_demo.py --stream")
            conn.close()
            return

        # Continue into streamer with same connection
        stream_live_feeds(conn)
        conn.close()
    else:
        # Stream-only mode (DB already seeded)
        conn = get_connection()
        stream_live_feeds(conn)
        conn.close()


if __name__ == "__main__":
    main()
