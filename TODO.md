# Sentinel Implementation Status

> AI-powered surveillance system for prediction market integrity
> **Mode: 48-Hour Hackathon | Solo Developer**

---

## Current Status: MVP FUNCTIONAL

The core demo pipeline is working. Dashboard can be launched with mock data.

```bash
# Quick start
cd mistral-monitor
pip install -r requirements.txt
cp ../.env.template .env  # Fill in MISTRAL_API_KEY
python main.py init       # Initialize DB + seed demo data
python main.py dashboard  # Launch Streamlit
```

---

## Completed

### Phase 0: Foundation
- [x] Project structure (`src/{data,detection,classification,osint,dashboard,api}`)
- [x] `requirements.txt` with all dependencies
- [x] `.env.template` with all API keys documented
- [x] SQLite database schema with WAL mode (`src/data/database.py`)
  - `anomaly_events`, `osint_events`, `wallet_profiles`, `sentinel_index`, `arena_votes`
- [x] `main.py` entry point with `init` and `dashboard` commands
- [x] `CLAUDE.md` project guidance
- [x] `ATTRIBUTION.md` for adapted open source code

### Phase 1: Data Pipelines

#### Polymarket Client (`src/data/polymarket_client.py`)
- [x] CLOB API client with rate limiting (token bucket, 10 req/s)
- [x] Exponential backoff retry decorator
- [x] Methods: `get_markets()`, `get_market()`, `get_prices()`, `get_trades()`
- [x] Adapted from `polymarket-insider-tracker` (MIT)

#### Detection Engine (`src/detection/anomaly_detector.py`)
- [x] VolumeDetector (z-score based, >3x baseline)
- [x] PriceDetector (>15 percentage point moves)
- [x] FreshWalletDetector with confidence scoring
- [x] Adapted from `polymarket-insider-tracker` (MIT)

#### Wallet Profiler (`src/detection/wallet_profiler.py`)
- [x] Trade history aggregation
- [x] Win rate calculation
- [x] Funding chain analysis with known address registry
- [x] Risk flag calculation
- [x] Adapted from `polymarket-insider-tracker` (MIT)

#### Cluster Analysis (`src/detection/cluster_analysis.py`)
- [x] DBSCAN sniper clustering (with sklearn fallback)
- [x] Market entry tracking relative to market creation time
- [x] Composite risk scoring with multi-signal bonuses
- [x] Cluster membership tracking and confidence scoring
- [x] Adapted from `polymarket-insider-tracker` (MIT)

#### WebSocket Handler (`src/data/websocket_handler.py`)
- [x] Real-time trade streaming via WebSocket
- [x] Automatic reconnection with exponential backoff
- [x] Event/market filtering
- [x] Connection state management
- [x] Mock stream for testing
- [x] Adapted from `polymarket-insider-tracker` (MIT)

#### OSINT Pipeline
- [x] RSS Aggregator (`src/osint/rss_aggregator.py`)
- [x] GDELT client with topic queries (`src/osint/sources.py`)
- [x] GDACS disaster alerts client
- [x] ACLED armed conflict client (requires API key)
- [x] NASA FIRMS fire detection client (requires API key)
- [x] Threat classification (CRITICAL/HIGH/MEDIUM/LOW/INFO)
- [x] OsintAggregator combining all sources
- [x] Adapted from `worldmonitor`

### Phase 3: AI Classification Pipeline

#### Stage 1: Triage (`src/classification/stage1_triage.py`)
- [x] Fast 4-class classifier with Mistral Small
- [x] Few-shot prompting with 4 examples
- [x] Outputs: classification, BSS, PES, confidence, reasoning
- [x] Rule-based fallback when API unavailable

#### Stage 2: Deep Analysis (`src/classification/stage2_magistral.py`)
- [x] Chain-of-thought reasoning with Magistral Medium
- [x] Fraud Triangle analysis (Pressure, Opportunity, Rationalization)
- [x] Temporal gap analysis
- [x] XAI narrative generation
- [x] Rule-based fallback when API unavailable

