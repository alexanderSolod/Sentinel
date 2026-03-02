"""
Demo Trade Stream

Generates realistic mock trades that simulate live Polymarket activity.
Trades stream in one at a time with configurable delays, each processed
through the full evidence correlator pipeline and persisted to the DB.

Markets, wallets, and OSINT events are modeled after real-world scenarios
(tariffs, geopolitical strikes, natural disasters, corporate events).
"""
import asyncio
import hashlib
import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.data.websocket_handler import TradeEvent
from src.osint.sources import OSINTEvent, EventCategory, ThreatLevel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

@dataclass
class DemoMarket:
    """A simulated prediction market with trade scenarios."""
    market_id: str
    name: str
    slug: str
    base_price: float
    osint_events: List[Dict[str, Any]] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)


def _wallet(seed: str) -> str:
    """Generate a deterministic wallet address from a seed string."""
    return "0x" + hashlib.sha256(seed.encode()).hexdigest()[:40]


def _build_scenarios() -> List[DemoMarket]:
    """Build the full set of demo markets with interleaved trades."""
    now = datetime.now(timezone.utc)

    return [
        # ── INSIDER scenario: tariff announcement ──
        DemoMarket(
            market_id="tariff-china-2026",
            name="Will the US announce new China tariffs before March 15?",
            slug="will-the-us-announce-new-china-tariffs-before-march-15",
            base_price=0.32,
            osint_events=[
                {
                    "event_id": "demo-osint-tariff-1",
                    "title": "Trade tensions rising as US-China talks stall",
                    "description": "Diplomats report no progress on trade framework after 3 rounds",
                    "source": "RSS:reuters",
                    "category": "ECONOMIC",
                    "threat_level": "MEDIUM",
                    "timestamp": (now - timedelta(hours=48)).isoformat(),
                },
                {
                    "event_id": "demo-osint-tariff-2",
                    "title": "White House briefing hints at trade policy changes",
                    "description": "Press secretary says 'all options on the table' regarding China trade",
                    "source": "RSS:ap_news",
                    "category": "ECONOMIC",
                    "threat_level": "HIGH",
                    "timestamp": (now - timedelta(hours=2)).isoformat(),
                },
            ],
            trades=[
                # Suspicious: fresh wallet, large trade BEFORE any news
                {"wallet": _wallet("insider-tariff-1"), "side": "buy", "price": 0.33, "size": 45000,
                 "age_hours": 12, "label": "SUSPICIOUS fresh wallet, large YES"},
                # Normal speculator
                {"wallet": _wallet("spec-tariff-1"), "side": "buy", "price": 0.35, "size": 800,
                 "age_hours": 2160, "label": "normal speculator"},
                # Another suspicious wallet from same cluster
                {"wallet": _wallet("insider-tariff-2"), "side": "buy", "price": 0.34, "size": 38000,
                 "age_hours": 8, "label": "SUSPICIOUS cluster wallet"},
                # Regular trader selling
                {"wallet": _wallet("trader-tariff-1"), "side": "sell", "price": 0.36, "size": 2000,
                 "age_hours": 4320, "label": "experienced trader selling"},
                # Third cluster wallet
                {"wallet": _wallet("insider-tariff-3"), "side": "buy", "price": 0.35, "size": 41000,
                 "age_hours": 6, "label": "SUSPICIOUS third cluster wallet"},
            ],
        ),

        # ── OSINT_EDGE scenario: Iran military action ──
        DemoMarket(
            market_id="iran-strike-2026",
            name="Will Israel strike Iranian nuclear facilities this quarter?",
            slug="will-israel-strike-iranian-nuclear-facilities-this-quarter",
            base_price=0.18,
            osint_events=[
                {
                    "event_id": "demo-osint-iran-1",
                    "title": "Satellite imagery shows new activity at Iranian nuclear sites",
                    "description": "Commercial satellite data reveals construction at Natanz facility",
                    "source": "RSS:bbc",
                    "category": "MILITARY",
                    "threat_level": "HIGH",
                    "timestamp": (now - timedelta(hours=72)).isoformat(),
                },
                {
                    "event_id": "demo-osint-iran-2",
                    "title": "IDF cancels military leave for select units",
                    "description": "Israeli defense forces cancel routine leave for undisclosed units",
                    "source": "GDELT",
                    "category": "MILITARY",
                    "threat_level": "CRITICAL",
                    "timestamp": (now - timedelta(hours=24)).isoformat(),
                },
                {
                    "event_id": "demo-osint-iran-3",
                    "title": "Iranian IRGC commander issues warning to Israel",
                    "description": "Commander threatens retaliation if red lines are crossed",
                    "source": "RSS:reuters",
                    "category": "MILITARY",
                    "threat_level": "HIGH",
                    "timestamp": (now - timedelta(hours=6)).isoformat(),
                },
            ],
            trades=[
                # OSINT edge: experienced wallet trades AFTER satellite imagery
                {"wallet": _wallet("osint-iran-1"), "side": "buy", "price": 0.19, "size": 15000,
                 "age_hours": 8760, "label": "OSINT analyst, trades after satellite data"},
                # Small speculator
                {"wallet": _wallet("spec-iran-1"), "side": "buy", "price": 0.21, "size": 500,
                 "age_hours": 720, "label": "small speculator"},
                # Another OSINT researcher
                {"wallet": _wallet("osint-iran-2"), "side": "buy", "price": 0.22, "size": 12000,
                 "age_hours": 4380, "label": "OSINT researcher, follows IDF news"},
                # Someone selling the risk
                {"wallet": _wallet("trader-iran-1"), "side": "sell", "price": 0.23, "size": 3000,
                 "age_hours": 2160, "label": "trader taking profit"},
            ],
        ),

        # ── FAST_REACTOR scenario: hurricane landfall ──
        DemoMarket(
            market_id="hurricane-fl-2026",
            name="Will a Category 4+ hurricane hit Florida before November?",
            slug="will-a-category-4-hurricane-hit-florida-before-november",
            base_price=0.42,
            osint_events=[
                {
                    "event_id": "demo-osint-hurr-1",
                    "title": "Tropical Storm Beta forms in Caribbean, tracking toward Florida",
                    "description": "NHC tracking tropical storm with potential for rapid intensification",
                    "source": "GDACS",
                    "category": "DISASTER",
                    "threat_level": "HIGH",
                    "timestamp": (now - timedelta(hours=36)).isoformat(),
                },
                {
                    "event_id": "demo-osint-hurr-2",
                    "title": "NHC upgrades Beta to Hurricane, Category 3 forecast",
                    "description": "Rapid intensification observed, Category 4 possible within 24h",
                    "source": "GDACS",
                    "category": "DISASTER",
                    "threat_level": "CRITICAL",
                    "timestamp": (now - timedelta(hours=4)).isoformat(),
                },
            ],
            trades=[
                # Fast reactor: trades immediately after NHC upgrade
                {"wallet": _wallet("reactor-hurr-1"), "side": "buy", "price": 0.55, "size": 5000,
                 "age_hours": 4320, "label": "fast reactor after NHC upgrade"},
                {"wallet": _wallet("reactor-hurr-2"), "side": "buy", "price": 0.57, "size": 3500,
                 "age_hours": 1440, "label": "fast reactor #2"},
                # Speculator selling against the trend
                {"wallet": _wallet("spec-hurr-1"), "side": "sell", "price": 0.56, "size": 2000,
                 "age_hours": 8760, "label": "contrarian speculator"},
            ],
        ),

        # ── SPECULATOR scenario: crypto market ──
        DemoMarket(
            market_id="btc-100k-2026",
            name="Will Bitcoin exceed $120K before July 2026?",
            slug="will-bitcoin-exceed-120k-before-july-2026",
            base_price=0.45,
            osint_events=[
                {
                    "event_id": "demo-osint-btc-1",
                    "title": "Bitcoin ETF sees record inflows for third consecutive week",
                    "description": "BlackRock iShares BTC ETF reports $1.2B weekly net inflow",
                    "source": "RSS:coindesk",
                    "category": "ECONOMIC",
                    "threat_level": "INFO",
                    "timestamp": (now - timedelta(hours=12)).isoformat(),
                },
            ],
            trades=[
                # Pure speculators with no edge
                {"wallet": _wallet("spec-btc-1"), "side": "buy", "price": 0.46, "size": 1200,
                 "age_hours": 2160, "label": "crypto speculator"},
                {"wallet": _wallet("spec-btc-2"), "side": "sell", "price": 0.44, "size": 800,
                 "age_hours": 4320, "label": "bear speculator"},
                {"wallet": _wallet("spec-btc-3"), "side": "buy", "price": 0.47, "size": 500,
                 "age_hours": 720, "label": "small bull"},
            ],
        ),

        # ── INSIDER scenario: corporate event ──
        DemoMarket(
            market_id="megacorp-merger-2026",
            name="Will MegaCorp announce merger before Q2 earnings?",
            slug="will-megacorp-announce-merger-before-q2-earnings",
            base_price=0.15,
            osint_events=[],  # No public signals — pure insider
            trades=[
                # Suspicious: large buy on a low-probability market, no OSINT
                {"wallet": _wallet("insider-merger-1"), "side": "buy", "price": 0.16, "size": 85000,
                 "age_hours": 24, "label": "SUSPICIOUS fresh wallet, huge position"},
                # Another suspicious fresh wallet
                {"wallet": _wallet("insider-merger-2"), "side": "buy", "price": 0.17, "size": 62000,
                 "age_hours": 18, "label": "SUSPICIOUS coordinated fresh wallet"},
                # Normal small speculator
                {"wallet": _wallet("spec-merger-1"), "side": "buy", "price": 0.16, "size": 200,
                 "age_hours": 8760, "label": "tiny speculator"},
            ],
        ),
    ]


