# SENTINEL: Technical Implementation Guide

## Document Purpose

This document decomposes the Sentinel PRD into **six independent workstreams**, each designed to be handed to a separate coding agent (e.g., Claude Code). Each workstream is self-contained with explicit inputs, outputs, file structures, API contracts, and acceptance criteria. Agents can work in parallel. Integration points are defined via shared data schemas.

---

## System Overview

Sentinel is an autonomous monitoring system that detects information asymmetry in prediction markets. It distinguishes between unlawful insider trading and legitimate OSINT research by combining Polymarket trade data, on-chain wallet behavior, and real-world OSINT signals, then classifying anomalies through a two-stage Mistral AI pipeline.

### Architecture Diagram (Logical)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION LAYER                             │
│                                                                          │
│  ┌─────────────────┐   ┌──────────────────┐   ┌──────────────────────┐  │
│  │  Polymarket      │   │  Wallet Profiler │   │  OSINT / worldmonitor│  │
│  │  CLOB API        │   │  (Polygon RPC)   │   │  (RSS, ADS-B, AIS,  │  │
│  │  (pselamy fork)  │   │  (pselamy fork)  │   │   ACLED, GDELT)      │  │
│  └────────┬─────────┘   └────────┬─────────┘   └──────────┬───────────┘  │
│           │                      │                         │              │
│           ▼                      ▼                         ▼              │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                    UNIFIED EVENT BUS (SQLite)                     │    │
│  │  anomalies table  |  wallet_profiles table  |  osint_events table │    │
│  └──────────────────────────────┬───────────────────────────────────┘    │
└─────────────────────────────────┼────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼────────────────────────────────────────┐
│                    FEATURE ENGINEERING LAYER                              │
│                                                                          │
│  ┌──────────────────────────────▼───────────────────────────────────┐    │
│  │  Spearman Clustering -> Hierarchical Clades                      │    │
│  │  Permutation Importance Weighting                                │    │
│  │  Output: Structured Feature Payload (JSON)                       │    │
│  └──────────────────────────────┬───────────────────────────────────┘    │
└─────────────────────────────────┼────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼────────────────────────────────────────┐
│                    AI CLASSIFICATION PIPELINE                             │
│                                                                          │
│  ┌──────────────────────────────▼──────────────────┐                    │
│  │  Stage 1: Mistral Small (Fine-Tuned)            │                    │
│  │  -> 4-class: INSIDER | OSINT_EDGE |             │                    │
│  │     FAST_REACTOR | SPECULATOR                   │                    │
│  │  -> PES Score, BSS Score                        │                    │
│  └──────────────────────────────┬──────────────────┘                    │
│                                 │ (if BSS > threshold)                   │
│  ┌──────────────────────────────▼──────────────────┐                    │
│  │  Stage 2: Magistral + RAG (ChromaDB)            │                    │
│  │  -> XAI Narrative                               │                    │
│  │  -> Temporal Gap Analysis                       │                    │
│  │  -> Fraud Triangle Mapping                      │                    │
│  └──────────────────────────────┬──────────────────┘                    │
│                                 │                                        │
│  ┌──────────────────────────────▼──────────────────┐                    │
│  │  Stage 3: Mistral Large -> SAR JSON             │                    │
│  └──────────────────────────────┬──────────────────┘                    │
└─────────────────────────────────┼────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼────────────────────────────────────────┐
│                    PRESENTATION LAYER                                     │
│                                                                          │
│  ┌──────────────────────────────▼──────────────────┐                    │
│  │  Dashboard (React/Streamlit)                    │                    │
│  │  - Temporal Gap Visualization                   │                    │
│  │  - XAI Narrative Display                        │                    │
│  │  - Human Consensus Arena                        │                    │
│  │  - Sentinel Index Browser                       │                    │
│  └─────────────────────────────────────────────────┘                    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Shared Data Contracts

All workstreams communicate through these schemas. Every agent must read this section first.

### Schema 1: `anomaly_event` (SQLite table + JSON)

This is the core data object that flows through the entire pipeline.

```sql
CREATE TABLE anomaly_events (
    id TEXT PRIMARY KEY,                    -- UUID
    detected_at TEXT NOT NULL,              -- ISO 8601 timestamp
    market_id TEXT NOT NULL,               -- Polymarket condition_id
    market_question TEXT,                  -- Human-readable market title
    market_slug TEXT,                      -- URL slug

    -- Anomaly Detection Fields
    anomaly_type TEXT NOT NULL,            -- 'VOLUME_SPIKE' | 'PRICE_JUMP' | 'FRESH_WALLET' | 'SIZE_ANOMALY' | 'SNIPER_CLUSTER'
    p_value REAL,                          -- Statistical significance
    z_score REAL,                          -- Standard deviations from baseline
    baseline_volume REAL,                  -- Rolling 7-day average volume
    observed_volume REAL,                  -- Volume at detection time
    price_before REAL,                     -- Price 1h before anomaly
    price_at_detection REAL,              -- Price at anomaly detection
    price_delta REAL,                      -- Absolute price change

    -- Wallet Fields
    wallet_address TEXT,                   -- Primary wallet involved
    wallet_age_hours REAL,                -- Hours since first tx
    wallet_tx_count INTEGER,              -- Lifetime transaction count
    wallet_unique_markets INTEGER,        -- Number of distinct markets traded
    trade_size_usdc REAL,                 -- Size of the flagged trade
    order_book_impact REAL,               -- % of visible order book consumed
    cluster_size INTEGER,                  -- Number of wallets in cluster (DBSCAN)

    -- Scores (populated by AI pipeline)
    bss_score REAL,                        -- Behavioral Suspicion Score (0-100)
    pes_score REAL,                        -- Public Explainability Score (0-100)
    classification TEXT,                   -- 'INSIDER' | 'OSINT_EDGE' | 'FAST_REACTOR' | 'SPECULATOR'
    confidence REAL,                       -- Model confidence (0-1)

    -- XAI Fields (populated by Magistral)
    xai_narrative TEXT,                    -- Human-readable explanation
    temporal_gap_minutes REAL,            -- Minutes between trade and news break
    fraud_triangle_json TEXT,             -- JSON: {opportunity, pressure, rationalization}
    osint_signals_found TEXT,             -- JSON array of matching OSINT events

    -- SAR Fields (populated by Mistral Large)
    sar_json TEXT,                          -- Full SAR report as JSON

    -- Human Consensus
    consensus_score REAL,                  -- Arena voting result (-1 to 1)
    vote_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',         -- 'pending' | 'classified' | 'reviewed' | 'archived'

    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
```

### Schema 2: `osint_event` (SQLite table + ChromaDB document)

```sql
CREATE TABLE osint_events (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,                  -- 'rss' | 'adsb' | 'ais' | 'acled' | 'gdelt' | 'twitter' | 'discord'
    source_name TEXT,                      -- e.g., 'Reuters', 'Breaking Defense'
    source_tier INTEGER,                   -- 1-4 credibility tier
    event_type TEXT,                       -- 'conflict' | 'political' | 'economic' | 'military' | 'disaster'
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT,
    published_at TEXT NOT NULL,           -- ISO 8601
    ingested_at TEXT DEFAULT (datetime('now')),
    latitude REAL,
    longitude REAL,
    country_code TEXT,                     -- ISO 3166-1 alpha-2
    entities_json TEXT,                    -- JSON array of extracted entities
    keywords_json TEXT,                    -- JSON array of keywords
    severity TEXT,                          -- 'critical' | 'high' | 'medium' | 'low' | 'info'
    relevance_to_markets TEXT             -- JSON array of matching market_ids
);
```

### Schema 3: `wallet_profile` (SQLite table)

```sql
CREATE TABLE wallet_profiles (
    wallet_address TEXT PRIMARY KEY,
    first_seen TEXT,
    last_seen TEXT,
    total_tx_count INTEGER,
    polymarket_tx_count INTEGER,
    unique_markets_traded INTEGER,
    total_volume_usdc REAL,
    avg_trade_size_usdc REAL,
    max_trade_size_usdc REAL,
    win_rate REAL,
    funding_source TEXT,                   -- 'cex' | 'dex' | 'bridge' | 'unknown'
    funding_chain_json TEXT,              -- JSON array tracing fund origins
    cluster_id TEXT,                       -- DBSCAN cluster identifier
    cluster_wallets_json TEXT,            -- JSON array of related wallets
    risk_score REAL,                        -- Composite suspicion (0-100)
    is_fresh_wallet BOOLEAN,
    profile_json TEXT,                     -- Full profiling data
    updated_at TEXT DEFAULT (datetime('now'))
);
```

### Schema 4: `sentinel_index` (the curated case database)

```sql
CREATE TABLE sentinel_index (
    case_id TEXT PRIMARY KEY,
    anomaly_event_id TEXT REFERENCES anomaly_events(id),
    classification TEXT NOT NULL,
    confidence REAL,
    consensus_score REAL,
    sar_json TEXT,
    xai_narrative TEXT,
    temporal_gap_minutes REAL,
    fraud_triangle_json TEXT,
    market_question TEXT,
    market_outcome TEXT,                   -- 'resolved_yes' | 'resolved_no' | 'pending'
    outcome_verified BOOLEAN DEFAULT FALSE,
    created_at TEXT DEFAULT (datetime('now')),
    notes TEXT
);
```

### Environment Variables (Shared `.env`)