#### Stage 3: SAR Generation (`src/classification/stage3_sar.py`)
- [x] Suspicious Activity Report generation with Mistral Large
- [x] Structured report format with executive summary, timeline, recommendation
- [x] Template-based fallback when API unavailable

#### Pipeline Orchestrator (`src/classification/pipeline.py`)
- [x] `SentinelPipeline.process_anomaly()` wiring all 3 stages
- [x] Conditional deep analysis for BSS >= 40 or INSIDER/OSINT_EDGE
- [x] `__main__` test harness

### Phase 4: Dashboard (`src/dashboard/app.py`)
- [x] Streamlit app with 5 pages
- [x] **Live Monitor**: Anomaly feed with filtering and stats
- [x] **Case Detail**: Temporal gap chart (THE key visualization)
- [x] **Sentinel Index**: Searchable case database
- [x] **Arena**: Human-in-the-loop voting interface
- [x] **System Health**: Pipeline metrics and status
- [x] 2x2 Classification grid (BSS vs PES)
- [x] `run_dashboard.py` launcher

### Phase 4.1: Mock Data (`src/data/mock_data.py`)
- [x] 10 compelling demo cases
- [x] All 4 classification types covered
- [x] Realistic wallet profiles
- [x] OSINT events for temporal gap visualization
- [x] `seed_demo_data()` function

---

## Remaining Work

### Priority 1: Integration (High Impact)

- [x] **ChromaDB Vector Store** (`src/osint/vector_store.py`) - DONE
  - Embed OSINT events using Mistral Embed (fallback: MiniLM)
  - Similarity search for RAG context
  - Used by Stage 2 for relevant OSINT retrieval

- [x] **Market-OSINT Correlator** (`src/osint/correlator.py`) - DONE
  - Match OSINT events to related markets by keyword/embedding similarity
  - Calculate temporal gap (trade_time - osint_time)
  - Tag events with market_ids they could impact
  - Information asymmetry classification (TRADE_BEFORE_INFO, TRADE_AFTER_INFO, etc.)

- [x] **Live Pipeline Runner** (update `main.py pipeline`) - DONE
  - Wire: Data ingestion → Detection → OSINT Correlation → Classification → Database
  - CLI flags: `--mock`, `--live`, `--backfill`
  - Process real anomalies through the AI pipeline
  - Full fallback chain when API unavailable

### Priority 2: Enhanced Analysis

- [x] **Wallet Profiler** (`src/detection/wallet_profiler.py`) - DONE
  - Trade history aggregation
  - Win rate calculation
  - Funding chain analysis (where did initial funds come from?)

- [x] **DBSCAN Cluster Analysis** (`src/detection/cluster_analysis.py`) - DONE
  - Detect coordinated wallet behavior
  - Cluster membership assignment
  - Suspicious cluster flagging

- [x] **Feature Extraction Module** (`src/detection/features.py`) - DONE
  - 13-feature vector: wallet age, trade count, win rate, position size %, hours before news, z-score, cluster membership, sniper flag, OSINT signal count, fresh wallet, funding risk, composite risk score
  - `FeatureExtractor.extract()` → `FeatureVector` with `.to_classifier_input()`, `.to_array()`, `.suspicion_heuristic`
  - Integrated into `SentinelPipeline.process_anomaly()` before Stage 1 triage
  - Suspicion heuristic for pre-classification prioritisation

### Priority 3: API Backend

- [x] **FastAPI Backend** (`src/api/main.py`) - DONE
  - `GET /api/anomalies` - List/filter anomalies
  - `GET /api/cases/{id}` - Get case details
  - `GET /api/index` - Query Sentinel Index
  - `POST /api/vote` - Submit Arena vote
  - `GET /api/health` - System health check

