# SENTINEL: Agent-Ingestible Implementation Plan

## How to Use This Document

This document is structured for consumption by coding agents (Claude Code, Cursor, Copilot Workspace, etc.). Each task is a self-contained unit with explicit inputs, outputs, commands, file paths, and done-criteria. Agents should execute tasks in the order specified within each phase. Tasks within the same phase that are marked `[PARALLEL]` can be run simultaneously by separate agents.

**Conventions:**
- `AGENT:` = which role/agent should own this task
- `DEPENDS_ON:` = task IDs that must complete first
- `INPUTS:` = files, data, or artifacts this task reads
- `OUTPUTS:` = files, data, or artifacts this task produces
- `DONE_WHEN:` = concrete, testable acceptance criteria
- `RISK:` = what can go wrong and the fallback
- `ESTIMATED_TIME:` = wall-clock estimate including debugging

---

## Architecture Summary (Context for All Agents)

Sentinel is an autonomous monitoring system that detects information asymmetry in prediction markets (Polymarket). It distinguishes insider trading from legitimate OSINT research via a multi-stage pipeline:

```
Polymarket Trades --> Anomaly Detection --> Feature Engineering --> AI Classification --> Dashboard
       |                                                                |
       +---- Wallet Profiling                                          |
                                                                       |
OSINT Feeds -----> ChromaDB Vector Store -----> RAG for XAI Layer -----+
```

**Core data flow:** Raw trades become `anomaly_events` (SQLite) --> feature payloads (JSON) --> Mistral classification --> XAI narrative + SAR report --> Dashboard display.

**Shared database:** All components read/write a single SQLite database at `./data/sentinel.db` using WAL mode for concurrent access.

**Tech stack:** Python 3.11+, SQLite (WAL mode), ChromaDB, Mistral AI API (Small, Magistral, Large), Streamlit, FastAPI, scipy/sklearn for statistics.

---

## PHASE 0: Foundation

> **Goal:** Establish shared infrastructure so all parallel workstreams have a stable contract to code against.
> **Total time:** 1-2 hours
> **Who:** One agent (Integration Engineer) sets this up before anyone else starts.

---

### TASK 0.1: Repository Scaffold

```
AGENT: Integration Engineer
DEPENDS_ON: None
ESTIMATED_TIME: 15 minutes
```

**Action:** Create the full directory structure and placeholder files.

```bash
mkdir -p sentinel/{workstream_1_ingestion/detectors,workstream_2_osint/{sources,processors},workstream_3_features,workstream_4_ai_pipeline/{training,prompts},workstream_5_dashboard/{pages,components,utils},workstream_6_integration,data,config}

# Create all __init__.py files
find sentinel -type d -exec touch {}/__init__.py \;

# Create placeholder .env
touch sentinel/config/.env
```

**OUTPUTS:**
```
sentinel/
├── workstream_1_ingestion/
│   ├── __init__.py
│   ├── detectors/
│   │   └── __init__.py
├── workstream_2_osint/
│   ├── __init__.py
│   ├── sources/
│   │   └── __init__.py
│   ├── processors/
│   │   └── __init__.py
├── workstream_3_features/
│   └── __init__.py
├── workstream_4_ai_pipeline/
│   ├── __init__.py
│   ├── training/
│   │   └── __init__.py
│   ├── prompts/
├── workstream_5_dashboard/
│   ├── __init__.py
│   ├── pages/
│   ├── components/
│   ├── utils/
├── workstream_6_integration/
│   └── __init__.py
├── data/
├── config/
│   └── .env
├── requirements.txt
├── Makefile
└── README.md
```

**DONE_WHEN:**
- [ ] All directories exist
- [ ] `__init__.py` in every Python package directory
- [ ] Repo is committed to version control

---

### TASK 0.2: Requirements and Environment

```
AGENT: Integration Engineer
DEPENDS_ON: TASK 0.1
ESTIMATED_TIME: 10 minutes
```

**Action:** Create `requirements.txt` and install all dependencies.

**File: `sentinel/requirements.txt`**
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