```bash
# Polymarket
POLYMARKET_API_BASE=https://clob.polymarket.com
POLYMARKET_GAMMA_API=https://gamma-api.polymarket.com

# Blockchain
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY

# Mistral AI
MISTRAL_API_KEY=your_key_here

# ChromaDB
CHROMA_PERSIST_DIR=./data/chromadb

# OSINT (from worldmonitor)
GROQ_API_KEY=gsk_xxx                    # For threat classification fallback
OPENSKY_USERNAME=xxx                     # ADS-B flight data
OPENSKY_PASSWORD=xxx
VESSELFINDER_API_KEY=xxx                 # AIS maritime data
NASA_FIRMS_API_KEY=xxx                   # Satellite fire detection

# Database
SENTINEL_DB_PATH=./data/sentinel.db

# Optional: Alert Channels
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## WORKSTREAM 1: Polymarket Data Ingestion & Anomaly Detection

**Agent Assignment: "Data Engineer"**
**Estimated Effort: 4-6 hours**
**Dependencies: None (first to start)**

### Objective

Build the market data ingestion layer that continuously polls Polymarket, computes rolling statistical baselines, and emits `anomaly_event` records when thresholds are breached.

### Strategy: Fork from `pselamy/polymarket-insider-tracker`

Do NOT write Polymarket API wrappers from scratch. The `pselamy/polymarket-insider-tracker` repo (Python, MIT license) already has:
- CLOB API client (`src/ingestor/clob_client.py`)
- WebSocket event handler (`src/ingestor/websocket.py`)
- Fresh wallet detection (`src/detector/fresh_wallet.py`)
- Size anomaly detection (`src/detector/size_anomaly.py`)
- DBSCAN sniper cluster detection (`src/detector/sniper.py`)
- Composite risk scoring (`src/detector/scorer.py`)
- Wallet profiling (`src/profiler/analyzer.py`, `chain.py`, `funding.py`)
- SQLAlchemy models (`src/storage/models.py`)

### What to Fork vs. What to Build

**Fork directly (adapt, don't rewrite):**
- `clob_client.py` -- Polymarket CLOB API integration
- `websocket.py` -- Real-time trade event streaming
- `fresh_wallet.py` -- Wallet age detection
- `size_anomaly.py` -- Trade size relative to market depth
- `sniper.py` -- DBSCAN clustering
- `scorer.py` -- Composite risk scoring
- `analyzer.py` + `chain.py` + `funding.py` -- Wallet profiling + funding chain tracing

**Build new:**
1. Rolling baseline / p-value anomaly detection
2. SQLite schema integration (migrate from their PostgreSQL/SQLAlchemy to our SQLite schema)
3. Anomaly event emitter that writes to `anomaly_events` table

### Detailed Implementation

#### 1.1 Project Setup

```
sentinel/
├── workstream_1_ingestion/
│   ├── __init__.py
│   ├── config.py                  # Environment variables, thresholds
│   ├── polymarket_client.py       # Forked from pselamy clob_client.py
│   ├── websocket_handler.py       # Forked from pselamy websocket.py
│   ├── wallet_profiler.py         # Forked from pselamy profiler/
│   ├── detectors/
│   │   ├── __init__.py
│   │   ├── fresh_wallet.py        # Forked
│   │   ├── size_anomaly.py        # Forked
│   │   ├── sniper_cluster.py      # Forked (DBSCAN)
│   │   ├── volume_spike.py        # NEW: rolling baseline + p-value
│   │   ├── price_jump.py          # NEW: price movement detection
│   │   └── scorer.py              # Forked + extended
│   ├── anomaly_emitter.py         # NEW: writes to SQLite
│   ├── db.py                      # SQLite connection + schema init
│   ├── main.py                    # Entry point: polling loop
│   └── backtest.py                # Historical analysis script
```

#### 1.2 Rolling Baseline Anomaly Detection (volume_spike.py)

This is the core statistical engine. Use Welford's online algorithm (same approach as worldmonitor) for numerically stable streaming mean/variance.

```python
"""
volume_spike.py -- Rolling baseline anomaly detection for Polymarket markets.

Approach:
- Maintain a 7-day rolling window of hourly volume snapshots per market.
- Use Welford's online algorithm for streaming mean/variance.
- Compute z-score for each new observation.
- If z-score > threshold, emit VOLUME_SPIKE anomaly.
- Also compute a p-value using scipy.stats.norm.sf(z_score) for the anomaly_event record.

Thresholds (configurable via config.py):
  Z >= 2.0 -> flag as anomaly (medium confidence)
  Z >= 3.0 -> flag as anomaly (high confidence)
  Minimum 48 hourly observations before flagging (prevent cold-start false positives)
"""

import math
import sqlite3
from datetime import datetime, timedelta
from scipy import stats
from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class WelfordState:
    """Welford's online algorithm for streaming mean/variance."""
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0

    def update(self, value: float):
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2

    @property
    def variance(self) -> float:
        if self.count < 2:
            return 0.0
        return self.m2 / (self.count - 1)

    @property
    def stddev(self) -> float:
        return math.sqrt(self.variance)

    def z_score(self, value: float) -> float:
        if self.stddev == 0 or self.count < 48:
            return 0.0
        return (value - self.mean) / self.stddev


class VolumeAnomalyDetector:
    """
    Maintains per-market rolling baselines and detects volume spikes.

    Usage:
        detector = VolumeAnomalyDetector(db_conn)
        anomalies = detector.check(market_id, current_hourly_volume)
    """

    def __init__(self, db_conn: sqlite3.Connection, z_threshold: float = 2.0):
        self.db = db_conn
        self.z_threshold = z_threshold
        self.baselines: dict[str, WelfordState] = {}  # market_id -> WelfordState
        self._load_baselines()

    def _load_baselines(self):
        """Load persisted baseline states from SQLite on startup."""
        # Implementation: query a baselines table for serialized WelfordState per market
        pass

    def check(self, market_id: str, market_question: str, current_volume: float,
              current_price: float) -> Optional[dict]:
        """
        Check if current volume is anomalous.
        Returns anomaly_event dict if threshold breached, else None.
        """
        if market_id not in self.baselines:
            self.baselines[market_id] = WelfordState()

        state = self.baselines[market_id]
        z = state.z_score(current_volume)
        p_value = stats.norm.sf(abs(z)) * 2  # two-tailed

        # Update baseline AFTER computing z-score
        state.update(current_volume)

        if abs(z) >= self.z_threshold and state.count >= 48:
            return {
                "id": str(uuid.uuid4()),
                "detected_at": datetime.utcnow().isoformat(),
                "market_id": market_id,
                "market_question": market_question,
                "anomaly_type": "VOLUME_SPIKE",
                "p_value": p_value,
                "z_score": z,
                "baseline_volume": state.mean,
                "observed_volume": current_volume,
                "price_at_detection": current_price,
            }
        return None
```

#### 1.3 Price Jump Detection (price_jump.py)

Same Welford approach but tracking hourly price deltas:

```python
"""
price_jump.py -- Detect abnormal price movements.

Track the distribution of hourly absolute price changes per market.
Flag when a price move exceeds 2 standard deviations from the rolling mean of price deltas.
"""