### Priority 4: Production Features

- [x] **Real-time Monitoring** (`main.py monitor`) - DONE
  - `--mock` mode: Mock trade stream for demo/testing
  - `--live` mode: Real-time WebSocket stream from Polymarket
  - Uses `EvidenceCorrelator` for full enrichment pipeline per trade
  - Wallet profiling + DBSCAN clustering + OSINT correlation + AI classification
  - Evidence packets persisted to database

- [x] **Fine-tuning Pipeline** (`src/classification/finetuning.py`) - DONE
  - Generate ~500 synthetic training examples (JSONL format)
  - 3 gold-standard examples from real events (Iran Strike, Axiom/ZachXBT)
  - Distribution: 25% INSIDER, 25% OSINT_EDGE, 15% FAST_REACTOR, 15% SPECULATOR, 20% Hard
  - Submit fine-tuning job to Mistral API
  - Poll for job completion
  - Stage 1 updated to use fine-tuned model via `SENTINEL_FINETUNED_MODEL` env var

  ```bash
  # Generate data only
  python -m src.classification.finetuning --generate-only --n-examples 500

  # Full pipeline (submit job)
  python -m src.classification.finetuning

  # Check job status
  python -m src.classification.finetuning --check-job <job_id>
  ```

- [x] **Evaluation Metrics** - DONE
  - Calculate FPR/FNR
  - Confusion matrix
  - Arena consensus accuracy

### Nice to Have

- [x] W&B Weave tracing for AI decisions - DONE
- [ ] Voice alerts with ElevenLabs
- [ ] Advanced OSINT: ADS-B flight tracking, social sentiment
- [ ] Export reports to PDF

---

## API Keys Status

| Service | Required | Status |
|---------|----------|--------|
| Mistral AI | Yes | Needed for classification |
| Polymarket | No | Public API works |
| GDELT | No | Public API (may rate limit) |
| GDACS | No | Public API |
| ACLED | Optional | Needed for conflict data |
| NASA FIRMS | Optional | Needed for fire detection |

---

## Known Issues

1. **GDELT rate limiting**: API returns 429 when hit too frequently. Graceful fallback to empty results is implemented.

2. **GDACS availability**: Occasionally returns 503. Graceful fallback implemented.

3. **Dashboard requires init**: Must run `python main.py init` before launching dashboard.

---

## File Structure

```
mistral-monitor/
├── main.py                    # Entry point
├── run_dashboard.py           # Streamlit launcher
├── requirements.txt           # Dependencies
├── CLAUDE.md                  # AI guidance
├── ATTRIBUTION.md             # Open source credits
├── TODO.md                    # This file
├── data/
│   └── sentinel.db            # SQLite database (created by init)
└── src/
    ├── data/
    │   ├── database.py        # Schema + helpers
    │   ├── mock_data.py       # Demo data generator
    │   └── polymarket_client.py  # Polymarket API
    ├── detection/
    │   └── anomaly_detector.py   # Volume/price/wallet detection
    ├── classification/
    │   ├── stage1_triage.py   # Fast classifier
    │   ├── stage2_magistral.py # Deep analysis
    │   ├── stage3_sar.py      # SAR generation
    │   └── pipeline.py        # Orchestrator
    ├── osint/
    │   ├── sources.py         # ACLED, GDELT, GDACS, FIRMS
    │   └── rss_aggregator.py  # RSS + GDELT wrapper
    ├── dashboard/
    │   └── app.py             # Streamlit UI
    └── api/
        └── (empty - FastAPI TODO)
```

---

## Quick Test Commands

```bash
# Test database
python -c "from src.data.database import init_schema; init_schema()"

# Test classification pipeline
python -m src.classification.pipeline

# Test OSINT sources (may hit rate limits)
python -m src.osint.sources

# Test Polymarket client
python -m src.data.polymarket_client

# Launch dashboard
streamlit run run_dashboard.py
```