```bash
cd sentinel
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**File: `sentinel/config/.env`**
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

# OSINT
GROQ_API_KEY=gsk_xxx
OPENSKY_USERNAME=xxx
OPENSKY_PASSWORD=xxx
VESSELFINDER_API_KEY=xxx
NASA_FIRMS_API_KEY=xxx

# Database
SENTINEL_DB_PATH=./data/sentinel.db

# Optional
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

**DONE_WHEN:**
- [ ] `pip install -r requirements.txt` completes without errors
- [ ] `python -c "import mistralai, chromadb, feedparser, scipy, sklearn, numpy, pandas, plotly, streamlit, fastapi, web3"` succeeds

---

### TASK 0.3: Verify All API Keys

```
AGENT: Integration Engineer
DEPENDS_ON: TASK 0.2
ESTIMATED_TIME: 30 minutes
RISK: Missing API keys will block entire workstreams. If a key is unavailable, note it and descope that data source from MVP.
```

**Action:** Test each external API with a minimal request. Record results.

**Test script: `sentinel/scripts/verify_keys.py`**
```python
"""
Run: python -m scripts.verify_keys
Tests each API dependency and prints pass/fail.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv("config/.env")

results = {}

# 1. Polymarket CLOB API (no auth required)
try:
    r = requests.get("https://clob.polymarket.com/markets", params={"limit": 1}, timeout=10)
    results["Polymarket CLOB"] = "PASS" if r.status_code == 200 else f"FAIL ({r.status_code})"
except Exception as e:
    results["Polymarket CLOB"] = f"FAIL ({e})"

# 2. Polymarket Gamma API (no auth required)
try:
    r = requests.get("https://gamma-api.polymarket.com/markets", params={"limit": 1}, timeout=10)
    results["Polymarket Gamma"] = "PASS" if r.status_code == 200 else f"FAIL ({r.status_code})"
except Exception as e:
    results["Polymarket Gamma"] = f"FAIL ({e})"

# 3. Mistral API
try:
    from mistralai import Mistral
    client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY", ""))
    resp = client.chat.complete(model="mistral-small-latest", messages=[{"role": "user", "content": "ping"}], max_tokens=5)
    results["Mistral API"] = "PASS"
except Exception as e:
    results["Mistral API"] = f"FAIL ({e})"

# 4. Polygon RPC (Alchemy)
try:
    rpc_url = os.environ.get("POLYGON_RPC_URL", "")
    if "YOUR_KEY" in rpc_url or not rpc_url:
        results["Polygon RPC"] = "SKIP (no key configured)"
    else:
        r = requests.post(rpc_url, json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}, timeout=10)
        results["Polygon RPC"] = "PASS" if r.status_code == 200 else f"FAIL ({r.status_code})"
except Exception as e:
    results["Polygon RPC"] = f"FAIL ({e})"

# 5. GDELT (public, no auth)
try:
    r = requests.get("http://data.gdeltproject.org/gdeltv2/lastupdate.txt", timeout=10)
    results["GDELT"] = "PASS" if r.status_code == 200 else f"FAIL ({r.status_code})"
except Exception as e:
    results["GDELT"] = f"FAIL ({e})"

# 6. RSS feed test
try:
    import feedparser
    feed = feedparser.parse("http://feeds.bbci.co.uk/news/world/rss.xml")
    results["RSS (BBC)"] = "PASS" if len(feed.entries) > 0 else "FAIL (no entries)"
except Exception as e:
    results["RSS"] = f"FAIL ({e})"

print("\n=== API KEY VERIFICATION ===")
for name, status in results.items():
    icon = "✓" if status == "PASS" else "✗" if "FAIL" in status else "⊘"
    print(f"  {icon} {name}: {status}")

# Determine what to descope
fails = [k for k, v in results.items() if "FAIL" in v]
if fails:
    print(f"\n⚠ BLOCKING FAILURES: {fails}")
    print("  Action: Fix these keys or descope the affected data sources.")
else:
    print("\n✓ All APIs verified. Proceed to Phase 1.")
```

**DONE_WHEN:**
- [ ] Script runs and prints status for all 6+ APIs
- [ ] Polymarket CLOB = PASS (critical, blocks WS1)
- [ ] Mistral API = PASS (critical, blocks WS4)
- [ ] At least one RSS feed = PASS (critical, blocks WS2)
- [ ] Any FAILs are documented with descoping decisions

---

### TASK 0.4: Shared Database Schema

```
AGENT: Integration Engineer
DEPENDS_ON: TASK 0.1
ESTIMATED_TIME: 30 minutes
```

**Action:** Create the database initialization module that all workstreams import. This is the shared contract.

**File: `sentinel/workstream_6_integration/database.py`**
```python
"""
database.py -- Shared SQLite database initialization and connection management.
ALL workstreams import get_connection() from here.
Run init_database() exactly once at system startup.
"""

import sqlite3
import os

DB_PATH = os.environ.get("SENTINEL_DB_PATH", "./data/sentinel.db")


def get_connection() -> sqlite3.Connection:
    """Get a thread-local SQLite connection with WAL mode."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """Create all tables if they don't exist. Idempotent."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS anomaly_events (
            id TEXT PRIMARY KEY,
            detected_at TEXT NOT NULL,
            market_id TEXT NOT NULL,
            market_question TEXT,
            market_slug TEXT,
            anomaly_type TEXT NOT NULL,
            p_value REAL,
            z_score REAL,
            baseline_volume REAL,
            observed_volume REAL,
            price_before REAL,
            price_at_detection REAL,
            price_delta REAL,
            wallet_address TEXT,
            wallet_age_hours REAL,
            wallet_tx_count INTEGER,
            wallet_unique_markets INTEGER,
            trade_size_usdc REAL,
            order_book_impact REAL,
            cluster_size INTEGER,
            bss_score REAL,
            pes_score REAL,
            classification TEXT,
            confidence REAL,
            xai_narrative TEXT,
            temporal_gap_minutes REAL,
            fraud_triangle_json TEXT,
            osint_signals_found TEXT,
            sar_json TEXT,
            consensus_score REAL,
            vote_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS osint_events (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            source_name TEXT,
            source_tier INTEGER,
            event_type TEXT,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT,
            published_at TEXT NOT NULL,
            ingested_at TEXT DEFAULT (datetime('now')),
            latitude REAL,
            longitude REAL,
            country_code TEXT,
            entities_json TEXT,
            keywords_json TEXT,
            severity TEXT,
            relevance_to_markets TEXT
        );

        CREATE TABLE IF NOT EXISTS wallet_profiles (
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
            funding_source TEXT,
            funding_chain_json TEXT,
            cluster_id TEXT,
            cluster_wallets_json TEXT,
            risk_score REAL,
            is_fresh_wallet BOOLEAN,
            profile_json TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sentinel_index (
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
            market_outcome TEXT,
            outcome_verified BOOLEAN DEFAULT FALSE,
            created_at TEXT DEFAULT (datetime('now')),
            notes TEXT
        );

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
            vote TEXT NOT NULL,
            voter_session TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_anomaly_status ON anomaly_events(status);
        CREATE INDEX IF NOT EXISTS idx_anomaly_detected ON anomaly_events(detected_at);
        CREATE INDEX IF NOT EXISTS idx_anomaly_classification ON anomaly_events(classification);
        CREATE INDEX IF NOT EXISTS idx_osint_published ON osint_events(published_at);
        CREATE INDEX IF NOT EXISTS idx_osint_source ON osint_events(source);
    """)

    conn.commit()
    conn.close()
    print("Database initialized at", DB_PATH)


if __name__ == "__main__":
    init_database()
    # Verify
    conn = get_connection()
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"Tables created: {[t['name'] for t in tables]}")
    conn.close()
```

**Test command:**
```bash
cd sentinel
python -m workstream_6_integration.database
# Expected output: Database initialized at ./data/sentinel.db
# Tables created: ['anomaly_events', 'osint_events', 'wallet_profiles', 'sentinel_index', 'volume_baselines', 'arena_votes']
```

**DONE_WHEN:**
- [ ] Running `python -m workstream_6_integration.database` creates `./data/sentinel.db`
- [ ] All 6 tables exist with correct schemas
- [ ] `get_connection()` returns a working connection with WAL mode enabled
- [ ] Running the command a second time is idempotent (no errors)

---

### TASK 0.5: Makefile

```
AGENT: Integration Engineer
DEPENDS_ON: TASK 0.1, TASK 0.2
ESTIMATED_TIME: 10 minutes
```

**File: `sentinel/Makefile`**
```makefile
.PHONY: setup init-db verify run run-dashboard run-api test clean

setup:
	python -m venv .venv
	.venv/bin/pip install -r requirements.txt

init-db:
	python -m workstream_6_integration.database

verify:
	python -m scripts.verify_keys

run:
	python -m workstream_6_integration.orchestrator

run-dashboard:
	streamlit run workstream_5_dashboard/app.py

run-api:
	uvicorn workstream_6_integration.api:app --reload --port 8000

test:
	python -m pytest tests/ -v

clean:
	rm -rf data/sentinel.db data/chromadb/
```

**DONE_WHEN:**
- [ ] `make setup` installs dependencies
- [ ] `make init-db` creates the database
- [ ] File committed to repo

---

## PHASE 1: Parallel Data Pipelines

> **Goal:** Get data flowing into SQLite and ChromaDB from both Polymarket and OSINT sources.
> **Total time:** 3-5 hours
> **Who:** Two agents working in parallel (Data Engineer + OSINT Engineer).

---

### TASK 1.1: Polymarket CLOB API Client [PARALLEL Track A]

```
AGENT: Data Engineer
DEPENDS_ON: TASK 0.4
ESTIMATED_TIME: 45 minutes
INPUTS: Polymarket CLOB API (https://clob.polymarket.com)
OUTPUTS: sentinel/workstream_1_ingestion/polymarket_client.py
```

**Action:** Fork and adapt `pselamy/polymarket-insider-tracker`'s `clob_client.py`. If forking is too complex, write a minimal client that covers:

1. `GET /markets` -- list active markets with pagination
2. `GET /markets/{condition_id}` -- single market details
3. `GET /trades` -- recent trades (paginated, filterable by market)

**Implementation contract:**
```python
class PolymarketClient:
    def __init__(self, base_url: str = "https://clob.polymarket.com"):
        ...

    def get_active_markets(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """Returns list of active market dicts with keys: condition_id, question, slug, tokens, active."""
        ...

    def get_market(self, condition_id: str) -> dict:
        """Returns full market details."""
        ...

    def get_recent_trades(self, market_id: str = None, limit: int = 100) -> list[dict]:
        """Returns recent trades. Each trade has: id, market, asset_id, side, size, price, timestamp, maker_address, taker_address."""
        ...

    def get_market_orderbook(self, token_id: str) -> dict:
        """Returns order book: {bids: [...], asks: [...]}."""
        ...
```

**Test:**
```python
client = PolymarketClient()
markets = client.get_active_markets(limit=5)
assert len(markets) > 0
assert "condition_id" in markets[0] or "id" in markets[0]
print(f"Fetched {len(markets)} markets. First: {markets[0].get('question', markets[0].get('title', 'N/A'))[:80]}")
```

**DONE_WHEN:**
- [ ] `get_active_markets()` returns real market data
- [ ] `get_recent_trades()` returns real trade data with wallet addresses
- [ ] Client handles rate limiting (429 responses) with exponential backoff
- [ ] Client handles network errors without crashing

---

### TASK 1.2: Volume Spike Detector [PARALLEL Track A]

```
AGENT: Data Engineer
DEPENDS_ON: TASK 0.4
ESTIMATED_TIME: 60 minutes
OUTPUTS: sentinel/workstream_1_ingestion/detectors/volume_spike.py
```

**Action:** Implement Welford's online algorithm for streaming mean/variance per market. Detect volume spikes when z-score exceeds threshold.

**Implementation contract:**
```python
@dataclass
class WelfordState:
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0

    def update(self, value: float): ...
    @property
    def variance(self) -> float: ...
    @property
    def stddev(self) -> float: ...
    def z_score(self, value: float) -> float: ...
        # Return 0.0 if count < 48 (cold-start protection)


class VolumeAnomalyDetector:
    def __init__(self, db_conn, z_threshold: float = 2.0): ...

    def check(self, market_id: str, market_question: str,
              current_volume: float, current_price: float) -> Optional[dict]:
        """
        Returns anomaly_event dict if volume is anomalous, else None.
        Anomaly dict must match anomaly_events schema:
          id, detected_at, market_id, market_question, anomaly_type='VOLUME_SPIKE',
          p_value, z_score, baseline_volume, observed_volume, price_at_detection
        """
        ...
```

**Thresholds:**
- z >= 2.0: medium confidence anomaly
- z >= 3.0: high confidence anomaly
- Minimum 48 hourly observations before flagging (prevent cold-start false positives)

**Test:**
```python
import sqlite3
from workstream_6_integration.database import init_database, get_connection

init_database()
conn = get_connection()
detector = VolumeAnomalyDetector(conn, z_threshold=2.0)

# Feed 100 normal observations, then one spike
for i in range(100):
    result = detector.check("test_market", "Will X happen?", 1000.0 + (i % 10), 0.5)
    assert result is None  # Should not fire during warm-up or normal volume

# Inject a 5x spike
result = detector.check("test_market", "Will X happen?", 5000.0, 0.65)
assert result is not None
assert result["anomaly_type"] == "VOLUME_SPIKE"
assert result["z_score"] > 2.0
print(f"Spike detected: z={result['z_score']:.2f}, p={result['p_value']:.6f}")
```

**DONE_WHEN:**
- [ ] WelfordState correctly computes streaming mean/variance
- [ ] Detector does NOT fire during first 48 observations (cold-start protection)
- [ ] Detector fires on 3x+ volume spikes after warm-up
- [ ] Returns valid anomaly_event dict with all required fields
- [ ] p-value computed correctly using `scipy.stats.norm.sf()`

---

### TASK 1.3: Price Jump Detector [PARALLEL Track A]

```
AGENT: Data Engineer
DEPENDS_ON: TASK 1.2 (reuses WelfordState)
ESTIMATED_TIME: 30 minutes
OUTPUTS: sentinel/workstream_1_ingestion/detectors/price_jump.py
```

**Action:** Same Welford pattern as volume_spike.py but tracking hourly absolute price deltas.

**Implementation contract:**
```python
class PriceJumpDetector:
    def __init__(self, db_conn, z_threshold: float = 2.0): ...

    def check(self, market_id: str, market_question: str,
              current_price: float, price_1h_ago: float) -> Optional[dict]:
        """
        Track distribution of hourly |price_now - price_1h_ago|.
        Returns anomaly_event dict with anomaly_type='PRICE_JUMP' if anomalous.
        Includes: price_before, price_at_detection, price_delta.
        """
        ...
```

**DONE_WHEN:**
- [ ] Detects abnormal price movements (>2 sigma from rolling mean of price deltas)
- [ ] Produces valid anomaly_event dict with PRICE_JUMP type
- [ ] Cold-start protection (minimum 48 observations)

---

### TASK 1.4: Fork pselamy Detectors [PARALLEL Track A]

```
AGENT: Data Engineer
DEPENDS_ON: TASK 0.4
ESTIMATED_TIME: 90 minutes
RISK: pselamy code uses SQLAlchemy/Postgres. Migration to raw SQLite will take time. If blocked, write simplified versions.
INPUTS: https://github.com/pselamy/polymarket-insider-tracker (MIT license)
OUTPUTS:
  - sentinel/workstream_1_ingestion/detectors/fresh_wallet.py
  - sentinel/workstream_1_ingestion/detectors/size_anomaly.py
  - sentinel/workstream_1_ingestion/detectors/sniper_cluster.py
  - sentinel/workstream_1_ingestion/detectors/scorer.py
  - sentinel/workstream_1_ingestion/wallet_profiler.py
```

**Action:** Adapt the following from pselamy's repo, replacing SQLAlchemy models with raw SQLite queries against our schema:

| pselamy file | Our file | What it does |
|---|---|---|
| `src/detector/fresh_wallet.py` | `detectors/fresh_wallet.py` | Flag wallets < 24h old with few txs |
| `src/detector/size_anomaly.py` | `detectors/size_anomaly.py` | Trade size vs market depth |
| `src/detector/sniper.py` | `detectors/sniper_cluster.py` | DBSCAN clustering of coordinated wallets |
| `src/detector/scorer.py` | `detectors/scorer.py` | Composite risk score (0-100) |
| `src/profiler/analyzer.py` + `chain.py` + `funding.py` | `wallet_profiler.py` | Wallet history and funding chain |

**Each detector must expose:**
```python
class XxxDetector:
    def check(self, trade: dict, wallet_profile: dict = None) -> Optional[dict]:
        """Returns anomaly_event dict or None."""
        ...
```

**FALLBACK:** If forking pselamy is too complex, write simplified versions:
- `fresh_wallet.py`: Check `wallet_age_hours < 24 AND wallet_tx_count < 5`
- `size_anomaly.py`: Check `trade_size_usdc > 3 * avg_trade_size_usdc` for that wallet
- `sniper_cluster.py`: Group wallets trading the same market within a 10-minute window, flag clusters of 3+
- `scorer.py`: Weighted sum of all detector flags

**DONE_WHEN:**
- [ ] Each detector can process a trade dict and return anomaly_event or None
- [ ] Wallet profiler writes to `wallet_profiles` table
- [ ] DBSCAN sniper cluster detection works with sklearn.cluster.DBSCAN
- [ ] Composite scorer produces 0-100 risk scores

---

### TASK 1.5: Anomaly Emitter [PARALLEL Track A]

```
AGENT: Data Engineer
DEPENDS_ON: TASK 0.4, TASK 1.2
ESTIMATED_TIME: 30 minutes
OUTPUTS: sentinel/workstream_1_ingestion/anomaly_emitter.py
```

**Action:** Collect outputs from all detectors, enrich with wallet data, write to `anomaly_events` table.

```python
class AnomalyEmitter:
    def __init__(self, db_conn): ...

    def emit(self, anomaly: dict, wallet_address: str = None) -> str:
        """
        1. If wallet_address provided, look up wallet_profile and merge fields
        2. Insert into anomaly_events table
        3. Return the anomaly event ID
        """
        ...
```

**DONE_WHEN:**
- [ ] Writes complete rows to `anomaly_events` table
- [ ] Merges wallet profile data when available
- [ ] Returns the UUID of the inserted row
- [ ] Handles duplicate detection (same market + same wallet within 5 min window)

---

### TASK 1.6: Ingestion Main Loop [PARALLEL Track A]

```
AGENT: Data Engineer
DEPENDS_ON: TASK 1.1, TASK 1.2, TASK 1.3, TASK 1.4, TASK 1.5
ESTIMATED_TIME: 45 minutes
OUTPUTS: sentinel/workstream_1_ingestion/main.py
```

**Action:** Polling loop that runs all detectors on live data.

```python
async def run_market_monitor(db):
    """
    Every 60 seconds:
    1. Fetch active markets from Polymarket
    2. For each market, get current volume and price
    3. Run VolumeAnomalyDetector.check() and PriceJumpDetector.check()
    4. For recent trades, run FreshWalletDetector, SizeAnomalyDetector, SniperClusterDetector
    5. Emit any anomalies via AnomalyEmitter
    """
    ...
```

**DONE_WHEN:**
- [ ] Loop runs for 10+ minutes without crashing
- [ ] Polls Polymarket at 60-second intervals
- [ ] Detected anomalies appear in `anomaly_events` table
- [ ] Handles API errors gracefully (logs and continues)
- [ ] Ctrl+C cleanly stops the loop

---

### TASK 1.7: Backtest Script [PARALLEL Track A, LOW PRIORITY]

```
AGENT: Data Engineer
DEPENDS_ON: TASK 1.1, TASK 1.2, TASK 1.4
ESTIMATED_TIME: 90 minutes
RISK: This feeds WS4 fine-tuning data. If time-constrained, skip and use purely synthetic data in TASK 4.1.
OUTPUTS: sentinel/workstream_1_ingestion/backtest.py, data/backtest_anomalies.jsonl
```

**Action:** Replay 60 days of historical trades through all detectors. For each flagged anomaly, check if the market has resolved and whether the trader's position was correct.

**Output JSONL format (one object per line):**
```json
{
  "anomaly_event": { ... all anomaly_events fields ... },
  "outcome": "correct_prediction | incorrect_prediction | unresolved",
  "timing_advantage_hours": 4.5,
  "market_resolved_at": "2025-01-15T00:00:00Z"
}
```

**DONE_WHEN:**
- [ ] Processes at least 30 days of historical data
- [ ] Outputs labeled JSONL with outcome field
- [ ] Produces at least 50 real historical anomalies

---

### TASK 2.1: ChromaDB Vector Store [PARALLEL Track B]

```
AGENT: OSINT Engineer
DEPENDS_ON: TASK 0.4
ESTIMATED_TIME: 45 minutes
OUTPUTS: sentinel/workstream_2_osint/vector_store.py
```

**Action:** Wrap ChromaDB for storing and querying OSINT event embeddings using Mistral Embed.

```python
class SentinelVectorStore:
    def __init__(self, persist_dir: str = "./data/chromadb"): ...

    def add_event(self, event: dict):
        """
        Embed "{title}. {summary}" via Mistral Embed.
        Store with metadata: source, source_name, source_tier, published_at, event_type, severity, country_code.
        """
        ...

    def query_by_timestamp_and_topic(self, query_text: str, before_timestamp: str, n_results: int = 10) -> dict:
        """
        Core RAG query for Stage 2 XAI.
        Returns OSINT events relevant to query_text that were published BEFORE before_timestamp.
        Uses Mistral Embed for query embedding.
        Applies ChromaDB where filter: published_at <= before_timestamp.
        """
        ...

    def get_event_count(self) -> int:
        """Return total number of stored events."""
        ...
```

**CRITICAL IMPLEMENTATION DETAIL:** Batch embedding calls to Mistral. The `add_event` method will be called hundreds of times. Queue events and embed in batches of 10-25 to avoid rate limits.

**Test:**
```python
vs = SentinelVectorStore()
vs.add_event({
    "id": "test_001",
    "title": "Iran nuclear talks collapse",
    "summary": "IAEA reports enrichment increase as negotiations break down.",
    "source": "rss", "source_name": "Reuters", "source_tier": 1,
    "published_at": "2025-06-15T10:00:00Z",
    "event_type": "political", "severity": "high", "country_code": "IR"
})
results = vs.query_by_timestamp_and_topic("Iran nuclear deal", before_timestamp="2025-06-16T00:00:00Z")
assert len(results["documents"][0]) > 0
print(f"Found {len(results['documents'][0])} matching events")
```

**DONE_WHEN:**
- [ ] Events embed and store in ChromaDB
- [ ] Timestamp-filtered queries return correct results
- [ ] Mistral Embed API calls work
- [ ] Handles rate limiting with retry/backoff

---

### TASK 2.2: RSS Feed Aggregator [PARALLEL Track B]

```
AGENT: OSINT Engineer
DEPENDS_ON: TASK 0.4, TASK 2.1
ESTIMATED_TIME: 60 minutes
OUTPUTS: sentinel/workstream_2_osint/sources/rss_aggregator.py, sentinel/workstream_2_osint/feed_list.py
```

**Action:** Poll 20-30 curated RSS feeds, deduplicate by URL hash, write to `osint_events` table and ChromaDB.

**Minimum feed list for MVP (in `feed_list.py`):**
```python
FEEDS = [
    # Tier 1 - Wire services
    {"url": "http://feeds.bbci.co.uk/news/world/rss.xml", "name": "BBC World", "tier": 1},
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "name": "Al Jazeera", "tier": 2},
    {"url": "https://www.theguardian.com/world/rss", "name": "Guardian World", "tier": 2},
    {"url": "http://rss.cnn.com/rss/edition_world.rss", "name": "CNN World", "tier": 2},

    # Tier 3 - Defense/specialized
    {"url": "https://breakingdefense.com/feed/", "name": "Breaking Defense", "tier": 3},
    {"url": "https://www.defenseone.com/rss/", "name": "Defense One", "tier": 3},

    # Add 15-20 more feeds covering energy, finance, geopolitics
]
```

**Implementation contract:**
```python
class RSSAggregator:
    def __init__(self, db_conn, vector_store, feeds=FEEDS): ...

    def poll_all(self) -> list[dict]:
        """Poll all feeds, deduplicate, return new events."""
        ...

    def _poll_feed(self, feed_config: dict) -> list[dict]:
        """Parse single feed, return new osint_event dicts."""
        ...
```

**Deduplication:** SHA-256 hash of entry URL, truncated to 16 chars. Store in `seen_hashes` set (in-memory) and check against `osint_events.id` in SQLite.

**DONE_WHEN:**
- [ ] Polls at least 20 RSS feeds successfully
- [ ] New events written to `osint_events` table
- [ ] New events embedded in ChromaDB via vector_store
- [ ] Duplicate entries are skipped
- [ ] Failed feeds are logged but don't crash the loop

---

### TASK 2.3: GDELT Client [PARALLEL Track B]

```
AGENT: OSINT Engineer
DEPENDS_ON: TASK 0.4, TASK 2.1
ESTIMATED_TIME: 60 minutes
OUTPUTS: sentinel/workstream_2_osint/sources/gdelt_client.py
```

**Action:** Poll GDELT 2.0 Events API every 15 minutes. Parse the tab-separated event data.

**Data source:** `http://data.gdeltproject.org/gdeltv2/lastupdate.txt` points to the latest event file (CSV/TSV).

**Key fields to extract and map to `osint_event`:**
- SQLDATE -> published_at
- Actor1Name, Actor2Name -> entities_json
- EventCode (CAMEO codes) -> event_type mapping
- GoldsteinScale -> severity mapping (-10 to +10, negative = conflict)
- ActionGeo_Lat, ActionGeo_Long -> latitude, longitude
- SOURCEURL -> url

**Severity mapping from GoldsteinScale:**
- <= -7: critical
- <= -3: high
- <= 0: medium
- <= 3: low
- > 3: info

**DONE_WHEN:**
- [ ] Downloads and parses GDELT lastupdate file
- [ ] Produces valid osint_event dicts
- [ ] Events written to SQLite and ChromaDB
- [ ] Handles network errors gracefully

---

### TASK 2.4: ACLED Client [PARALLEL Track B]

```
AGENT: OSINT Engineer
DEPENDS_ON: TASK 0.4, TASK 2.1
ESTIMATED_TIME: 45 minutes
OUTPUTS: sentinel/workstream_2_osint/sources/acled_client.py
```

**Action:** Poll ACLED API every 30 minutes for conflict events.

**API:** `https://acleddata.com/data-export-tool/`

**Severity mapping from ACLED event_type:**
- Battles, Explosions/Remote violence -> critical
- Violence against civilians -> high
- Protests, Riots -> medium
- Strategic developments -> low

**DONE_WHEN:**
- [ ] Fetches at least one batch of conflict events
- [ ] Produces valid osint_event dicts with geolocation
- [ ] Events written to SQLite and ChromaDB

---

### TASK 2.5: Market Correlator [PARALLEL Track B]

```
AGENT: OSINT Engineer
DEPENDS_ON: TASK 2.2 (needs some OSINT events), TASK 1.1 (needs market list)
ESTIMATED_TIME: 60 minutes
OUTPUTS: sentinel/workstream_2_osint/processors/market_correlator.py
```

**Action:** For each new OSINT event, compute text similarity against active Polymarket market questions. Use keyword overlap (TF-IDF), NOT embeddings (keep it fast).

```python
class MarketCorrelator:
    def __init__(self, db_conn): ...

    def update_market_list(self):
        """Refresh the list of active markets from Polymarket (or from anomaly_events table)."""
        ...

    def correlate(self, osint_event: dict) -> list[str]:
        """
        Returns list of market_ids that match this OSINT event.
        Uses TF-IDF keyword overlap between event title+summary and market questions.
        Threshold: cosine similarity > 0.15.
        """
        ...
```

**DONE_WHEN:**
- [ ] Matches OSINT events to at least 3 Polymarket markets in testing
- [ ] Updates `osint_events.relevance_to_markets` field
- [ ] Runs fast (< 100ms per event)

---

### TASK 2.6: OSINT Main Loop [PARALLEL Track B]

```
AGENT: OSINT Engineer
DEPENDS_ON: TASK 2.1, TASK 2.2, TASK 2.3, TASK 2.4, TASK 2.5
ESTIMATED_TIME: 30 minutes
OUTPUTS: sentinel/workstream_2_osint/main.py
```

**Action:** Orchestrate all OSINT sources on their respective polling intervals.

```python
async def run_osint_monitor(db):
    """
    Concurrent polling:
    - RSS feeds: every 5 minutes (staggered)
    - GDELT: every 15 minutes
    - ACLED: every 30 minutes
    - Market correlation: after each new batch of events
    """
    ...
```

**DONE_WHEN:**
- [ ] All sources poll on their intervals
- [ ] Loop runs 10+ minutes without crashing
- [ ] `osint_events` table is populated
- [ ] ChromaDB has embedded events
- [ ] Failed sources don't crash the loop

---

## PHASE 2: Feature Engineering + Training Data

> **Goal:** Transform raw anomaly data into structured feature payloads for the AI classifier. Simultaneously generate training data and kick off fine-tuning.
> **Total time:** 2-3 hours
> **Who:** ML Engineer starts when WS1 has sample data in SQLite (or uses mock data). AI Engineer starts training data generation immediately.

---

### TASK 3.1: Feature Extraction

```
AGENT: ML Engineer
DEPENDS_ON: TASK 0.4 (schema), TASK 1.5 (sample anomaly_events in DB, OR use mock data)
ESTIMATED_TIME: 60 minutes
OUTPUTS: sentinel/workstream_3_features/feature_builder.py
```

**Action:** Extract flat feature dictionaries from `anomaly_events` + `wallet_profiles` rows.

**Feature groups (all features must be present in output):**

```python
FEATURE_SCHEMA = {
    # Liquidity
    "observed_volume": float,       # Volume at detection time
    "baseline_volume": float,       # Rolling 7-day mean
    "volume_ratio": float,          # observed / baseline
    "order_book_impact": float,     # % of visible book consumed
    "market_daily_volume": float,   # Total market volume in last 24h

    # Volatility
    "z_score": float,               # Std devs from baseline
    "price_delta": float,           # Absolute price change
    "price_velocity": float,        # price_delta / time_window_hours
    "idiosyncratic_vol": float,     # Market-specific vol vs platform avg

    # Entity/Governance
    "wallet_age_hours": float,
    "wallet_tx_count": int,
    "wallet_unique_markets": int,
    "trade_size_usdc": float,
    "avg_trade_size_usdc": float,
    "trade_size_ratio": float,      # This trade / wallet average
    "is_fresh_wallet": bool,        # wallet_age_hours < 24
    "cluster_size": int,
    "win_rate": float,
    "funding_source": str,          # 'cex'|'dex'|'bridge'|'unknown'
    "market_concentration": float,  # % of wallet's trades in this market

    # Timing
    "hour_of_day": int,             # 0-23 UTC
    "day_of_week": int,             # 0-6
    "minutes_since_market_creation": float,
    "minutes_to_market_resolution": float,
}
```

```python
class FeatureBuilder:
    def __init__(self, db_conn): ...

    def extract(self, anomaly_event_id: str) -> dict:
        """
        Join anomaly_events + wallet_profiles, compute derived features.
        Returns flat dict matching FEATURE_SCHEMA.
        Missing values should be filled with sensible defaults (0, 'unknown', etc).
        """
        ...
```

**DONE_WHEN:**
- [ ] Extracts all listed features from a real or mock anomaly_event
- [ ] Handles missing wallet_profile gracefully (defaults)
- [ ] Returns a flat dict with consistent keys

---

### TASK 3.2: Spearman Hierarchical Clustering

```
AGENT: ML Engineer
DEPENDS_ON: TASK 3.1
ESTIMATED_TIME: 45 minutes
OUTPUTS: sentinel/workstream_3_features/clustering.py
```

**Action:** Group correlated features into clades using Spearman rank-order correlation.

```python
def compute_clades(feature_matrix: np.ndarray, feature_names: list[str],
                   threshold: float = 0.5) -> dict[str, list[str]]:
    """
    1. Compute Spearman correlation matrix
    2. Convert to distance: 1 - |correlation|
    3. Ward linkage hierarchical clustering
    4. Cut dendrogram at threshold
    5. Return dict: clade_name -> [feature_names]

    Expected output (approximately):
      - Liquidity Clade: volume_ratio, order_book_impact, market_daily_volume
      - Volatility Clade: z_score, price_velocity, idiosyncratic_vol
      - Entity Clade: wallet_age_hours, wallet_tx_count, is_fresh_wallet, cluster_size
      - Timing Clade: hour_of_day, minutes_since_market_creation
      - Size Clade: trade_size_usdc, trade_size_ratio, market_concentration
    """
    ...
```

**DONE_WHEN:**
- [ ] Produces 3-5 interpretable clades from test data
- [ ] Uses scipy.stats.spearmanr and scipy.cluster.hierarchy
- [ ] Dendrogram can be plotted for debugging (save to file)

---

### TASK 3.3: Permutation Importance Weighting

```
AGENT: ML Engineer
DEPENDS_ON: TASK 3.1
ESTIMATED_TIME: 30 minutes
RISK: Requires labeled data (from backtest TASK 1.7). If unavailable, use mock labels or skip and assign uniform weights.
OUTPUTS: sentinel/workstream_3_features/importance_weighting.py
```

```python
def compute_importance_weights(X: np.ndarray, y: np.ndarray,
                               feature_names: list[str]) -> dict[str, float]:
    """
    1. Train RandomForestClassifier (n_estimators=100, class_weight='balanced')
    2. Run sklearn.inspection.permutation_importance (n_repeats=10)
    3. Normalize weights to [0, 1]
    4. Return dict: feature_name -> normalized_weight
    """
    ...
```

**FALLBACK:** If no labeled data available, return uniform weights `{name: 1.0 for name in feature_names}` and note this in the payload.

**DONE_WHEN:**
- [ ] Produces normalized importance weights for all features
- [ ] Works with at least 50 samples
- [ ] Fallback to uniform weights works

---

### TASK 3.4: Payload Formatter

```
AGENT: ML Engineer
DEPENDS_ON: TASK 3.1, TASK 3.2, TASK 3.3
ESTIMATED_TIME: 30 minutes
OUTPUTS: sentinel/workstream_3_features/payload_formatter.py
```

**Action:** Combine features, clades, and weights into the JSON payload that gets sent to Mistral.

**Output JSON format (this is the contract with Workstream 4):**
```json
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
    "entity_governance": {
      "importance": 0.91,
      "features": {
        "wallet_age_hours": {"value": 2.5, "weight": 0.95, "description": "Wallet created 2.5 hours ago"},
        "is_fresh_wallet": {"value": true, "weight": 0.90, "description": "Fewer than 5 lifetime txs"}
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
```

**DONE_WHEN:**
- [ ] Produces valid JSON matching the schema above
- [ ] All clades have importance scores
- [ ] Each feature has value, weight, and human-readable description
- [ ] End-to-end: anomaly_event_id in -> JSON payload out

---

### TASK 4.1: Synthetic Training Data Generation [CAN START IMMEDIATELY]

```
AGENT: AI Engineer
DEPENDS_ON: TASK 0.2 (Mistral API key verified)
ESTIMATED_TIME: 60 minutes (30 min coding + 30 min API generation time)
OUTPUTS: sentinel/data/synthetic_training.jsonl
```

**Action:** Use Mistral Large to generate ~500 synthetic training examples.

**Target class distribution:**
- 40% SPECULATOR (200 examples)
- 25% FAST_REACTOR (125 examples)
- 20% OSINT_EDGE (100 examples)
- 15% INSIDER (75 examples)

**Each JSONL line must be:**
```json
{"messages": [
  {"role": "system", "content": "<classifier system prompt>"},
  {"role": "user", "content": "<feature payload JSON>"},
  {"role": "assistant", "content": "{\"classification\": \"INSIDER\", \"confidence\": 0.87, \"bss_score\": 82.5, \"pes_score\": 12.0, \"reasoning\": \"...\"}"}
]}
```

**CRITICAL:** Kick this off early. The generation takes 20-30 min of API time. Then the fine-tuning job takes another 30-60 min. Total lead time: ~90 min from start.

**DONE_WHEN:**
- [ ] 500+ examples generated across all 4 classes
- [ ] Each example has valid feature payload JSON and classification output JSON
- [ ] Class distribution approximately matches targets
- [ ] JSONL file validates (each line is parseable JSON)

---

### TASK 4.2: Submit Fine-Tuning Job

```
AGENT: AI Engineer
DEPENDS_ON: TASK 4.1
ESTIMATED_TIME: 15 minutes (coding) + 30-60 minutes (Mistral processing)
OUTPUTS: sentinel/config/fine_tuned_model.json
```

**Action:** Upload JSONL to Mistral API, start fine-tuning job, poll until complete.

```python
# Key API calls:
client.files.upload(file={"file_name": "sentinel_train.jsonl", "content": f})
client.fine_tuning.jobs.create(
    model="open-mistral-7b",  # or "mistral-small-latest"
    training_files=[{"file_id": train_file.id, "weight": 1}],
    validation_files=[val_file.id],
    hyperparameters={"training_steps": 100, "learning_rate": 0.0001},
    auto_start=True,
)
# Poll with: client.fine_tuning.jobs.get(job_id=job.id)
# Save result: {"model_id": status.fine_tuned_model}
```

**RISK:** Job may fail. FALLBACK: Use base `mistral-small-latest` with detailed few-shot prompting in Stage 1.

**DONE_WHEN:**
- [ ] Fine-tuning job submitted successfully
- [ ] Job ID recorded
- [ ] Model ID saved to `config/fine_tuned_model.json` when job completes
- [ ] OR: fallback documented if job fails

---

## PHASE 3: AI Classification Pipeline

> **Goal:** Three-stage pipeline: classify, explain, report.
> **Total time:** 3-4 hours
> **Who:** AI Engineer. Can start Stage 1 with base model while fine-tuning runs.

---

### TASK 4.3: Stage 1 -- Triage Classifier

```
AGENT: AI Engineer
DEPENDS_ON: TASK 3.4 (payload format), TASK 4.2 (fine-tuned model, or use base model)
ESTIMATED_TIME: 60 minutes
OUTPUTS: sentinel/workstream_4_ai_pipeline/stage1_classifier.py
```

**System prompt** (save to `prompts/classifier_system.txt`):
```
You are Sentinel, a financial anomaly classifier for prediction markets. You analyze structured feature data from Polymarket trade anomalies and classify them into exactly one of four categories:

1. INSIDER - Material non-public information. High BSS (70-100), Low PES (0-30).
2. OSINT_EDGE - Skillful use of public intelligence. Moderate BSS (30-60), High PES (60-90).
3. FAST_REACTOR - Quick reaction to breaking news. Low BSS (10-40), High PES (70-100).
4. SPECULATOR - Normal speculation, no information edge. Low BSS (0-20), Moderate PES (40-70).

Respond ONLY with valid JSON: {"classification": "...", "confidence": 0.0-1.0, "bss_score": 0-100, "pes_score": 0-100, "reasoning": "2-3 sentences"}
```

```python
class SentinelClassifier:
    def __init__(self, model_id: str = None):
        """Use fine-tuned model_id if available, else 'mistral-small-latest'."""
        ...

    def classify(self, feature_payload: dict) -> dict:
        """
        Send feature payload to Mistral. Parse JSON response.
        Returns: {"classification": str, "confidence": float, "bss_score": float, "pes_score": float, "reasoning": str}
        MUST handle: malformed JSON (retry up to 3 times), API errors, timeouts.
        Temperature: 0.1 (low for consistency).
        """
        ...
```

**Test with 4 manually crafted payloads (one per class):**
```python
# INSIDER test case: fresh wallet, large trade, no public signals
insider_payload = {
    "anomaly_id": "test-001",
    "market": {"question": "Will Country X leader resign by March?", "current_price": 0.25},
    "clades": {
        "entity_governance": {
            "importance": 0.95,
            "features": {
                "wallet_age_hours": {"value": 3.0, "weight": 0.95, "description": "3h old wallet"},
                "is_fresh_wallet": {"value": True, "weight": 0.9, "description": "Brand new"},
                "cluster_size": {"value": 4, "weight": 0.85, "description": "4-wallet cluster"}
            }
        },
        "liquidity": {
            "importance": 0.8,
            "features": {
                "volume_ratio": {"value": 6.0, "weight": 0.85, "description": "6x baseline"},
                "trade_size_usdc": {"value": 25000, "weight": 0.7, "description": "$25k trade"}
            }
        }
    },
    "raw_scores": {"composite_risk": 88.0}
}
result = classifier.classify(insider_payload)
assert result["classification"] == "INSIDER"
assert result["bss_score"] > 60
```

**DONE_WHEN:**
- [ ] Returns valid JSON with all required fields for all 4 test cases
- [ ] Correctly classifies obvious INSIDER vs SPECULATOR cases
- [ ] Handles malformed model output with retry logic
- [ ] Latency < 5 seconds per classification

---

### TASK 4.4: Stage 2 -- Magistral XAI Layer

```
AGENT: AI Engineer
DEPENDS_ON: TASK 4.3, TASK 2.1 (ChromaDB populated)
ESTIMATED_TIME: 90 minutes
OUTPUTS: sentinel/workstream_4_ai_pipeline/stage2_xai.py
```

**This is the most important component for the demo.** It produces the explainable reasoning.

```python
class MagistralXAI:
    def __init__(self, vector_store: SentinelVectorStore): ...

    def analyze(self, anomaly: dict, classification: dict) -> dict:
        """
        1. Query ChromaDB for OSINT events BEFORE trade timestamp
        2. Build context combining anomaly details + classification + OSINT signals
        3. Send to Magistral (magistral-medium-latest) with XAI system prompt
        4. Parse response into structured output

        Returns: {
            "xai_narrative": str,       # Full human-readable explanation
            "temporal_gap_minutes": float, # Minutes between trade and nearest public signal
            "osint_signals_found": list,   # Matching OSINT events
            "fraud_triangle": {            # For INSIDER classifications
                "opportunity": str,
                "pressure": str,
                "rationalization": str
            }
        }
        """
        ...

    def _compute_temporal_gap(self, anomaly: dict, signals: list) -> float:
        """
        Parse trade timestamp and signal timestamps.
        Return minutes between trade and NEAREST PRIOR public signal.
        NEGATIVE means trade came BEFORE any public signal (suspicious).
        POSITIVE means public signal was available (less suspicious).
        """
        ...
```

**Model:** `magistral-medium-latest`, temperature 0.7, max_tokens 4000.

**DONE_WHEN:**
- [ ] Queries ChromaDB for relevant OSINT events
- [ ] Produces readable XAI narrative
- [ ] Computes temporal gap correctly (negative = trade before public info)
- [ ] Fraud triangle populated for INSIDER classifications
- [ ] Latency < 15 seconds per analysis

---

### TASK 4.5: Stage 3 -- SAR Report Generator

```
AGENT: AI Engineer
DEPENDS_ON: TASK 4.4
ESTIMATED_TIME: 45 minutes
OUTPUTS: sentinel/workstream_4_ai_pipeline/stage3_sar.py
```

```python
class SARGenerator:
    def __init__(self): ...

    def generate(self, anomaly: dict, classification: dict, xai: dict) -> dict:
        """
        Generate structured SAR JSON using Mistral Large.
        Model: mistral-large-latest, temperature 0.2.
        Output must include ALL fields: sar_id, generated_at, classification,
        severity, summary, subject, activity, temporal_analysis, fraud_triangle,
        evidence, recommendation, confidence, xai_narrative.
        """
        ...
```

**DONE_WHEN:**
- [ ] Produces complete, valid SAR JSON
- [ ] All required fields present
- [ ] Recommendation field is one of: ESCALATE, MONITOR, ARCHIVE
- [ ] Latency < 10 seconds

---

### TASK 4.6: Pipeline Orchestrator

```
AGENT: AI Engineer
DEPENDS_ON: TASK 4.3, TASK 4.4, TASK 4.5
ESTIMATED_TIME: 45 minutes
OUTPUTS: sentinel/workstream_4_ai_pipeline/pipeline.py
```

```python
class SentinelPipeline:
    def __init__(self, db, vector_store, classifier, xai_engine, sar_generator):
        self.bss_threshold = 50.0  # Only run XAI if BSS > 50
        ...

    def process_anomaly(self, anomaly_id: str):
        """
        1. Load anomaly from DB
        2. Build feature payload (call WS3 payload_formatter)
        3. Stage 1: Classify -> update anomaly_events row
        4. If BSS > 50: Stage 2 XAI -> update row
        5. If INSIDER or BSS > 75: Stage 3 SAR -> update row + add to sentinel_index
        """
        ...

    def run_batch(self):
        """Process all anomaly_events where status = 'pending'. Error handling per-anomaly."""
        ...
```

**DONE_WHEN:**
- [ ] Processes pending anomalies end-to-end
- [ ] Updates anomaly_events rows with classification, XAI, SAR data
- [ ] Adds INSIDER/OSINT_EDGE cases to sentinel_index
- [ ] Single anomaly processing < 30 seconds
- [ ] Errors on one anomaly don't block the batch

---

## PHASE 4: Dashboard

> **Goal:** Streamlit dashboard with 5 pages, centered on the temporal gap visualization.
> **Total time:** 3-5 hours
> **Who:** Frontend Engineer. Can start with mock data immediately.

---

### TASK 5.1: Mock Data Generator

```
AGENT: Frontend Engineer
DEPENDS_ON: TASK 0.4
ESTIMATED_TIME: 30 minutes
OUTPUTS: sentinel/workstream_5_dashboard/utils/mock_data.py
```

**Action:** Generate realistic mock data for all dashboard pages so development can proceed without waiting for the live pipeline.

```python
def generate_mock_anomalies(n: int = 20) -> list[dict]:
    """Generate n mock anomaly_events with varied classifications, BSS scores, etc."""
    ...

def generate_mock_osint_signals(anomaly: dict, n: int = 5) -> list[dict]:
    """Generate mock OSINT signals with timestamps around the anomaly's detected_at."""
    ...

def seed_mock_database(db_conn):
    """Insert mock data into all tables for dashboard development."""
    ...
```

**DONE_WHEN:**
- [ ] Produces realistic mock data for all 4 classification types
- [ ] Mock OSINT signals have varied timestamps (some before trade, some after)
- [ ] Can seed the database for dashboard testing

---

### TASK 5.2: Temporal Gap Chart (HIGHEST PRIORITY VISUALIZATION)

```
AGENT: Frontend Engineer
DEPENDS_ON: TASK 5.1
ESTIMATED_TIME: 60 minutes
OUTPUTS: sentinel/workstream_5_dashboard/components/temporal_gap_chart.py
```

**This is the single most important visualization for the demo.**

```python
def render_temporal_gap(anomaly: dict, osint_signals: list) -> plotly.graph_objects.Figure:
    """
    Horizontal timeline showing:
    1. Red diamond: Trade timestamp
    2. Green circles: OSINT signal timestamps (labeled with source)
    3. Orange marker: News break timestamp (if known)
    4. Highlighted zone between trade and earliest public signal:
       - RED zone if trade came BEFORE any signal ("NO PUBLIC PRECEDENT")
       - GREEN zone if signal came first ("PUBLIC SIGNAL AVAILABLE")
    5. Gap measurement in minutes displayed prominently
    """
    ...
```

**DONE_WHEN:**
- [ ] Renders correctly with mock data
- [ ] Red zone clearly visible for INSIDER cases (trade before public info)
- [ ] Green zone for OSINT_EDGE cases (public info existed before trade)
- [ ] Interactive hover shows signal details
- [ ] Visually compelling (this wins the demo)

---

### TASK 5.3: Dashboard Pages

```
AGENT: Frontend Engineer
DEPENDS_ON: TASK 5.1, TASK 5.2
ESTIMATED_TIME: 120 minutes
OUTPUTS:
  - sentinel/workstream_5_dashboard/app.py
  - sentinel/workstream_5_dashboard/pages/1_Live_Monitor.py
  - sentinel/workstream_5_dashboard/pages/2_Case_Detail.py
  - sentinel/workstream_5_dashboard/pages/3_Sentinel_Index.py
  - sentinel/workstream_5_dashboard/pages/4_Arena.py
  - sentinel/workstream_5_dashboard/pages/5_System_Health.py
```

**Page priority (build in this order):**

**Page 2: Case Detail (build first -- this is the demo centerpiece)**
- Top: Market question, current price, classification badge (color-coded)
- Middle: Temporal gap chart (from TASK 5.2)
- XAI narrative display (markdown rendered)
- Fraud triangle visualization (three connected nodes with labels)
- Feature radar chart showing clade importances
- Bottom: Full SAR report (collapsible JSON viewer)

**Page 1: Live Monitor**
- Auto-refreshing table of anomaly_events (st.dataframe with auto_refresh)
- Columns: Time, Market, Type, BSS, Classification, Status
- Color coding: INSIDER=red, OSINT_EDGE=yellow, FAST_REACTOR=blue, SPECULATOR=gray
- Click row -> navigate to Case Detail
- Filters: classification, date range, BSS threshold

**Page 3: Sentinel Index**
- Searchable, sortable table of sentinel_index cases
- Summary stats: total cases, breakdown by classification
- Export button (CSV download)

**Page 4: Arena**
- Display one anonymized case at a time
- Show feature payload + XAI narrative
- Three voting buttons: "Agree (INSIDER)", "Disagree (LEGITIMATE)", "Unsure"
- After vote: reveal consensus score
- Write votes to arena_votes table, update consensus_score on anomaly_events

**Page 5: System Health (lowest priority)**
- Data source status grid (last update time, status, event count)
- Pipeline metrics: pending anomalies, avg processing time

**Streamlit config (`app.py`):**
```python
import streamlit as st
st.set_page_config(page_title="Sentinel", page_icon="🛡️", layout="wide")
st.title("🛡️ Sentinel: Prediction Market Surveillance")
# Sidebar navigation handled automatically by pages/ directory
```

**DONE_WHEN:**
- [ ] All 5 pages load without errors
- [ ] Case Detail page shows temporal gap chart + XAI narrative
- [ ] Live Monitor auto-refreshes and shows anomalies
- [ ] Arena voting updates database
- [ ] `streamlit run workstream_5_dashboard/app.py` works

---

## PHASE 5: Integration and Polish

> **Goal:** Wire everything together. Single command starts the full system.
> **Total time:** 2-3 hours
> **Who:** Integration Engineer + all agents for bug fixes.

---

### TASK 6.1: FastAPI Backend

```
AGENT: Integration Engineer
DEPENDS_ON: TASK 0.4, All Phase 1-3 tasks
ESTIMATED_TIME: 60 minutes
OUTPUTS: sentinel/workstream_6_integration/api.py
```

**Endpoints:**
```
GET  /api/anomalies              - List anomalies (query params: status, classification, limit, offset)
GET  /api/anomalies/{id}         - Single anomaly with full details
GET  /api/index                  - Sentinel Index cases
GET  /api/metrics                - FPR/FNR and system metrics
GET  /api/health                 - Data source health status
POST /api/arena/vote             - Submit vote: {anomaly_event_id, vote, voter_session}
GET  /api/arena/case             - Get next unvoted case
```

**DONE_WHEN:**
- [ ] All endpoints return valid JSON
- [ ] `/api/anomalies` supports filtering
- [ ] `/api/arena/vote` updates consensus_score
- [ ] CORS enabled for dashboard access
- [ ] `uvicorn workstream_6_integration.api:app --port 8000` works

---

### TASK 6.2: Evaluator

```
AGENT: Integration Engineer
DEPENDS_ON: TASK 0.4
ESTIMATED_TIME: 30 minutes
OUTPUTS: sentinel/workstream_6_integration/evaluator.py
```

```python
def compute_metrics(db) -> dict:
    """
    Compute confusion matrix from sentinel_index where outcome_verified = TRUE.
    Returns: {true_positives, false_positives, true_negatives, false_negatives, fpr, fnr, precision, recall}

    Logic:
    - predicted_suspicious = classification in ("INSIDER", "OSINT_EDGE")
    - actually_suspicious = consensus_score > 0.3
    """
    ...
```

**DONE_WHEN:**
- [ ] Computes FPR and FNR correctly from test data
- [ ] Returns all 8 metric fields
- [ ] Handles edge cases (no data, all same class)

---

### TASK 6.3: Main Orchestrator

```
AGENT: Integration Engineer
DEPENDS_ON: TASK 1.6, TASK 2.6, TASK 4.6, TASK 6.1
ESTIMATED_TIME: 60 minutes
OUTPUTS: sentinel/workstream_6_integration/orchestrator.py
```

```python
async def main():
    """
    1. init_database()
    2. Start concurrent tasks:
       - run_market_monitor(db)          # WS1 polling loop
       - run_osint_monitor(db)           # WS2 polling loop
       - run_ai_pipeline(db)             # WS4 batch processor (every 10s)
    3. Start FastAPI server on separate thread (port 8000)
    4. Handle graceful shutdown on SIGINT
    """
    ...
```

**CRITICAL: SQLite concurrent access.** Use WAL mode (already set in database.py). Add retry logic with `sqlite3.OperationalError` handling for write conflicts. Each async task should get its own connection via `get_connection()`.

**DONE_WHEN:**
- [ ] `python -m workstream_6_integration.orchestrator` starts all components
- [ ] All three polling loops run concurrently
- [ ] API server accessible at localhost:8000
- [ ] Ctrl+C cleanly shuts down everything
- [ ] No SQLite locking errors after 5 minutes of operation

---

### TASK 6.4: Seed Compelling Demo Data

```
AGENT: Integration Engineer
DEPENDS_ON: TASK 6.3
ESTIMATED_TIME: 60 minutes
OUTPUTS: sentinel/scripts/seed_demo.py
```

**Action:** Create 3-5 compelling, realistic cases that demonstrate Sentinel's value. These are the cases you walk through in a demo.

**Target demo cases:**
1. **Clear INSIDER:** Fresh wallet cluster places $50K on a niche geopolitical market 4 hours before a news break. No public signals exist before the trade. Temporal gap chart shows dramatic red zone.
2. **OSINT_EDGE:** Established wallet places a trade 2 hours after ADS-B data shows military aircraft movement, but 6 hours before major news outlets report it. Green zone with clear OSINT trail.
3. **FAST_REACTOR:** Multiple wallets trade within minutes of a Reuters wire breaking. Blue classification, clearly reactive.
4. **SPECULATOR:** Normal trading pattern, no correlation with events. Gray, boring, correctly classified.
5. **Borderline case:** Could be INSIDER or OSINT_EDGE. Good for the Arena voting demo.

**DONE_WHEN:**
- [ ] 5 demo cases in sentinel_index with full SAR reports
- [ ] At least one case has a dramatic temporal gap visualization
- [ ] Cases cover all 4 classification types
- [ ] Data is realistic and compelling for a live demo

---

### TASK 6.5: End-to-End Smoke Test

```
AGENT: Integration Engineer
DEPENDS_ON: All previous tasks
ESTIMATED_TIME: 30 minutes
```

**Run through this checklist manually:**

```
[ ] make init-db                              # Database creates successfully
[ ] make run                                  # Orchestrator starts all components
[ ] Wait 2 minutes                            # Let data flow in
[ ] curl localhost:8000/api/health             # API responds
[ ] curl localhost:8000/api/anomalies          # Returns anomaly data
[ ] Open new terminal: make run-dashboard      # Streamlit launches
[ ] Navigate to Live Monitor                   # Shows anomalies
[ ] Click an anomaly -> Case Detail            # Temporal gap chart renders
[ ] Navigate to Arena                          # Voting works
[ ] Navigate to Sentinel Index                 # Cases listed
[ ] Run for 10 minutes                         # No crashes
[ ] Ctrl+C both processes                      # Clean shutdown
```

**DONE_WHEN:**
- [ ] All checklist items pass
- [ ] System runs end-to-end for 10+ minutes without errors
- [ ] Demo flow is smooth: anomaly detected -> classified -> XAI narrative -> SAR report -> visible in dashboard

---

## Dependency Graph (Visual Summary)

```
PHASE 0 (Foundation)
  0.1 Repo Scaffold
  0.2 Requirements ---------> 0.3 Verify Keys
  0.4 Database Schema
  0.5 Makefile

PHASE 1 (Parallel Data Pipelines)
  TRACK A (Data Engineer):          TRACK B (OSINT Engineer):
  1.1 Polymarket Client             2.1 ChromaDB Vector Store
  1.2 Volume Detector               2.2 RSS Aggregator
  1.3 Price Detector                2.3 GDELT Client
  1.4 Fork pselamy Detectors        2.4 ACLED Client
  1.5 Anomaly Emitter               2.5 Market Correlator
  1.6 Main Loop                     2.6 OSINT Main Loop
  1.7 Backtest (low priority)

PHASE 2 (Features + Training)
  3.1 Feature Extraction  ---------> 3.4 Payload Formatter
  3.2 Spearman Clustering --------/
  3.3 Importance Weighting ------/
  4.1 Synthetic Data (start ASAP) -> 4.2 Submit Fine-Tune Job

PHASE 3 (AI Pipeline)
  4.3 Stage 1 Classifier
  4.4 Stage 2 XAI (needs ChromaDB from 2.1)
  4.5 Stage 3 SAR
  4.6 Pipeline Orchestrator

PHASE 4 (Dashboard)
  5.1 Mock Data
  5.2 Temporal Gap Chart (HIGHEST PRIORITY VIZ)
  5.3 Dashboard Pages (5 pages)

PHASE 5 (Integration)
  6.1 FastAPI Backend
  6.2 Evaluator
  6.3 Main Orchestrator
  6.4 Seed Demo Data
  6.5 End-to-End Smoke Test
```

---

## Critical Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Mistral API rate limits | Blocks WS4 entirely | Batch requests. Add exponential backoff. Monitor usage. |
| Polymarket CLOB API downtime | No live data | Cache recent data. Build backtest mode as fallback. |
| Fine-tuning job fails | No custom model | FALLBACK: Use finetuned mistral-small model. Already built into TASK 4.3. |
| ChromaDB sparse data | Weak XAI narratives | Manually seed 50-100 OSINT events. Run RSS aggregator for 30+ min before demo. |
| SQLite write conflicts | Crashes under concurrency | WAL mode + retry logic + separate connections per async task. |
| Missing API keys (OpenSky, VesselFinder) | Reduced OSINT coverage | Descope ADS-B/AIS from MVP. RSS + GDELT + ACLED sufficient for demo. |
| pselamy fork too complex | Delays WS1 | Write simplified detectors (see TASK 1.4 fallback). |

---

## Agent Assignment Summary

| Agent Role | Tasks | Phase | Estimated Hours |
|---|---|---|---|
| **Integration Engineer** | 0.1-0.5, 6.1-6.5 | 0, 5 | 4-5h |
| **Data Engineer** | 1.1-1.7 | 1 | 5-7h |
| **OSINT Engineer** | 2.1-2.6 | 1 | 4-6h |
| **ML Engineer** | 3.1-3.4 | 2 | 3-4h |
| **AI Engineer** | 4.1-4.6 | 2-3 | 5-7h |
| **Frontend Engineer** | 5.1-5.3 | 4 | 4-6h |

**Minimum viable team:** 2 agents (one handles Tracks A+ML+AI, one handles Track B+Frontend+Integration). The key constraint is API call latency, not coding speed.