# Same WelfordState pattern as volume_spike.py but operating on:
#   value = abs(price_now - price_1h_ago)
#
# Emit anomaly_type = "PRICE_JUMP" with:
#   price_before = price_1h_ago
#   price_at_detection = price_now
#   price_delta = price_now - price_1h_ago
```

#### 1.4 Composite Anomaly Emitter (anomaly_emitter.py)

Aggregates signals from all detectors and writes to `anomaly_events`:

```python
"""
anomaly_emitter.py -- Collects detector outputs, enriches with wallet data, writes to SQLite.

Flow:
1. Receive raw anomaly dict from any detector
2. Look up wallet_profile for the primary wallet (if wallet-based anomaly)
3. Merge wallet fields into the anomaly dict
4. Insert into anomaly_events table
5. Return the anomaly_event_id for downstream consumption
"""
```

#### 1.5 Main Polling Loop (main.py)

```python
"""
main.py -- Entry point for the ingestion workstream.

Two modes:
  1. LIVE MODE: Poll Polymarket CLOB API every 60 seconds for active markets.
     For each market, fetch current volume and price.
     Run through VolumeAnomalyDetector and PriceJumpDetector.
     On WebSocket trade events, also run FreshWalletDetector, SizeAnomalyDetector, SniperClusterDetector.

  2. BACKTEST MODE: Load historical trade data and replay through detectors.
     Use this to generate ground-truth training data for the fine-tuning JSONL.
     Run: python -m workstream_1_ingestion.main --backtest --days 60
"""
```

#### 1.6 Backtest Script for Ground Truth (backtest.py)

Critical for Workstream 4 (fine-tuning data). Run the `pselamy` detection pipeline over 60 days of historical Polymarket data:

```python
"""
backtest.py -- Generate labeled historical anomalies for fine-tuning.

Steps:
1. Fetch historical trades from Polymarket CLOB API (paginated, last 60 days)
2. Replay each trade through all detectors
3. For each flagged anomaly, check if the market has since resolved
4. If resolved, check if the flagged wallet was correct (trade direction matched outcome)
5. Output: labeled anomalies with fields:
   - All anomaly_event fields
   - outcome: 'correct_prediction' | 'incorrect_prediction' | 'unresolved'
   - timing_advantage_hours: how many hours before resolution the trade was placed
6. Save to both SQLite and a JSONL file for fine-tuning prep

This gives us REAL historical anomalies with known outcomes, which Workstream 4
will use to build training data.
"""
```

### Acceptance Criteria

- [ ] Polymarket CLOB API client connects and fetches active markets
- [ ] Volume spike detector fires on synthetic test data (inject a 3x volume event)
- [ ] Price jump detector fires on synthetic test data
- [ ] Fresh wallet, size anomaly, and sniper cluster detectors work (forked from pselamy)
- [ ] All detected anomalies are written to `anomaly_events` SQLite table
- [ ] Wallet profiles are populated in `wallet_profiles` table
- [ ] Backtest mode can process 60 days of history and output labeled JSONL
- [ ] Main loop runs continuously without crashing for 10+ minutes

---

## WORKSTREAM 2: OSINT Data Ingestion & Vector Store

**Agent Assignment: "OSINT Engineer"**
**Estimated Effort: 4-6 hours**
**Dependencies: None (can run in parallel with Workstream 1)**

### Objective

Ingest real-time OSINT data from worldmonitor's data sources, store structured events in SQLite, and dump event summaries into ChromaDB for RAG retrieval by the AI pipeline.

### Strategy: Adapt worldmonitor's Data Layer

The `koala73/worldmonitor` repo (TypeScript/Vite) uses 30+ Vercel Edge Functions to proxy and normalize external APIs. We cannot directly fork the TypeScript code into our Python backend, but we CAN replicate their data source integrations. The key data sources from worldmonitor that matter for Sentinel:

| Source | worldmonitor Usage | Sentinel Usage | API |
|--------|-------------------|----------------|-----|
| **RSS Feeds (100+)** | News aggregation, threat classification | Cross-reference trade timing with news breaks | Direct RSS polling |
| **ACLED** | Conflict events, protests | Geopolitical event correlation | ACLED API |
| **GDELT** | Global event database | Event detection, entity extraction | GDELT API (public) |
| **OpenSky (ADS-B)** | Military flight tracking | Military activity correlation | OpenSky API |
| **VesselFinder (AIS)** | Naval vessel monitoring | Maritime activity correlation | VesselFinder API |
| **NASA FIRMS** | Satellite fire detection | Infrastructure/conflict events | NASA FIRMS API |
| **Polymarket** | Prediction market prices | Already handled by Workstream 1 | CLOB API |
| **Cloudflare Radar** | Internet outages | Infrastructure disruption signals | Cloudflare API |

### Detailed Implementation

#### 2.1 Project Structure

```
sentinel/
├── workstream_2_osint/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py                          # Shared SQLite (same DB as workstream 1)
│   ├── vector_store.py                # ChromaDB wrapper
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── rss_aggregator.py          # 80+ defense/energy/geopolitical RSS feeds
│   │   ├── acled_client.py            # ACLED conflict data
│   │   ├── gdelt_client.py            # GDELT event database
│   │   ├── opensky_client.py          # ADS-B military flight tracking
│   │   ├── ais_client.py              # Maritime vessel tracking
│   │   ├── nasa_firms_client.py       # Satellite fire detection
│   │   ├── social_monitor.py          # Twitter/Discord/Telegram keyword monitoring
│   │   └── cloudflare_radar.py        # Internet outage detection
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── entity_extractor.py        # NER for countries, orgs, people
│   │   ├── geo_locator.py             # Geolocation from text (worldmonitor's 74-hub approach)
│   │   ├── threat_classifier.py       # Keyword-based severity classification
│   │   └── market_correlator.py       # Match OSINT events to Polymarket markets
│   ├── main.py                        # Polling orchestrator
│   └── feed_list.py                   # Curated list of 80+ RSS feeds
```

#### 2.2 RSS Feed Aggregator (rss_aggregator.py)

```python
"""
rss_aggregator.py -- Poll 80+ curated RSS feeds for defense, energy, and geopolitical news.

Feed list sourced from worldmonitor's data layer. Organized by tier:

Tier 1 (Wire services, official):
  - Reuters World: https://www.reutersagency.com/feed/
  - AP Top News: https://rss.app/feeds/v1.1/xxx (or AP RSS endpoint)
  - BBC World: http://feeds.bbci.co.uk/news/world/rss.xml
  - DOD News: https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx

Tier 2 (Major outlets):
  - CNN World: http://rss.cnn.com/rss/edition_world.rss
  - Al Jazeera: https://www.aljazeera.com/xml/rss/all.xml
  - The Guardian World: https://www.theguardian.com/world/rss

Tier 3 (Specialized defense/energy):
  - Defense One: https://www.defenseone.com/rss/
  - Breaking Defense: https://breakingdefense.com/feed/
  - The War Zone: https://www.thedrive.com/the-war-zone/rss
  - Naval News: https://www.navalnews.com/feed/
  - OilPrice.com: https://oilprice.com/rss/main
  - Energy Intelligence: via RSS

Tier 4 (Aggregators, niche):
  - Google News (geopolitics): custom RSS URL
  - Liveuamap: scrape/RSS
  - OSINT analyst blogs

Implementation:
  - Use feedparser library
  - Poll each feed every 5 minutes (stagger to avoid burst)
  - Deduplicate by URL hash
  - Extract: title, summary, published date, source URL
  - Run through entity_extractor and threat_classifier
  - Write to osint_events table
  - Embed summary into ChromaDB
"""

import feedparser
import hashlib
from datetime import datetime
from typing import List, Dict


# Feed definitions with metadata
FEEDS = [
    {"url": "http://feeds.bbci.co.uk/news/world/rss.xml", "name": "BBC World", "tier": 1, "category": "general"},
    {"url": "http://rss.cnn.com/rss/edition_world.rss", "name": "CNN World", "tier": 2, "category": "general"},
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "name": "Al Jazeera", "tier": 2, "category": "general"},
    {"url": "https://www.defenseone.com/rss/", "name": "Defense One", "tier": 3, "category": "defense"},
    {"url": "https://breakingdefense.com/feed/", "name": "Breaking Defense", "tier": 3, "category": "defense"},
    # ... 75+ more feeds
    # Full list should be maintained in feed_list.py
]


class RSSAggregator:
    def __init__(self, db_conn, vector_store, feeds=FEEDS):
        self.db = db_conn
        self.vs = vector_store
        self.feeds = feeds
        self.seen_hashes = set()  # In-memory dedup, persist to SQLite on restart

    def poll_all(self) -> List[Dict]:
        """Poll all feeds and return new events."""
        new_events = []
        for feed_config in self.feeds:
            try:
                events = self._poll_feed(feed_config)
                new_events.extend(events)
            except Exception as e:
                # Circuit breaker: log and skip, don't crash the loop
                print(f"Feed error [{feed_config['name']}]: {e}")
        return new_events

    def _poll_feed(self, feed_config: dict) -> List[Dict]:
        parsed = feedparser.parse(feed_config["url"])
        events = []
        for entry in parsed.entries:
            url_hash = hashlib.sha256(entry.get("link", "").encode()).hexdigest()[:16]
            if url_hash in self.seen_hashes:
                continue
            self.seen_hashes.add(url_hash)

            event = {
                "id": url_hash,
                "source": "rss",
                "source_name": feed_config["name"],
                "source_tier": feed_config["tier"],
                "title": entry.get("title", ""),
                "summary": entry.get("summary", "")[:2000],
                "url": entry.get("link", ""),
                "published_at": entry.get("published", datetime.utcnow().isoformat()),
            }
            events.append(event)
        return events
```

#### 2.3 ChromaDB Vector Store (vector_store.py)

```python
"""
vector_store.py -- ChromaDB wrapper for OSINT event embeddings.

Purpose: Enable the Magistral XAI layer (Workstream 4) to query:
  "What public information was available at timestamp T
   that could explain trade activity on market M?"

Uses Mistral Embed (mistral-embed) for embedding generation.
Each document = one OSINT event summary with metadata.

ChromaDB collection schema:
  - document: "{title}. {summary}"
  - metadata: {source, source_tier, published_at, event_type, severity, country_code, keywords}
  - id: osint_event.id
"""

import chromadb
from chromadb.config import Settings
from mistralai import Mistral
import os


class SentinelVectorStore:
    def __init__(self, persist_dir: str = "./data/chromadb"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="osint_events",
            metadata={"hnsw:space": "cosine"}
        )
        self.mistral = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    def add_event(self, event: dict):
        """Embed and store an OSINT event."""
        text = f"{event['title']}. {event.get('summary', '')}"

        # Generate embedding via Mistral Embed
        embedding_response = self.mistral.embeddings.create(
            model="mistral-embed",
            inputs=[text]
        )
        embedding = embedding_response.data[0].embedding

        self.collection.add(
            ids=[event["id"]],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "source": event.get("source", ""),
                "source_name": event.get("source_name", ""),
                "source_tier": event.get("source_tier", 4),
                "published_at": event.get("published_at", ""),
                "event_type": event.get("event_type", ""),
                "severity": event.get("severity", "info"),
                "country_code": event.get("country_code", ""),
            }]
        )

    def query_by_timestamp_and_topic(
        self,
        query_text: str,
        before_timestamp: str,
        n_results: int = 10,
    ) -> list:
        """
        Find OSINT events relevant to a query that were published BEFORE a given timestamp.
        This is the core RAG query used by Magistral to determine if public info existed
        before a suspicious trade.
        """
        # Generate query embedding
        embedding_response = self.mistral.embeddings.create(
            model="mistral-embed",
            inputs=[query_text]
        )
        query_embedding = embedding_response.data[0].embedding

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results * 2,  # Over-fetch, then filter by timestamp
            where={"published_at": {"$lte": before_timestamp}},
        )
        return results
