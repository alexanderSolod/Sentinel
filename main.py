#!/usr/bin/env python
"""
Sentinel - AI-powered surveillance system for prediction market integrity

Entry point for running different components of Sentinel.

Usage:
    python main.py init                     - Initialize database and seed demo data
    python main.py dashboard                - Launch Streamlit dashboard
    python main.py pipeline --mock          - Run full pipeline on mock data (detection + OSINT + classify)
    python main.py pipeline --live          - Run pipeline on live Polymarket data
    python main.py pipeline --backfill      - Reprocess existing DB anomalies through classifier
    python main.py monitor --mock           - Run real-time monitor with mock trades
    python main.py monitor --live           - Run real-time monitor with live Polymarket WebSocket
    python main.py api                      - Launch FastAPI server
    python main.py metrics                  - Print evaluation metrics (FPR/FNR/confusion/consensus)
"""
import sys
import subprocess
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


def init_db():
    """Initialize database and seed demo data."""
    print("Initializing Sentinel database...")
    from src.data.database import init_schema
    from src.data.mock_data import seed_demo_data

    init_schema()
    seed_demo_data()
    print("Database initialized with demo data!")


def run_dashboard():
    """Launch the Streamlit dashboard."""
    print("Launching Sentinel Dashboard...")
    print("   Open http://localhost:8501 in your browser")
    subprocess.run(["streamlit", "run", "run_dashboard.py"])


# ------------------------------------------------------------------
# Pipeline Runner
# ------------------------------------------------------------------

def run_pipeline(args: list):
    """
    Run the full Sentinel pipeline:
      Data Ingestion -> Detection -> OSINT Correlation -> Classification -> Database

    Modes:
      --mock      Process synthetic anomalies from mock data generator
      --live      Fetch live markets from Polymarket, detect anomalies, classify
      --backfill  Reprocess existing DB anomalies through the classifier
    """
    from dotenv import load_dotenv
    load_dotenv()

    mode = "mock"
    for arg in args:
        if arg.startswith("--"):
            mode = arg.lstrip("-")

    if mode == "mock":
        _pipeline_mock()
    elif mode == "live":
        _pipeline_live()
    elif mode == "backfill":
        _pipeline_backfill()
    else:
        print(f"Unknown pipeline mode: {mode}")
        print("Usage: python main.py pipeline [--mock|--live|--backfill]")