def _to_osint_event(d: Dict[str, Any]) -> OSINTEvent:
    """Convert a dict to an OSINTEvent object."""
    ts = d.get("timestamp")
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

    cat_str = d.get("category", "POLITICAL").lower()
    try:
        category = EventCategory(cat_str)
    except ValueError:
        category = EventCategory.POLITICAL

    threat_str = d.get("threat_level", "INFO")
    try:
        threat = ThreatLevel(threat_str)
    except ValueError:
        threat = ThreatLevel.INFO

    return OSINTEvent(
        event_id=d["event_id"],
        source=d.get("source", "unknown"),
        title=d["title"],
        description=d.get("description", ""),
        timestamp=ts,
        category=category,
        threat_level=threat,
        country=d.get("country", "Global"),
        url=d.get("url", ""),
    )


async def run_demo_stream(
    correlator: Any,
    *,
    delay_seconds: float = 3.0,
    loop: bool = False,
) -> None:
    """
    Stream realistic demo trades through the evidence correlator.

    Each trade is processed through the full pipeline (wallet profiling,
    cluster analysis, OSINT correlation, AI classification) and persisted
    to the database. The dashboard picks up new cases via polling.

    Args:
        correlator: EvidenceCorrelator instance
        delay_seconds: Seconds between trades (default 3s for demo pacing)
        loop: If True, loop forever through scenarios
    """
    scenarios = _build_scenarios()

    # Flatten all trades across markets with their context
    trade_queue: List[Dict[str, Any]] = []
    for market in scenarios:
        osint_objects = [_to_osint_event(e) for e in market.osint_events]
        for i, trade_def in enumerate(market.trades):
            trade_queue.append({
                "market": market,
                "trade_def": trade_def,
                "osint_events": osint_objects,
                "index": i,
            })

    # Shuffle to simulate interleaved activity across markets
    random.shuffle(trade_queue)

    trade_num = 0
    total = len(trade_queue)

    print(f"\nStreaming {total} trades across {len(scenarios)} markets")
    print(f"Delay: {delay_seconds}s between trades")
    print(f"Markets:")
    for m in scenarios:
        print(f"  - {m.name} ({len(m.trades)} trades, {len(m.osint_events)} OSINT events)")
    print()

    while True:
        for item in trade_queue:
            trade_num += 1
            market: DemoMarket = item["market"]
            trade_def: Dict[str, Any] = item["trade_def"]
            osint_events: List[OSINTEvent] = item["osint_events"]

            # Build TradeEvent
            trade = TradeEvent(
                trade_id=f"demo-{trade_num:04d}",
                market_id=market.market_id,
                market_slug=market.name,
                wallet_address=trade_def["wallet"],
                side=trade_def["side"],
                outcome="yes" if trade_def["side"] == "buy" else "no",
                price=Decimal(str(trade_def["price"])),
                size=Decimal(str(trade_def["size"])),
                notional_value=Decimal(str(trade_def["size"])),
                timestamp=datetime.now(timezone.utc),
            )

            suffix = f"[{trade_num}/{total}]" if not loop else f"[{trade_num}]"
            side_str = f"{'BUY' if trade.side == 'buy' else 'SELL':4s}"
            size_str = f"${trade_def['size']:>8,.0f}"
            price_str = f"@{trade_def['price']:.2f}"
            wallet_short = trade.wallet_address[:8] + "..."

            print(f"  {suffix} {side_str} {size_str} {price_str}  {wallet_short}  {market.name[:50]}")
            print(f"         {trade_def['label']}")

            try:
                packet = await correlator.process_trade(
                    trade, osint_events_override=osint_events
                )
                case_id = packet.get("case_id", "?")
                classification = packet.get("evidence_json", "{}")
                try:
                    ej = json.loads(classification)
                    cls = ej.get("classification", {}).get("classification", "?")
                    bss = ej.get("classification", {}).get("bss_score", "?")
                except (json.JSONDecodeError, AttributeError):
                    cls = "?"
                    bss = "?"
                corr = packet.get("correlation_score", 0)
                print(f"         => {case_id} | {cls} | BSS={bss} | corr={corr:.2f}")
            except Exception as e:
                logger.exception("Failed to process demo trade")
                print(f"         => ERROR: {e}")

            print()
            await asyncio.sleep(delay_seconds)

        if not loop:
            break
        print("\n--- Restarting demo cycle ---\n")
        random.shuffle(trade_queue)