```

#### 2.4 ACLED Conflict Data (acled_client.py)

```python
"""
acled_client.py -- Ingest conflict events from ACLED.

ACLED provides structured data on political violence and protests worldwide.
API: https://acleddata.com/data-export-tool/

Poll every 30 minutes for new events.
Map ACLED event types to our severity scale:
  - Battles, Explosions/Remote violence -> critical
  - Violence against civilians -> high
  - Protests, Riots -> medium
  - Strategic developments -> low

Output: osint_event records with geolocation and entity data.
"""
```

#### 2.5 GDELT Client (gdelt_client.py)

```python
"""
gdelt_client.py -- Ingest events from the GDELT Project.

GDELT monitors world news from nearly every country in print, broadcast, and web formats.
Use GDELT 2.0 Events API: https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/

The GDELT GKG (Global Knowledge Graph) is particularly useful for entity extraction
and event tone analysis.

Poll the GDELT Events lastupdate file every 15 minutes:
  http://data.gdeltproject.org/gdeltv2/lastupdate.txt

Key fields to extract:
  - SQLDATE, Actor1Name, Actor2Name, EventCode (CAMEO)
  - GoldsteinScale (conflict intensity, -10 to +10)
  - NumMentions, AvgTone
  - ActionGeo_Lat, ActionGeo_Long
"""
```

#### 2.6 Market Correlator (market_correlator.py)

```python
"""
market_correlator.py -- Match OSINT events to active Polymarket markets.

This is the bridge between Workstream 2 (OSINT) and Workstream 1 (Market data).

Approach:
1. Maintain a list of active Polymarket markets with their questions and keywords.
2. For each new OSINT event, compute text similarity against market questions.
3. Use simple TF-IDF or keyword overlap (not embeddings -- keep it fast).
4. If similarity > threshold, add the market_id to the event's relevance_to_markets field.

Example:
  OSINT event: "Iran nuclear talks break down as IAEA reports enrichment increase"
  Matched market: "Will Iran reach a nuclear deal by 2026?" (market_id: 0x...)

This correlation is later used by the Magistral XAI layer to establish
whether a trader could have been reacting to public information.
"""
```

### Acceptance Criteria

- [ ] RSS aggregator polls at least 20 feeds successfully and deduplicates
- [ ] Events are written to `osint_events` SQLite table
- [ ] Events are embedded and stored in ChromaDB
- [ ] `query_by_timestamp_and_topic` returns relevant results with timestamp filtering
- [ ] ACLED client fetches and normalizes at least one batch of conflict events
- [ ] GDELT client fetches and normalizes at least one update cycle
- [ ] Market correlator matches at least 3 OSINT events to active Polymarket markets in testing
- [ ] Main loop runs all sources on their respective intervals without crashing

---

## WORKSTREAM 3: Feature Engineering & Hierarchical Clustering

**Agent Assignment: "ML Engineer"**
**Estimated Effort: 3-4 hours**
**Dependencies: Workstream 1 (needs anomaly_events and wallet_profiles data)**

### Objective

Transform raw anomaly data and wallet profiles into a structured, de-correlated feature payload using Spearman hierarchical clustering and Permutation Importance weighting. The output is a JSON feature vector that becomes the input to the Mistral classifier.

### Detailed Implementation

#### 3.1 Project Structure

```
sentinel/
├── workstream_3_features/
│   ├── __init__.py
│   ├── config.py
│   ├── clustering.py              # Spearman rank-order clustering
│   ├── feature_builder.py         # Raw feature extraction
│   ├── importance_weighting.py    # Permutation importance
│   ├── payload_formatter.py       # Format for Mistral prompt
│   └── main.py                    # CLI: process anomaly_events -> feature payloads
```

#### 3.2 Feature Extraction (feature_builder.py)

```python
"""
feature_builder.py -- Extract raw features from anomaly_events + wallet_profiles.

For each anomaly_event, produce a flat feature dictionary with these groups:

LIQUIDITY FEATURES:
  - observed_volume (float): Volume at detection time
  - baseline_volume (float): Rolling 7-day mean
  - volume_ratio (float): observed / baseline
  - order_book_impact (float): % of visible book consumed
  - market_daily_volume (float): Total market volume in last 24h

VOLATILITY FEATURES:
  - z_score (float): Standard deviations from baseline
  - price_delta (float): Absolute price change
  - price_velocity (float): price_delta / time_window_hours
  - idiosyncratic_vol (float): Market-specific volatility vs platform average

ENTITY/GOVERNANCE FEATURES:
  - wallet_age_hours (float): Hours since first transaction
  - wallet_tx_count (int): Lifetime transaction count
  - wallet_unique_markets (int): Number of distinct markets traded
  - trade_size_usdc (float): Size of the flagged trade
  - avg_trade_size_usdc (float): Wallet's historical average
  - trade_size_ratio (float): This trade / wallet average
  - is_fresh_wallet (bool): wallet_age_hours < 24
  - cluster_size (int): Number of wallets in DBSCAN cluster
  - win_rate (float): Wallet's historical win rate
  - funding_source (categorical): 'cex' | 'dex' | 'bridge' | 'unknown'
  - market_concentration (float): % of wallet's trades in this market

TIMING FEATURES:
  - hour_of_day (int): 0-23 UTC
  - day_of_week (int): 0-6
  - minutes_since_market_creation (float)
  - minutes_to_market_resolution (float, if known)
"""
```

#### 3.3 Spearman Hierarchical Clustering (clustering.py)

```python
"""
clustering.py -- Group correlated features into clades using Spearman rank-order correlation.

Purpose: The PRD requires features to be grouped into "clades" to prevent the classifier
from overfitting on highly correlated features. This follows the approach described in
the sklearn documentation on Permutation Importance with correlated features.

Algorithm:
1. Compute Spearman rank-order correlation matrix across all features.
2. Convert to distance matrix: distance = 1 - |correlation|
3. Build a hierarchical dendrogram using Ward's linkage.
4. Cut the dendrogram at a threshold (e.g., distance = 0.5) to form clusters.
5. For each cluster (clade), select the most representative feature
   (highest average correlation with other members).

Output clades (expected):
  - Liquidity Clade: volume_ratio, order_book_impact, market_daily_volume
  - Volatility Clade: z_score, price_velocity, idiosyncratic_vol
  - Entity Clade: wallet_age_hours, wallet_tx_count, is_fresh_wallet, cluster_size
  - Timing Clade: hour_of_day, minutes_since_market_creation
  - Size Clade: trade_size_usdc, trade_size_ratio, market_concentration
"""

import numpy as np
from scipy.stats import spearmanr
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import squareform


def compute_clades(feature_matrix: np.ndarray, feature_names: list[str],
                   threshold: float = 0.5) -> dict[str, list[str]]:
    """
    Group features into clades based on Spearman correlation.

    Args:
        feature_matrix: (n_samples, n_features) array
        feature_names: list of feature names matching columns
        threshold: distance threshold for cutting dendrogram

    Returns:
        Dict mapping clade_name -> list of feature names
    """
    # Compute Spearman correlation matrix
    corr_matrix, _ = spearmanr(feature_matrix)
    if isinstance(corr_matrix, float):
        # Single feature edge case
        return {"clade_0": feature_names}

    # Convert to distance
    distance_matrix = 1 - np.abs(corr_matrix)
    np.fill_diagonal(distance_matrix, 0)

    # Hierarchical clustering
    condensed = squareform(distance_matrix)
    Z = linkage(condensed, method='ward')
    clusters = fcluster(Z, t=threshold, criterion='distance')

    # Group features by cluster
    clades = {}
    for feat_name, cluster_id in zip(feature_names, clusters):
        clade_name = f"clade_{cluster_id}"
        if clade_name not in clades:
            clades[clade_name] = []
        clades[clade_name].append(feat_name)

    return clades
```

#### 3.4 Permutation Importance (importance_weighting.py)

```python
"""
importance_weighting.py -- Weight features using Permutation Importance.

Why not Gini impurity (MDI)?
  MDI is biased toward high-cardinality features. A feature like 'trade_size_usdc'
  with thousands of unique values will appear more important than 'is_fresh_wallet'
  (binary) even if the binary feature is more predictive.

  Permutation Importance randomly shuffles each feature and measures how much
  predictive performance degrades. This is unbiased with respect to cardinality.

Implementation:
  - Use sklearn's permutation_importance function
  - Train a simple RandomForest on the backtest data (labels from backtest.py outcome field)
  - Compute importance for each feature
  - Normalize to [0, 1] and include in the feature payload sent to Mistral

The importance weights serve two purposes:
  1. Inform the Mistral classifier which features matter most
  2. Provide transparency for the XAI narrative
"""

from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
import numpy as np


def compute_importance_weights(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    n_repeats: int = 10,
) -> dict[str, float]:
    """
    Compute permutation importance weights for each feature.

    Args:
        X: (n_samples, n_features) feature matrix
        y: (n_samples,) labels (0=legitimate, 1=suspicious)
        feature_names: list of feature names
        n_repeats: number of permutation repeats

    Returns:
        Dict mapping feature_name -> importance_weight (0-1 normalized)
    """
    clf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    clf.fit(X, y)

    result = permutation_importance(clf, X, y, n_repeats=n_repeats, random_state=42)

    # Normalize to [0, 1]
    importances = result.importances_mean
    max_imp = max(importances) if max(importances) > 0 else 1
    normalized = {name: float(imp / max_imp) for name, imp in zip(feature_names, importances)}

    return normalized