def _pipeline_mock():
    """Process mock anomalies through the full pipeline."""
    from datetime import datetime, timedelta, timezone
    from src.data.database import init_schema, get_connection
    from src.osint.vector_store import VectorStore
    from src.osint.correlator import MarketCorrelator
    from src.classification.pipeline import SentinelPipeline

    print("=" * 60)
    print("SENTINEL PIPELINE - MOCK MODE")
    print("=" * 60)

    init_schema()

    # 1. Set up OSINT vector store with sample events
    print("\n[1/4] Seeding OSINT vector store...")
    store = VectorStore()
    osint_events = [
        {
            "event_id": "osint-tariff-1",
            "title": "Trade tensions escalate as US reviews China import policies",
            "description": "Multiple sources report the USTR is preparing a new round of tariffs on Chinese goods",
            "source": "GDELT", "category": "ECONOMIC", "threat_level": "HIGH",
            "country": "United States",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=18)).isoformat(),
        },
        {
            "event_id": "osint-tariff-2",
            "title": "White House announces 25% tariffs on Chinese goods effective immediately",
            "description": "Official press release confirms sweeping new tariffs on all Chinese imports",
            "source": "RSS", "category": "ECONOMIC", "threat_level": "CRITICAL",
            "country": "United States",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
        },
        {
            "event_id": "osint-iran-1",
            "title": "Iran nuclear talks show signs of progress",
            "description": "Diplomatic sources indicate movement toward a new nuclear agreement framework",
            "source": "GDELT", "category": "DIPLOMATIC", "threat_level": "HIGH",
            "country": "Iran",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(),
        },
        {
            "event_id": "osint-iran-2",
            "title": "Reports: Israel preparing military strike on Iranian nuclear facilities",
            "description": "Anonymous intelligence sources suggest imminent military action against Iran",
            "source": "GDELT", "category": "MILITARY", "threat_level": "CRITICAL",
            "country": "Iran",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        },
        {
            "event_id": "osint-hurricane-1",
            "title": "Tropical storm forms in Gulf of Mexico, models predict Florida impact",
            "description": "NHC tracking tropical disturbance with 80% chance of development",
            "source": "GDACS", "category": "DISASTER", "threat_level": "MEDIUM",
            "country": "United States",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat(),
        },
        {
            "event_id": "osint-hurricane-2",
            "title": "Hurricane warning issued for Florida coast - Category 4",
            "description": "National Hurricane Center issues warning as major hurricane approaches",
            "source": "GDACS", "category": "DISASTER", "threat_level": "CRITICAL",
            "country": "United States",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
        },
        {
            "event_id": "osint-crypto-1",
            "title": "ZachXBT publishes evidence of Axiom exchange manipulation",
            "description": "On-chain researcher reveals wash trading on Axiom platform",
            "source": "RSS", "category": "ECONOMIC", "threat_level": "HIGH",
            "country": "Global",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=36)).isoformat(),
        },
    ]
    added = store.add_events(osint_events)
    print(f"   Added {added} OSINT events to vector store")

    # 2. Create test anomalies
    print("\n[2/4] Generating mock anomalies...")
    now = datetime.now(timezone.utc)
    mock_anomalies = [
        {
            "market_id": "tariff-china-march",
            "market_name": "Will the US announce new China tariffs before March 1?",
            "wallet_address": "0x" + "a1" * 20,
            "wallet_age_days": 3,
            "wallet_trades": 2,
            "trade_size": 47500,
            "price_before": 0.35,
            "price_after": 0.89,
            "z_score": 4.2,
            "trade_timestamp": (now - timedelta(hours=24)).isoformat(),
        },
        {
            "market_id": "iran-strike",
            "market_name": "Will Israel strike Iranian nuclear facilities this month?",
            "wallet_address": "0x" + "b2" * 20,
            "wallet_age_days": 180,
            "wallet_trades": 45,
            "trade_size": 15000,
            "price_before": 0.22,
            "price_after": 0.78,
            "z_score": 3.1,
            "trade_timestamp": (now - timedelta(hours=8)).isoformat(),
        },
        {
            "market_id": "hurricane-fl",
            "market_name": "Will a hurricane make landfall in Florida this season?",
            "wallet_address": "0x" + "c3" * 20,
            "wallet_age_days": 90,
            "wallet_trades": 22,
            "trade_size": 8000,
            "price_before": 0.45,
            "price_after": 0.92,
            "z_score": 2.5,
            "trade_timestamp": (now - timedelta(hours=6)).isoformat(),
        },
        {
            "market_id": "random-spec",
            "market_name": "Will it rain in New York next Tuesday?",
            "wallet_address": "0x" + "d4" * 20,
            "wallet_age_days": 60,
            "wallet_trades": 12,
            "trade_size": 500,
            "price_before": 0.50,
            "price_after": 0.55,
            "z_score": 0.4,
            "trade_timestamp": (now - timedelta(hours=1)).isoformat(),
        },
    ]
    print(f"   Generated {len(mock_anomalies)} mock anomalies")

    # 3. Enrich with OSINT correlation
    print("\n[3/4] Correlating with OSINT events...")
    correlator = MarketCorrelator(vector_store=store)
    enriched = correlator.batch_correlate(mock_anomalies)
    for a in enriched:
        sig_before = a.get("osint_signals_before_trade", 0)
        pattern = a.get("information_asymmetry", "UNKNOWN")
        print(f"   {a['market_name'][:50]:50s} | signals_before={sig_before} | {pattern}")

    # 4. Run through classification pipeline
    print("\n[4/4] Running classification pipeline...")
    pipeline = SentinelPipeline(skip_low_suspicion=False)
    results = pipeline.process_batch(enriched, save_to_db=True)

    # Summary
    print("\n" + "=" * 60)
    print("PIPELINE RESULTS")
    print("=" * 60)
    for r in results:
        print(f"  {r.case_id:15s} | {r.classification:15s} | BSS={r.bss_score:3d} PES={r.pes_score:3d} | conf={r.confidence:.0%}")
        if r.sar_report:
            print(f"  {'':15s} | SAR report generated")

    print(f"\nTotal: {len(results)} cases processed and saved to database")
    store.clear()