```

#### 3.5 Payload Formatter (payload_formatter.py)

```python
"""
payload_formatter.py -- Format the clustered, weighted features into a JSON payload
for the Mistral classifier prompt.

Output format (this is what gets injected into the Mistral prompt):

{
  "anomaly_id": "uuid",
  "market": {
    "question": "Will X happen by Y?",
    "slug": "will-x-happen-by-y",
    "current_price": 0.35
  },
  "clades": {
    "liquidity": {
      "importance": 0.72,
      "features": {
        "volume_ratio": {"value": 4.2, "weight": 0.85, "description": "4.2x baseline volume"},
        "order_book_impact": {"value": 0.08, "weight": 0.65, "description": "8% of visible book consumed"}
      }
    },
    "volatility": {
      "importance": 0.58,
      "features": {
        "z_score": {"value": 3.1, "weight": 0.92, "description": "3.1 std devs above mean"},
        "price_velocity": {"value": 0.15, "weight": 0.45, "description": "15 cents/hour price movement"}
      }
    },
    "entity_governance": {
      "importance": 0.91,
      "features": {
        "wallet_age_hours": {"value": 2.5, "weight": 0.95, "description": "Wallet created 2.5 hours ago"},
        "is_fresh_wallet": {"value": true, "weight": 0.90, "description": "Fewer than 5 lifetime transactions"},
        "cluster_size": {"value": 3, "weight": 0.80, "description": "Part of 3-wallet cluster"}
      }
    }
  },
  "raw_scores": {
    "composite_risk": 78.5,
    "fresh_wallet_flag": true,
    "size_anomaly_flag": true,
    "sniper_cluster_flag": true
  }
}
"""
```

### Acceptance Criteria

- [ ] Feature extraction produces all listed features from anomaly_events + wallet_profiles
- [ ] Spearman clustering groups features into 3-5 interpretable clades
- [ ] Permutation importance weights are computed and normalized
- [ ] Payload formatter outputs valid JSON matching the schema above
- [ ] Pipeline runs end-to-end: anomaly_event_id in -> JSON feature payload out
- [ ] Dendrogram visualization can be generated for demo purposes

---

## WORKSTREAM 4: Mistral AI Classification Pipeline

**Agent Assignment: "AI/ML Engineer"**
**Estimated Effort: 6-8 hours**
**Dependencies: Workstream 3 (needs feature payload format), Workstream 2 (needs ChromaDB populated)**

### Objective

Build the three-stage AI pipeline: (1) Fine-tuned Mistral Small for fast triage classification, (2) Magistral + RAG for explainable reasoning, (3) Mistral Large for SAR report generation.

### Detailed Implementation

#### 4.1 Project Structure

```
sentinel/
├── workstream_4_ai_pipeline/
│   ├── __init__.py
│   ├── config.py
│   ├── training/
│   │   ├── generate_synthetic.py      # Generate synthetic training examples
│   │   ├── prepare_jsonl.py           # Format backtest + synthetic data into JSONL
│   │   ├── submit_finetune.py         # Upload to Mistral API and start fine-tune job
│   │   └── validate_data.py           # Validate JSONL format before upload
│   ├── stage1_classifier.py           # Fine-tuned Mistral Small triage
│   ├── stage2_xai.py                 # Magistral + RAG explainability
│   ├── stage3_sar.py                 # Mistral Large SAR generation
│   ├── pipeline.py                    # Orchestrates all three stages
│   └── prompts/
│       ├── classifier_system.txt      # System prompt for fine-tuned classifier
│       ├── xai_system.txt             # System prompt for Magistral XAI
│       └── sar_system.txt             # System prompt for SAR generation
```

#### 4.2 Training Data Generation (generate_synthetic.py)

```python
"""
generate_synthetic.py -- Generate ~500 synthetic training examples using Mistral Large.

Strategy (from PRD):
  - Use Mistral Large to generate diverse training examples
  - Mix with REAL historical anomalies from backtest.py (Workstream 1)
  - Target distribution: 40% SPECULATOR, 25% FAST_REACTOR, 20% OSINT_EDGE, 15% INSIDER
    (matches expected real-world class distribution -- heavily imbalanced toward legitimate)

Each training example has:
  - Input: The structured feature payload (from Workstream 3 format)
  - Output: Classification + PES + BSS + brief reasoning

Generation prompt for Mistral Large:
"""

GENERATION_SYSTEM_PROMPT = """You are a financial fraud data generator. Given the following
classification category and constraints, generate a realistic feature payload for a
Polymarket prediction market trade anomaly.

The four categories are:
1. INSIDER: The trader had material non-public information. Characteristics:
   - Fresh wallet (< 24 hours old), very few transactions
   - Large position size relative to market depth
   - Trade placed 1-6 hours before a major news event
   - Often part of a small wallet cluster (2-5 wallets)
   - High win rate on resolved markets
   - Low market concentration (trades in very few markets)

2. OSINT_EDGE: The trader used publicly available information skillfully. Characteristics:
   - Established wallet (weeks-months old), moderate transaction history
   - Moderate position size
   - Trade placed AFTER detectable public signals (flight tracking, satellite imagery, RSS news)
   - Not part of a cluster
   - Moderate win rate

3. FAST_REACTOR: The trader reacted quickly to breaking public news. Characteristics:
   - Established wallet, active trader
   - Trade placed minutes after a news break (not before)
   - High volume but explainable by news catalyst
   - High market activity from many wallets simultaneously

4. SPECULATOR: Normal speculative trading, no edge. Characteristics:
   - Any wallet age
   - Normal position size relative to history
   - No correlation with news timing
   - Random win rate

Generate a complete feature payload matching the category. Include realistic
numerical values. Vary the scenarios across different geopolitical topics
(elections, military conflicts, economic policy, natural disasters, crypto events).
"""
```

#### 4.3 JSONL Preparation (prepare_jsonl.py)

```python
"""
prepare_jsonl.py -- Combine synthetic + real historical data into Mistral fine-tuning JSONL.

JSONL format required by Mistral API:
{"messages": [
  {"role": "system", "content": "<system prompt>"},
  {"role": "user", "content": "<feature payload JSON>"},
  {"role": "assistant", "content": "<classification output JSON>"}
]}

Classification output format:
{
  "classification": "INSIDER",
  "confidence": 0.87,
  "bss_score": 82.5,
  "pes_score": 12.0,
  "reasoning": "Fresh wallet (2.5h old) placed $15,000 on a niche market 3 hours before
                a major policy announcement. DBSCAN detected 3-wallet cluster with similar
                timing. No public signals found in the 6 hours preceding the trade."
}

Steps:
1. Load synthetic examples from generate_synthetic.py output
2. Load real historical anomalies from backtest.py output (Workstream 1)
3. For real data: manually categorize using heuristics based on outcome
   (correct prediction on fresh wallet with timing advantage = likely INSIDER)
4. Merge, shuffle, split 90/10 train/validation
5. Write to train.jsonl and validation.jsonl
"""
```

#### 4.4 Fine-Tuning Job Submission (submit_finetune.py)

```python
"""
submit_finetune.py -- Upload JSONL and start Mistral fine-tuning job.

Uses the Mistral API fine-tuning endpoint.
Model: mistral-small-latest (or open-mistral-7b for budget)

Steps:
1. Upload train.jsonl via client.files.upload()
2. Upload validation.jsonl via client.files.upload()
3. Create fine-tuning job via client.fine_tuning.jobs.create()
4. Poll job status until SUCCEEDED
5. Save the fine-tuned model ID to config
"""

from mistralai import Mistral
import os
import time
import json


def submit_finetune_job(train_path: str, val_path: str):
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    # Upload files
    with open(train_path, "rb") as f:
        train_file = client.files.upload(
            file={"file_name": "sentinel_train.jsonl", "content": f}
        )
    with open(val_path, "rb") as f:
        val_file = client.files.upload(
            file={"file_name": "sentinel_val.jsonl", "content": f}
        )

    # Create fine-tuning job
    job = client.fine_tuning.jobs.create(
        model="open-mistral-7b",  # or "mistral-small-latest"
        training_files=[{"file_id": train_file.id, "weight": 1}],
        validation_files=[val_file.id],
        hyperparameters={
            "training_steps": 100,  # Adjust based on dataset size
            "learning_rate": 0.0001,
        },
        auto_start=True,
    )

    print(f"Fine-tuning job created: {job.id}")

    # Poll until complete
    while True:
        status = client.fine_tuning.jobs.get(job_id=job.id)
        print(f"Status: {status.status}")
        if status.status in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            break
        time.sleep(30)

    if status.status == "SUCCEEDED":
        print(f"Fine-tuned model: {status.fine_tuned_model}")
        # Save model ID
        with open("config/fine_tuned_model.json", "w") as f:
            json.dump({"model_id": status.fine_tuned_model}, f)
    else:
        print(f"Job failed: {status}")
```

#### 4.5 Stage 1: Fast Triage Classifier (stage1_classifier.py)

```python
"""
stage1_classifier.py -- Fine-tuned Mistral Small for 4-class classification.

Input: Feature payload JSON (from Workstream 3)
Output: Classification, BSS, PES, confidence, reasoning

If fine-tuned model is not yet available (job still running), fall back to
base Mistral Small with a detailed few-shot prompt.
"""

CLASSIFIER_SYSTEM_PROMPT = """You are Sentinel, a financial anomaly classifier for
prediction markets. You analyze structured feature data from Polymarket trade anomalies
and classify them into exactly one of four categories:

1. INSIDER - Material non-public information. High BSS (70-100), Low PES (0-30).
2. OSINT_EDGE - Skillful use of public intelligence. Moderate BSS (30-60), High PES (60-90).
3. FAST_REACTOR - Quick reaction to breaking news. Low BSS (10-40), High PES (70-100).
4. SPECULATOR - Normal speculation, no information edge. Low BSS (0-20), Moderate PES (40-70).

Respond ONLY with valid JSON matching this schema:
{
  "classification": "INSIDER|OSINT_EDGE|FAST_REACTOR|SPECULATOR",
  "confidence": 0.0-1.0,
  "bss_score": 0-100,
  "pes_score": 0-100,
  "reasoning": "2-3 sentence explanation of key factors"
}

Key decision factors:
- wallet_age_hours < 24 AND high trade_size_ratio -> likely INSIDER
- OSINT signals found before trade -> likely OSINT_EDGE or FAST_REACTOR
- Distinguish OSINT_EDGE (hours before news) from FAST_REACTOR (minutes after news)
- No timing correlation with events -> likely SPECULATOR
- cluster_size > 1 increases INSIDER probability significantly
"""


class SentinelClassifier:
    def __init__(self, model_id: str = None):
        self.client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
        # Use fine-tuned model if available, otherwise base model
        self.model = model_id or "mistral-small-latest"

    def classify(self, feature_payload: dict) -> dict:
        response = self.client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(feature_payload)},
            ],
            temperature=0.1,  # Low temp for consistent classification
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
```

#### 4.6 Stage 2: Magistral XAI Layer (stage2_xai.py)

```python
"""
stage2_xai.py -- Magistral reasoning model + ChromaDB RAG for explainable analysis.

Triggered when Stage 1 returns BSS > 50 (configurable threshold).

Steps:
1. Take the anomaly_event and Stage 1 classification
2. Query ChromaDB for OSINT events published BEFORE the trade timestamp
3. Query ChromaDB for OSINT events published AFTER the trade but BEFORE news break
4. Feed everything to Magistral with a reasoning prompt
5. Magistral produces:
   - XAI narrative (human-readable explanation)
   - Temporal gap analysis (minutes between trade and nearest public signal)
   - Fraud Triangle mapping
6. Update the anomaly_event record with XAI fields
"""

XAI_SYSTEM_PROMPT = """You are the Explainable AI layer of Sentinel, a prediction market
surveillance system. Your task is to produce a transparent, human-readable analysis of
a flagged trading anomaly.

You will receive:
1. The anomaly details and initial classification
2. OSINT events that were publicly available BEFORE the trade
3. OSINT events that appeared AFTER the trade

Your analysis must address:

A. TEMPORAL GAP ANALYSIS
   - What is the time gap between the trade and the EARLIEST public signal that could
     explain it?
   - If public signals existed BEFORE the trade: the trader may have used OSINT (OSINT_EDGE)
   - If NO public signals existed before: potential insider information

B. FRAUD TRIANGLE MAPPING (required for all INSIDER classifications)
   - OPPORTUNITY: What access or mechanism could the trader have used?
     (e.g., wallet interacted with a specific smart contract, wallet cluster suggests
     organizational access)
   - PRESSURE: Is there evidence of financial pressure?
     (e.g., wallet was recently drained, rapid fund movement from CEX)
   - RATIONALIZATION: What narrative might the trader construct?
     (e.g., "I just follow OSINT" but no OSINT trail exists)

C. CONFIDENCE ASSESSMENT
   - How confident are you in the classification?
   - What alternative explanations exist?
   - What additional data would strengthen or weaken the case?

Respond in structured markdown with clear section headers.
Be specific about timestamps, amounts, and sources.
"""