def _pipeline_live():
    """Fetch live market data, gather OSINT from ALL sources, and classify."""
    import math
    import time as _time
    import os
    from datetime import datetime, timezone
    from src.data.database import init_schema
    from src.data.polymarket_client import PolymarketClient
    from src.osint.rss_aggregator import RSSAggregator
    from src.osint.sources import GDELTClient, GDACSClient, ACLEDClient, FIRMSClient
    from src.osint.vector_store import VectorStore
    from src.osint.correlator import MarketCorrelator
    from src.classification.pipeline import SentinelPipeline

    DELAY = 3  # seconds between external API calls to avoid rate limits

    print("=" * 60)
    print("SENTINEL PIPELINE - LIVE MODE")
    print("=" * 60)

    init_schema()

    polymarket = PolymarketClient()
    store = VectorStore()
    correlator = MarketCorrelator(vector_store=store)
    pipeline = SentinelPipeline(skip_low_suspicion=False)

    # =========================================================
    # 1. Fetch top markets by volume
    # =========================================================
    print("\n[1/5] Fetching active markets from Polymarket...")
    try:
        markets = polymarket.get_markets(limit=20, order="volume24hr")
        print(f"   Fetched {len(markets)} markets")
    except Exception as e:
        print(f"   Failed to fetch markets: {e}")
        return

    # =========================================================
    # 2. Gather OSINT from ALL sources (RSS first — most reliable)
    # =========================================================
    print("\n[2/5] Gathering OSINT signals from all sources...")
    all_osint = []

    # --- RSS feeds: Reuters, AP, BBC, Bloomberg, ESPN, etc. ---
    # Most reliable source — no API key, no rate limits
    print("   --- RSS Feeds (primary) ---")
    rss = RSSAggregator()
    try:
        rss_items = rss.fetch_all(max_age_hours=72)
        if rss_items:
            # Convert NewsItem objects to dicts for the vector store
            for item in rss_items:
                osint_dict = {
                    "event_id": f"rss-{item.item_id}" if hasattr(item, "item_id") else f"rss-{hash(item.title) & 0xFFFFFFFF:08x}",
                    "title": item.title,
                    "description": getattr(item, "summary", "") or getattr(item, "description", "") or item.title,
                    "source": f"RSS:{item.source}",
                    "category": getattr(item, "category", "NEWS"),
                    "threat_level": "INFO",
                    "url": getattr(item, "url", getattr(item, "link", "")),
                    "timestamp": item.published.isoformat() if hasattr(item, "published") and item.published else datetime.now(timezone.utc).isoformat(),
                }
                all_osint.append(osint_dict)
            print(f"   RSS [all feeds]: {len(rss_items)} articles")
    except Exception as e:
        print(f"   RSS [all feeds]: failed ({e})")

    # --- GDELT: intelligence topics (may rate-limit) ---
    print("   --- GDELT (intelligence topics) ---")
    gdelt = GDELTClient()
    gdelt_topics = ["military", "sanctions", "nuclear"]
    for topic in gdelt_topics:
        try:
            _time.sleep(DELAY)
            events = gdelt.search_topic(topic, timespan="72h", max_records=15)
            if events:
                all_osint.extend(events)
                print(f"   GDELT [{topic}]: {len(events)} events")
        except Exception as e:
            print(f"   GDELT [{topic}]: unavailable ({type(e).__name__})")

    # --- GDELT: market-specific queries ---
    stop_words = {"will", "what", "does", "this", "that", "have", "been",
                  "before", "after", "next", "2026", "2025", "february",
                  "march", "january", "from", "the", "win", "2026?"}
    seen_keywords = set()
    for market in markets[:6]:
        name = market.get("question", market.get("title", ""))
        words = [w.strip("?") for w in name.split()
                 if len(w) > 3 and w.lower().strip("?") not in stop_words]
        query = " ".join(words[:3])
        if not query or query in seen_keywords:
            continue
        seen_keywords.add(query)
        try:
            _time.sleep(DELAY)
            events = gdelt.search_documents(query, max_records=10, timespan="72h")
            if events:
                all_osint.extend(events)
                print(f"   GDELT [{query[:35]:35s}]: {len(events)} events")
        except Exception as e:
            print(f"   GDELT [{query[:35]:35s}]: unavailable ({type(e).__name__})")

    # --- GDACS: disaster alerts (no key needed) ---
    print("   --- GDACS (disasters) ---")
    gdacs = GDACSClient()
    try:
        _time.sleep(DELAY)
        gdacs_events = gdacs.get_events(min_alert_level="green")
        if gdacs_events:
            all_osint.extend(gdacs_events)
            print(f"   GDACS [disasters]: {len(gdacs_events)} events")
        else:
            print(f"   GDACS [disasters]: 0 events")
    except Exception as e:
        print(f"   GDACS [disasters]: unavailable ({type(e).__name__})")

    # --- ACLED: armed conflict (needs token) ---
    print("   --- ACLED (conflict) ---")
    acled_token = os.getenv("ACLED_ACCESS_TOKEN")
    if acled_token:
        acled = ACLEDClient(acled_token)
        try:
            _time.sleep(DELAY)
            acled_events = acled.get_events(days=7, limit=50)
            if acled_events:
                all_osint.extend(acled_events)
                print(f"   ACLED [conflict]: {len(acled_events)} events")
        except Exception as e:
            print(f"   ACLED [conflict]: unavailable ({type(e).__name__})")
    else:
        print("   ACLED [conflict]: skipped (no ACLED_ACCESS_TOKEN)")

    # --- NASA FIRMS: fire detections (needs key) ---
    print("   --- NASA FIRMS (fires) ---")
    firms_key = os.getenv("NASA_FIRMS_API_KEY")
    if firms_key:
        firms = FIRMSClient(firms_key)
        try:
            _time.sleep(DELAY)
            firms_events = firms.get_fires(days=3)
            if firms_events:
                all_osint.extend(firms_events)
                print(f"   FIRMS [fires]: {len(firms_events)} events")
        except Exception as e:
            print(f"   FIRMS [fires]: unavailable ({type(e).__name__})")
    else:
        print("   FIRMS [fires]: skipped (no NASA_FIRMS_API_KEY)")

    # --- Index all OSINT into vector store ---
    print(f"\n   Indexing {len(all_osint)} OSINT events into vector store...")
    if all_osint:
        _time.sleep(1)
        added = store.add_osint_objects(all_osint)
        print(f"   Indexed {added} events in vector store")
    else:
        print("   WARNING: No OSINT events gathered from any source")

    # =========================================================
    # 3. Build anomaly entries from top markets
    # =========================================================
    print("\n[3/5] Building market profiles...")
    anomalies = []
    for market in markets:
        market_id = (
            market.get("condition_id")
            or market.get("conditionId")
            or market.get("id", "unknown")
        )
        market_name = market.get("question", market.get("title", "Unknown"))
        volume = float(market.get("volume24hr", 0) or 0)

        if volume < 1000:
            continue

        try:
            prices = polymarket.get_prices(market)
            yes_price = prices.get("yes")
            no_price = prices.get("no")
            current_price = float(yes_price if yes_price is not None else (no_price if no_price is not None else 0.5))
        except Exception:
            current_price = 0.5

        # Estimate a z-score proxy from price extremity and volume
        price_extremity = abs(current_price - 0.5) * 2  # 0-1 scale
        volume_log = math.log10(max(volume, 1))
        z_proxy = round(price_extremity * 2 + volume_log / 3, 2)

        anomaly = {
            "market_id": market_id,
            "market_name": market_name,
            "wallet_address": "0x_live_scan",
            "wallet_age_days": 30,
            "wallet_trades": 10,
            "trade_size": volume,
            "price_before": 0.50,
            "price_after": current_price,
            "z_score": z_proxy,
            "market_volume_24h": volume,
            "trade_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        anomalies.append(anomaly)
        print(f"   {market_name[:55]:55s} | price={current_price:.2f} vol=${volume:,.0f} z={z_proxy:.1f}")

    if not anomalies:
        print("   No markets with sufficient volume")
        return

    # =========================================================
    # 4. Correlate with OSINT
    # =========================================================
    print(f"\n[4/5] Correlating {len(anomalies)} markets with OSINT ({store.count()} events in store)...")
    enriched = correlator.batch_correlate(anomalies)
    for a in enriched:
        sig = a.get("osint_signals_before_trade", 0)
        pattern = a.get("information_asymmetry", "UNKNOWN")
        if sig > 0:
            print(f"   {a['market_name'][:55]:55s} | signals={sig} {pattern}")

    # =========================================================
    # 5. Classify top candidates (limit to 5 to manage API cost)
    # =========================================================
    # Sort by OSINT signal count (prefer markets with correlation),
    # then by z-score as tiebreaker
    enriched.sort(
        key=lambda a: (a.get("osint_signals_before_trade", 0), a.get("z_score", 0)),
        reverse=True,
    )
    to_classify = enriched[:5]

    print(f"\n[5/5] Classifying top {len(to_classify)} markets (with {DELAY}s delay between calls)...")
    results = []
    for i, anomaly in enumerate(to_classify, 1):
        if i > 1:
            _time.sleep(DELAY)
        print(f"\n   [{i}/{len(to_classify)}] {anomaly['market_name'][:55]}")
        sigs = anomaly.get("osint_signals_before_trade", 0)
        if sigs > 0:
            print(f"       OSINT signals: {sigs} | {anomaly.get('information_asymmetry', 'UNKNOWN')}")
        try:
            result = pipeline.process_anomaly(anomaly, save_to_db=True)
            results.append(result)
            print(f"       -> {result.classification} | BSS={result.bss_score} PES={result.pes_score} | conf={result.confidence:.0%}")
        except Exception as e:
            print(f"       -> ERROR: {e}")

    print(f"\n{'=' * 60}")
    print("LIVE PIPELINE RESULTS")
    print("=" * 60)
    for r in results:
        print(f"  {r.case_id:15s} | {r.classification:15s} | BSS={r.bss_score:3d} PES={r.pes_score:3d} | conf={r.confidence:.0%}")
        if r.sar_report:
            print(f"  {'':15s} | SAR report generated")

    print(f"\nProcessed {len(results)} live markets ({len(all_osint)} OSINT events gathered)")
    store.clear()


def _pipeline_backfill():
    """Reprocess existing database anomalies through the classification pipeline."""
    from src.data.database import get_connection, list_anomalies
    from src.osint.vector_store import VectorStore
    from src.osint.correlator import MarketCorrelator
    from src.classification.pipeline import SentinelPipeline

    print("=" * 60)
    print("SENTINEL PIPELINE - BACKFILL MODE")
    print("=" * 60)

    conn = get_connection()
    anomalies = list_anomalies(conn, limit=100)
    conn.close()

    if not anomalies:
        print("No anomalies in database to reprocess")
        return

    print(f"Found {len(anomalies)} anomalies to reprocess")

    store = VectorStore()
    correlator = MarketCorrelator(vector_store=store)
    pipeline = SentinelPipeline(skip_low_suspicion=False)

    enriched = correlator.batch_correlate(anomalies)
    results = pipeline.process_batch(enriched, save_to_db=True)

    print(f"\nReprocessed {len(results)} anomalies")


# ------------------------------------------------------------------
# Real-time Monitor
# ------------------------------------------------------------------

def run_monitor(args: list):
    """
    Run the real-time trade monitor.

    Streams trades (live WebSocket or mock), enriches each trade with
    wallet + cluster + OSINT context, and classifies via the AI pipeline.

    Modes:
      --mock   Generate mock trades for local demo/testing
      --live   Connect to Polymarket WebSocket for real trades
    """
    import asyncio
    import os
    from dotenv import load_dotenv
    load_dotenv()

    from src.data.database import init_schema
    from src.pipeline.evidence_correlator import EvidenceCorrelator

    init_schema()

    mode = "mock"
    num_trades = 20
    for arg in args:
        if arg.startswith("--"):
            mode = arg.lstrip("-")
        elif arg.isdigit():
            num_trades = int(arg)

    correlator = EvidenceCorrelator(
        api_key=os.getenv("MISTRAL_API_KEY"),
        acled_token=os.getenv("ACLED_ACCESS_TOKEN"),
        firms_key=os.getenv("NASA_FIRMS_API_KEY"),
    )

    if mode == "mock":
        print("=" * 60)
        print("SENTINEL MONITOR - MOCK MODE")
        print(f"Processing {num_trades} mock trades...")
        print("=" * 60)
        asyncio.run(correlator.run_mock(num_trades=num_trades, delay_seconds=0.25))
        print("\nMock monitoring complete.")

    elif mode == "live":
        print("=" * 60)
        print("SENTINEL MONITOR - LIVE MODE")
        print("Connecting to Polymarket WebSocket...")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        try:
            asyncio.run(correlator.run_live())
        except KeyboardInterrupt:
            print("\nMonitor stopped.")

    else:
        print(f"Unknown monitor mode: {mode}")
        print("Usage: python main.py monitor [--mock|--live] [num_trades]")


def run_api():
    """Launch FastAPI backend."""
    print("Launching Sentinel API on http://localhost:8000")
    subprocess.run(["uvicorn", "src.api.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"])


def run_metrics():
    """Compute and print evaluation metrics from Arena consensus."""
    import json
    from src.data.database import get_connection
    from src.classification.evaluation import compute_evaluation_metrics

    conn = get_connection()
    try:
        metrics = compute_evaluation_metrics(conn)
    finally:
        conn.close()

    print("=" * 60)
    print("SENTINEL EVALUATION METRICS")
    print("=" * 60)
    print(json.dumps(metrics, indent=2))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    if command == "init":
        init_db()
    elif command == "dashboard":
        run_dashboard()
    elif command == "pipeline":
        run_pipeline(sys.argv[2:])
    elif command == "monitor":
        run_monitor(sys.argv[2:])
    elif command == "api":
        run_api()
    elif command == "metrics":
        run_metrics()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