class MagistralXAI:
    def __init__(self, vector_store):
        self.client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
        self.vs = vector_store  # ChromaDB instance from Workstream 2

    def analyze(self, anomaly: dict, classification: dict) -> dict:
        # Query OSINT events before the trade
        trade_time = anomaly["detected_at"]
        market_question = anomaly["market_question"]

        pre_trade_signals = self.vs.query_by_timestamp_and_topic(
            query_text=market_question,
            before_timestamp=trade_time,
            n_results=10,
        )

        # Build context for Magistral
        context = self._build_context(anomaly, classification, pre_trade_signals)

        response = self.client.chat.complete(
            model="magistral-medium-latest",
            messages=[
                {"role": "system", "content": XAI_SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            temperature=0.7,
            max_tokens=4000,
        )

        # Parse the structured response
        narrative = response.choices[0].message.content

        # Extract thinking traces if available
        thinking = ""
        for block in response.choices[0].message.content:
            if hasattr(block, 'type') and block.type == 'thinking':
                thinking = block.thinking[0].text if block.thinking else ""

        return {
            "xai_narrative": narrative,
            "thinking_trace": thinking,
            "osint_signals_found": self._format_signals(pre_trade_signals),
            "temporal_gap_minutes": self._compute_temporal_gap(anomaly, pre_trade_signals),
        }

    def _build_context(self, anomaly, classification, signals) -> str:
        return f"""
ANOMALY DETAILS:
- Market: {anomaly['market_question']}
- Trade Time: {anomaly['detected_at']}
- Wallet: {anomaly.get('wallet_address', 'N/A')}
- Trade Size: ${anomaly.get('trade_size_usdc', 'N/A')} USDC
- Wallet Age: {anomaly.get('wallet_age_hours', 'N/A')} hours
- Volume Z-Score: {anomaly.get('z_score', 'N/A')}

STAGE 1 CLASSIFICATION:
- Class: {classification['classification']}
- BSS: {classification['bss_score']}
- PES: {classification['pes_score']}
- Initial Reasoning: {classification['reasoning']}

PUBLIC SIGNALS AVAILABLE BEFORE TRADE:
{self._format_signals(signals)}

Produce your full XAI analysis.
"""

    def _compute_temporal_gap(self, anomaly, signals) -> float:
        """Compute minutes between trade and nearest prior public signal."""
        # Implementation: parse timestamps, find minimum gap
        return 0.0  # Placeholder

    def _format_signals(self, signals) -> str:
        if not signals or not signals.get("documents"):
            return "NO PUBLIC SIGNALS FOUND BEFORE TRADE"
        formatted = []
        for doc, meta in zip(signals["documents"][0], signals["metadatas"][0]):
            formatted.append(f"- [{meta.get('published_at', '?')}] [{meta.get('source_name', '?')}] {doc[:200]}")
        return "\n".join(formatted)
```

#### 4.7 Stage 3: SAR Report Generation (stage3_sar.py)

```python
"""
stage3_sar.py -- Mistral Large generates structured Suspicious Activity Report (SAR).

Input: Complete anomaly_event with XAI narrative
Output: Structured JSON SAR

This is the final output artifact. The SAR format is designed to be:
1. Machine-readable (JSON) for database storage and API consumption
2. Human-readable when rendered in the dashboard
3. Comprehensive enough for a hypothetical regulatory submission
"""

SAR_SYSTEM_PROMPT = """You are a financial compliance report generator. Produce a structured
Suspicious Activity Report (SAR) in JSON format for the given prediction market anomaly.

The SAR must include ALL of the following fields:

{
  "sar_id": "auto-generated UUID",
  "generated_at": "ISO 8601 timestamp",
  "classification": "INSIDER|OSINT_EDGE|FAST_REACTOR|SPECULATOR",
  "severity": "critical|high|medium|low",
  "summary": "One-paragraph executive summary",

  "subject": {
    "wallet_address": "0x...",
    "wallet_age": "human-readable duration",
    "associated_wallets": ["0x...", "0x..."],
    "funding_source": "description of fund origins"
  },

  "activity": {
    "market": "market question text",
    "trade_timestamp": "ISO 8601",
    "trade_direction": "BUY YES|BUY NO|SELL YES|SELL NO",
    "trade_size_usdc": 0.0,
    "price_at_entry": 0.0,
    "current_price": 0.0,
    "unrealized_pnl": 0.0
  },

  "temporal_analysis": {
    "trade_timestamp": "ISO 8601",
    "earliest_public_signal": "ISO 8601 or null",
    "news_break_timestamp": "ISO 8601 or null",
    "gap_trade_to_signal_minutes": 0,
    "gap_trade_to_news_minutes": 0,
    "timeline": [
      {"timestamp": "...", "event": "description", "source": "..."}
    ]
  },

  "fraud_triangle": {
    "opportunity": "description",
    "pressure": "description",
    "rationalization": "description"
  },

  "evidence": {
    "behavioral_suspicion_score": 0-100,
    "public_explainability_score": 0-100,
    "signals_triggered": ["FRESH_WALLET", "SIZE_ANOMALY", "SNIPER_CLUSTER"],
    "osint_correlation": "description of matching/non-matching public signals"
  },

  "recommendation": "ESCALATE|MONITOR|ARCHIVE",
  "confidence": 0.0-1.0,
  "xai_narrative": "full explanation from Magistral"
}

Respond ONLY with valid JSON. No markdown, no explanation outside the JSON.
"""


class SARGenerator:
    def __init__(self):
        self.client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    def generate(self, anomaly: dict, classification: dict, xai: dict) -> dict:
        context = json.dumps({
            "anomaly": anomaly,
            "classification": classification,
            "xai_analysis": xai,
        }, indent=2)

        response = self.client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {"role": "system", "content": SAR_SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)
```

#### 4.8 Pipeline Orchestrator (pipeline.py)

```python
"""
pipeline.py -- Orchestrates all three AI stages.

Flow:
1. Read unprocessed anomaly_events from SQLite (status = 'pending')
2. For each: run feature payload through Stage 1 classifier
3. If BSS > 50: run through Stage 2 Magistral XAI
4. For all INSIDER or high-BSS results: run through Stage 3 SAR generator
5. Update anomaly_event record with all AI outputs
6. Insert into sentinel_index if classification is INSIDER or OSINT_EDGE
"""


class SentinelPipeline:
    def __init__(self, db, vector_store, classifier, xai_engine, sar_generator):
        self.db = db
        self.classifier = classifier
        self.xai = xai_engine
        self.sar = sar_generator
        self.bss_threshold = 50.0

    def process_anomaly(self, anomaly_id: str):
        """Full pipeline for a single anomaly."""
        # 1. Load anomaly and build feature payload
        anomaly = self._load_anomaly(anomaly_id)
        payload = self._build_feature_payload(anomaly)

        # 2. Stage 1: Fast classification
        classification = self.classifier.classify(payload)
        self._update_anomaly(anomaly_id, {
            "classification": classification["classification"],
            "confidence": classification["confidence"],
            "bss_score": classification["bss_score"],
            "pes_score": classification["pes_score"],
            "status": "classified",
        })

        # 3. Stage 2: XAI (if BSS > threshold)
        if classification["bss_score"] > self.bss_threshold:
            xai_result = self.xai.analyze(anomaly, classification)
            self._update_anomaly(anomaly_id, {
                "xai_narrative": xai_result["xai_narrative"],
                "temporal_gap_minutes": xai_result["temporal_gap_minutes"],
                "osint_signals_found": json.dumps(xai_result["osint_signals_found"]),
            })

            # 4. Stage 3: SAR (for INSIDER or high BSS)
            if classification["classification"] == "INSIDER" or classification["bss_score"] > 75:
                sar = self.sar.generate(anomaly, classification, xai_result)
                self._update_anomaly(anomaly_id, {
                    "sar_json": json.dumps(sar),
                    "fraud_triangle_json": json.dumps(sar.get("fraud_triangle", {})),
                    "status": "reviewed",
                })

                # 5. Add to Sentinel Index
                self._add_to_index(anomaly_id, classification, sar)

    def run_batch(self):
        """Process all pending anomalies."""
        pending = self._get_pending_anomalies()
        for anomaly_id in pending:
            try:
                self.process_anomaly(anomaly_id)
            except Exception as e:
                print(f"Pipeline error for {anomaly_id}: {e}")
                self._update_anomaly(anomaly_id, {"status": "error"})
```

### Acceptance Criteria

- [ ] Synthetic data generator produces 500+ diverse training examples across all 4 classes
- [ ] JSONL files validate against Mistral's format requirements
- [ ] Fine-tuning job submits successfully (or fallback prompt-based classifier works)
- [ ] Stage 1 classifier returns valid JSON with all required fields
- [ ] Stage 2 Magistral XAI queries ChromaDB and produces narrative with temporal analysis
- [ ] Stage 3 SAR generator outputs complete, valid SAR JSON
- [ ] Full pipeline processes an anomaly end-to-end in under 30 seconds
- [ ] Sentinel Index is populated with classified cases

---

## WORKSTREAM 5: Dashboard & Frontend

**Agent Assignment: "Frontend Engineer"**
**Estimated Effort: 5-7 hours**
**Dependencies: Workstreams 1-4 (needs data to display, but can scaffold with mock data)**

### Objective

Build a React dashboard (or Streamlit for speed) that visualizes the Sentinel system's outputs: temporal gap analysis, XAI narratives, the human-consensus Arena, and the Sentinel Index browser.

### Technology Choice

For hackathon speed: **Streamlit** (Python, fastest path to a working demo).
For production quality: **React + Tailwind + shadcn/ui**.

The guide below covers Streamlit for the hackathon, with React component specs for future migration.

### Detailed Implementation

#### 5.1 Project Structure (Streamlit)

```
sentinel/
├── workstream_5_dashboard/
│   ├── app.py                         # Main Streamlit app
│   ├── pages/
│   │   ├── 1_Live_Monitor.py          # Real-time anomaly feed
│   │   ├── 2_Case_Detail.py           # Deep dive on a single anomaly
│   │   ├── 3_Sentinel_Index.py        # Browse all classified cases
│   │   ├── 4_Arena.py                 # Human consensus voting
│   │   └── 5_System_Health.py         # Data source status, pipeline health
│   ├── components/
│   │   ├── temporal_gap_chart.py      # Timeline visualization
│   │   ├── fraud_triangle.py          # Fraud triangle diagram
│   │   ├── feature_radar.py           # Radar chart of feature clades
│   │   └── sar_viewer.py              # SAR report renderer
│   └── utils/
│       ├── db.py                      # SQLite query helpers
│       └── mock_data.py               # Mock data for development
```

#### 5.2 Page Specifications

**Page 1: Live Monitor**
- Real-time feed of detected anomalies (auto-refresh every 30s)
- Columns: Time, Market, Anomaly Type, BSS Score, Classification, Status
- Color coding: INSIDER (red), OSINT_EDGE (yellow), FAST_REACTOR (blue), SPECULATOR (gray)
- Click-through to Case Detail
- Filter by: classification, date range, BSS threshold, anomaly type

**Page 2: Case Detail**
- Top: Market info (question, current price, volume chart)
- Middle-left: Feature radar chart showing clade importance
- Middle-right: Temporal gap timeline
  - Horizontal timeline showing: trade timestamp, OSINT signals, news break
  - Visual gap measurement in minutes
- Bottom-left: Fraud Triangle visualization (three interconnected nodes)
- Bottom-right: Full XAI narrative (Magistral output)
- Collapsible: Full SAR JSON viewer
- Action buttons: "Escalate", "Archive", "Vote in Arena"

**Page 3: Sentinel Index**
- Searchable, sortable table of all classified cases
- Export to CSV
- Aggregate statistics: total cases, classification distribution, average confidence
- Charts: classification distribution pie chart, BSS histogram, temporal gap distribution

**Page 4: Arena (Human Consensus)**
- Display one case at a time with anonymized details
- Show: feature payload, XAI narrative, classification
- Voting buttons: "Agree (INSIDER)", "Disagree (LEGITIMATE)", "Unsure"
- After voting, reveal consensus score and other votes
- Leaderboard of most-voted cases

**Page 5: System Health**
- Data source status grid (adapted from worldmonitor's data freshness tracker)
- For each source: last update time, status (fresh/stale/error), event count
- Pipeline health: pending anomalies, average processing time, error rate

#### 5.3 Key Visualization: Temporal Gap Chart

```python
"""
temporal_gap_chart.py -- The core visual for demonstrating Sentinel's value.

This is the single most important visualization for the demo.
It shows a horizontal timeline with:
  1. Trade timestamp (red marker)
  2. OSINT signals (green markers, labeled with source)
  3. News break (orange marker)
  4. The GAP between trade and earliest public signal (highlighted zone)

If the gap is NEGATIVE (trade came BEFORE any public signal):
  -> Red zone, labeled "NO PUBLIC PRECEDENT"
  -> Strongly suggests insider information

If the gap is POSITIVE (public signal came first):
  -> Green zone, labeled "PUBLIC SIGNAL AVAILABLE"
  -> Suggests OSINT_EDGE or FAST_REACTOR

Use plotly for interactive timeline.
"""

import plotly.graph_objects as go
from datetime import datetime


def render_temporal_gap(anomaly: dict, osint_signals: list):
    """Render a temporal gap timeline for a single anomaly."""

    fig = go.Figure()

    trade_time = datetime.fromisoformat(anomaly["detected_at"])

    # Trade marker
    fig.add_trace(go.Scatter(
        x=[trade_time],
        y=[1],
        mode='markers+text',
        marker=dict(size=20, color='red', symbol='diamond'),
        text=['TRADE'],
        textposition='top center',
        name='Suspicious Trade',
    ))

    # OSINT signal markers
    for i, signal in enumerate(osint_signals):
        signal_time = datetime.fromisoformat(signal["published_at"])
        fig.add_trace(go.Scatter(
            x=[signal_time],
            y=[1],
            mode='markers+text',
            marker=dict(size=12, color='green', symbol='circle'),
            text=[signal.get("source_name", "OSINT")],
            textposition='bottom center',
            name=f'Signal: {signal.get("source_name", "?")}',
        ))

    fig.update_layout(
        title="Temporal Gap Analysis",
        xaxis_title="Time",
        showlegend=True,
        height=300,
    )

    return fig
```

### Acceptance Criteria

- [ ] Dashboard loads and displays mock data on all 5 pages
- [ ] Live Monitor auto-refreshes and displays anomalies from SQLite
- [ ] Case Detail page renders temporal gap chart, fraud triangle, and XAI narrative
- [ ] Sentinel Index is searchable and sortable
- [ ] Arena voting UI works (vote updates consensus_score in DB)
- [ ] System Health page shows status of all data sources
- [ ] Dashboard runs locally via `streamlit run app.py`

---

## WORKSTREAM 6: Integration, Database, & API Layer

**Agent Assignment: "Backend/Integration Engineer"**
**Estimated Effort: 3-4 hours**
**Dependencies: All other workstreams (this is the glue)**

### Objective

Wire all workstreams together: shared SQLite database initialization, inter-workstream communication, API endpoints for the dashboard, and the main application entry point.

### Detailed Implementation

#### 6.1 Project Structure

```
sentinel/
├── workstream_6_integration/
│   ├── __init__.py
│   ├── database.py                    # SQLite schema init, migration, shared connection
│   ├── api.py                         # FastAPI server for dashboard backend
│   ├── orchestrator.py                # Main event loop connecting all workstreams
│   ├── evaluator.py                   # FPR/FNR metrics computation
│   └── export.py                      # Export Sentinel Index to various formats
├── data/
│   ├── sentinel.db                    # SQLite database (auto-created)
│   └── chromadb/                      # ChromaDB persistence (auto-created)
├── config/
│   ├── .env                           # Environment variables
│   └── fine_tuned_model.json          # Model ID from fine-tuning
├── requirements.txt
├── docker-compose.yml
├── Makefile                           # Common commands
└── README.md
```

#### 6.2 Database Manager (database.py)

```python
"""
database.py -- Shared SQLite database initialization and connection management.

All tables from the Shared Data Contracts section are created here.
This is the first thing that runs when the system starts.
"""

import sqlite3
import os

DB_PATH = os.environ.get("SENTINEL_DB_PATH", "./data/sentinel.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # All CREATE TABLE statements from Shared Data Contracts
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS anomaly_events ( ... );
        CREATE TABLE IF NOT EXISTS osint_events ( ... );
        CREATE TABLE IF NOT EXISTS wallet_profiles ( ... );
        CREATE TABLE IF NOT EXISTS sentinel_index ( ... );
        CREATE TABLE IF NOT EXISTS volume_baselines (
            market_id TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0,
            mean REAL DEFAULT 0.0,
            m2 REAL DEFAULT 0.0,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS arena_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anomaly_event_id TEXT REFERENCES anomaly_events(id),
            vote TEXT NOT NULL,  -- 'insider' | 'legitimate' | 'unsure'
            voter_session TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Indexes for common queries
        CREATE INDEX IF NOT EXISTS idx_anomaly_status ON anomaly_events(status);
        CREATE INDEX IF NOT EXISTS idx_anomaly_detected ON anomaly_events(detected_at);
        CREATE INDEX IF NOT EXISTS idx_anomaly_classification ON anomaly_events(classification);
        CREATE INDEX IF NOT EXISTS idx_osint_published ON osint_events(published_at);
        CREATE INDEX IF NOT EXISTS idx_osint_source ON osint_events(source);
    """)

    conn.commit()
    conn.close()
```

#### 6.3 Main Orchestrator (orchestrator.py)

```python
"""
orchestrator.py -- Main event loop that connects all workstreams.

Architecture:
  - Uses asyncio for concurrent execution of ingestion loops
  - Polymarket polling (every 60s)
  - OSINT polling (every 5 min for RSS, 15 min for GDELT, 30 min for ACLED)
  - AI pipeline processing (triggered when new anomalies appear)
  - Dashboard API server (runs on separate thread)

Start with: python -m sentinel.orchestrator
"""

import asyncio
import threading
from workstream_1_ingestion.main import run_market_monitor
from workstream_2_osint.main import run_osint_monitor
from workstream_4_ai_pipeline.pipeline import SentinelPipeline
from workstream_6_integration.database import init_database, get_connection
from workstream_6_integration.api import start_api_server


async def main():
    # Initialize
    init_database()
    db = get_connection()

    # Start components
    tasks = [
        asyncio.create_task(run_market_monitor(db)),     # Workstream 1
        asyncio.create_task(run_osint_monitor(db)),       # Workstream 2
        asyncio.create_task(run_ai_pipeline(db)),         # Workstream 4
    ]

    # Start API server in separate thread
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    await asyncio.gather(*tasks)


async def run_ai_pipeline(db):
    """Continuously process pending anomalies through the AI pipeline."""
    pipeline = SentinelPipeline(...)  # Initialize with all components

    while True:
        pipeline.run_batch()
        await asyncio.sleep(10)  # Check for new anomalies every 10 seconds


if __name__ == "__main__":
    asyncio.run(main())
```

#### 6.4 Evaluation Metrics (evaluator.py)

```python
"""
evaluator.py -- Compute FPR and FNR metrics for the classification pipeline.

From the PRD:
  - Optimize for False Positive Rate (FPR): minimize lawful transactions flagged as unlawful
  - Optimize for False Negative Rate (FNR): ensure true anomalies aren't missed

Implementation:
  Uses resolved market outcomes + arena consensus as ground truth.
  If a case was classified as INSIDER but the market resolved against the trader,
  OR the arena consensus is strongly "legitimate", it's a false positive.

  If a case was classified as SPECULATOR but the wallet had a pattern of correctly
  timed trades that later resolved profitably, it's a false negative.
"""

def compute_metrics(db) -> dict:
    """Compute FPR and FNR from the Sentinel Index."""
    # Query all cases with known outcomes
    cases = db.execute("""
        SELECT classification, consensus_score, market_outcome, outcome_verified
        FROM sentinel_index WHERE outcome_verified = 1
    """).fetchall()

    # Compute confusion matrix
    tp = fp = tn = fn = 0
    for case in cases:
        predicted_suspicious = case["classification"] in ("INSIDER", "OSINT_EDGE")
        actually_suspicious = case["consensus_score"] > 0.3  # Arena says suspicious

        if predicted_suspicious and actually_suspicious:
            tp += 1
        elif predicted_suspicious and not actually_suspicious:
            fp += 1
        elif not predicted_suspicious and actually_suspicious:
            fn += 1
        else:
            tn += 1

    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0

    return {
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "fpr": fpr,
        "fnr": fnr,
        "precision": tp / (tp + fp) if (tp + fp) > 0 else 0,
        "recall": tp / (tp + fn) if (tp + fn) > 0 else 0,
    }
```

#### 6.5 FastAPI Backend (api.py)

```python
"""
api.py -- FastAPI server providing REST endpoints for the dashboard.

Endpoints:
  GET  /api/anomalies              List anomalies (with filters)
  GET  /api/anomalies/{id}         Get single anomaly with full details
  GET  /api/index                  List Sentinel Index cases
  GET  /api/metrics                Get FPR/FNR and system metrics
  GET  /api/health                 Data source health status
  POST /api/arena/vote             Submit arena vote
  GET  /api/arena/case             Get next case for voting
"""
```

### Acceptance Criteria

- [ ] Database initializes with all tables on first run
- [ ] Orchestrator starts all workstreams concurrently
- [ ] API endpoints return valid data from SQLite
- [ ] Arena voting endpoint updates consensus scores
- [ ] Evaluation metrics compute correctly from test data
- [ ] System runs end-to-end: ingest -> detect -> classify -> display

---

## Implementation Order & Critical Path

```
HOUR 0-2:   Workstream 1 (Data Ingestion) + Workstream 2 (OSINT)
            Run in parallel. No dependencies.
            Goal: Data flowing into SQLite + ChromaDB.

HOUR 2-4:   Workstream 3 (Feature Engineering)
            Needs sample data from WS1.
            Goal: Feature payloads generating from anomaly records.

HOUR 2-4:   Workstream 4 - Training Data (can start with synthetic only)
            Generate synthetic JSONL, submit fine-tuning job.
            Fine-tuning takes 30-60 min to complete.

HOUR 4-6:   Workstream 4 - AI Pipeline (classification + XAI + SAR)
            Needs: feature payloads (WS3), ChromaDB data (WS2)
            Use base model while fine-tune job runs.
            Goal: End-to-end classification producing SAR JSON.

HOUR 4-8:   Workstream 5 (Dashboard)
            Start with mock data immediately.
            Switch to live data once WS4 pipeline is producing output.
            Goal: All 5 pages functional.

HOUR 6-8:   Workstream 6 (Integration)
            Wire everything together.
            Goal: Single `make run` command starts the full system.

HOUR 8-10:  Polish & Demo Prep
            - Seed with compelling real cases from backtest
            - Ensure temporal gap visualization is dramatic
            - Verify end-to-end flow for live demo
```

---

## Quick Reference: External Dependencies

| Dependency | Install | Version | Used By |
|------------|---------|---------|---------|
| Python | -- | 3.11+ | All |
| mistralai | `pip install mistralai` | latest | WS4 |
| chromadb | `pip install chromadb` | latest | WS2, WS4 |
| feedparser | `pip install feedparser` | latest | WS2 |
| scipy | `pip install scipy` | latest | WS1, WS3 |
| scikit-learn | `pip install scikit-learn` | latest | WS3 |
| numpy | `pip install numpy` | latest | WS3 |
| pandas | `pip install pandas` | latest | WS1, WS3 |
| plotly | `pip install plotly` | latest | WS5 |
| streamlit | `pip install streamlit` | latest | WS5 |
| fastapi | `pip install fastapi[standard]` | latest | WS6 |
| uvicorn | `pip install uvicorn` | latest | WS6 |
| web3 | `pip install web3` | latest | WS1 (wallet profiling) |
| requests | `pip install requests` | latest | All |

### Full requirements.txt

```
mistralai>=1.0.0
chromadb>=0.4.0
feedparser>=6.0.0
scipy>=1.11.0
scikit-learn>=1.3.0
numpy>=1.24.0
pandas>=2.0.0
plotly>=5.15.0
streamlit>=1.30.0
fastapi[standard]>=0.100.0
uvicorn>=0.23.0
web3>=6.0.0
requests>=2.31.0
python-dotenv>=1.0.0
```
