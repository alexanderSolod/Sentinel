# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sentinel is an AI-powered surveillance system for prediction market integrity. It detects information asymmetry in prediction markets (specifically Polymarket), distinguishes insider trading from legitimate OSINT research, and maintains a curated database of potential insider trading cases.

## Commands

```bash
# Setup
pip install -r requirements.txt
cp ../.env.template .env  # Then fill in API keys

# Initialize database with demo data
python main.py init

# Launch dashboard
python main.py dashboard
# Or directly: streamlit run run_dashboard.py

# Run full pipeline (detection + OSINT correlation + classification)
python main.py pipeline --mock      # Mock data end-to-end
python main.py pipeline --live      # Live Polymarket data
python main.py pipeline --backfill  # Reprocess DB anomalies

# Real-time monitoring (continuous trade processing)
python main.py monitor --mock       # Mock trades for demo
python main.py monitor --mock 50    # Custom number of mock trades
python main.py monitor --live       # Live WebSocket stream (Ctrl+C to stop)

# Run classification pipeline on test data
python -m src.classification.pipeline

# Fine-tuning pipeline
python -m src.classification.finetuning --generate-only  # Generate training data
python -m src.classification.finetuning                   # Submit fine-tuning job
python -m src.classification.finetuning --check-job <id>  # Check job status

# Test individual modules
python -m src.data.polymarket_client
python -m src.detection.anomaly_detector
python -m src.osint.sources
python -m src.osint.vector_store
python -m src.osint.correlator
```

## Architecture

### Classification Pipeline (3-stage)

The core AI pipeline processes anomalies through three stages:

1. **Stage 1 - Triage** (`src/classification/stage1_triage.py`): Fast 4-class classification using Mistral Small with few-shot prompting. Outputs BSS (Behavioral Suspicion Score) and PES (Public Explainability Score).

2. **Stage 2 - Deep Analysis** (`src/classification/stage2_magistral.py`): Chain-of-thought reasoning with Fraud Triangle analysis (Pressure, Opportunity, Rationalization). Only runs for INSIDER/OSINT_EDGE cases or BSS >= 40.

3. **Stage 3 - SAR Generation** (`src/classification/stage3_sar.py`): Generates Suspicious Activity Reports for high-suspicion cases.

Pipeline orchestration: `src/classification/pipeline.py` → `SentinelPipeline.process_anomaly()`

### Fine-Tuning Pipeline

`src/classification/finetuning.py` handles model fine-tuning:

1. **Data Generation**: Creates 500 training examples with distribution:
   - 25% INSIDER, 25% OSINT_EDGE, 15% FAST_REACTOR, 15% SPECULATOR, 20% Hard/Ambiguous
   - Includes 3 gold-standard examples from real events

2. **Job Submission**: Uploads JSONL to Mistral API and submits fine-tuning job

3. **Deployment**: Set `SENTINEL_FINETUNED_MODEL=<model_id>` in .env to use fine-tuned model

### Four Classification Types

- **INSIDER**: Trade based on material non-public information (high BSS, low PES)
- **OSINT_EDGE**: Trade based on superior public intelligence gathering (low BSS, high PES)
- **FAST_REACTOR**: Quick reaction to breaking news (trade after news)
- **SPECULATOR**: Normal speculation with no edge

### Database Schema

SQLite with WAL mode (`src/data/database.py`). Core tables:
- `anomaly_events`: Raw trade anomalies with z-scores and classifications
- `osint_events`: OSINT signals with timestamps and embeddings
- `wallet_profiles`: Wallet history, win rates, cluster membership
- `sentinel_index`: Curated case database with SARs and consensus scores
- `arena_votes`: Human-in-the-loop voting records

### OSINT Sources

`src/osint/sources.py` integrates multiple intelligence APIs:
- **GDELT**: News with tone analysis (public, no key)
- **GDACS**: Disaster alerts (public, no key)
- **ACLED**: Armed conflict data (requires `ACLED_ACCESS_TOKEN`)
- **NASA FIRMS**: Fire detection (requires `NASA_FIRMS_API_KEY`)

Threat classification uses keyword matching with levels: CRITICAL, HIGH, MEDIUM, LOW, INFO.

### OSINT Vector Store & Correlator

`src/osint/vector_store.py` - ChromaDB-backed vector store:
- **VectorStore**: Embeds OSINT events using Mistral Embed (fallback: MiniLM)
- `search()`, `search_by_market()`, `search_time_window()` for similarity search
- `add_events()` / `add_osint_objects()` for ingestion
- Used by Stage 2 for RAG context

`src/osint/correlator.py` - Market-OSINT correlation:
- **MarketCorrelator**: Matches OSINT events to markets via semantic + keyword search
- Computes temporal gaps (trade_time - osint_time)
- `enrich_anomaly()` adds osint_signals_before_trade, hours_before_news, information_asymmetry
- Information asymmetry patterns: TRADE_BEFORE_INFO, TRADE_AFTER_INFO, NO_SIGNALS, MIXED_SIGNALS

### Feature Extraction

`src/detection/features.py` - Standardised feature vectors for classification:
- **FeatureExtractor**: Extracts 13-feature vectors from raw anomaly data
- **FeatureVector**: Dataclass with `.to_classifier_input()`, `.to_array()`, `.suspicion_heuristic`
- Features: wallet_age_days, wallet_trade_count, wallet_win_rate, is_fresh_wallet, funding_risk, trade_size_usd, position_size_pct, z_score, hours_before_news, osint_signal_count, cluster_member, is_sniper, composite_risk_score
- Integrated into pipeline: `FeatureExtractor.extract()` runs before Stage 1 triage

### Detection Module

`src/detection/anomaly_detector.py` contains:
- **VolumeDetector**: Z-score based volume spike detection (>3x baseline)
- **PriceDetector**: Price jump detection (>15 percentage points)
- **FreshWalletDetector**: Confidence scoring for fresh wallets (nonce ≤5, age <48h)

`src/detection/wallet_profiler.py` contains:
- **WalletProfiler**: Trade history aggregation, win rate calculation
- **FundingChain**: Funding chain tracing with known address registry (CEX, DEX, mixers)
- Risk flag calculation (fresh_wallet, high_win_rate, mixer_funded)

`src/detection/cluster_analysis.py` contains:
- **SniperDetector**: DBSCAN clustering for coordinated wallet behavior
- **CompositeRiskScorer**: Weighted signal aggregation with multi-signal bonuses
- Market entry tracking relative to market creation time

`src/data/websocket_handler.py` contains:
- **TradeStreamHandler**: Real-time WebSocket trade streaming
- Automatic reconnection with exponential backoff
- Event/market filtering, connection state management

### Real-time Evidence Correlator

`src/pipeline/evidence_correlator.py` - Live trade processing pipeline:
- **EvidenceCorrelator**: Async pipeline that processes each trade through:
  1. Wallet profiling (trade history, win rate, risk flags)
  2. DBSCAN cluster analysis (coordinated wallet detection)
  3. OSINT correlation (temporal gap to public signals)
  4. AI classification (Stage 1-3 pipeline)
  5. Evidence packet persistence to database
- `run_live()`: Connects to Polymarket WebSocket via TradeStreamHandler
- `run_mock(num_trades, delay_seconds)`: Mock trades for demo/testing
- `process_trade()`: Full enrichment per trade → evidence packet
- `compute_temporal_gap_score()`: Suspicion scoring from trade-vs-signal timing
- Correlation score: weighted composite of wallet risk, cluster confidence, temporal gap

### Dashboard

Streamlit app (`src/dashboard/app.py`) with pages:
- Live Monitor: Real-time anomaly feed
- Case Detail: Temporal gap chart (key visualization showing trade vs. news timing)
- Sentinel Index: Searchable case database
- Arena: Human-in-the-loop voting interface
- System Health: API status and metrics

## Key Patterns

- Rate limiting uses token bucket pattern (10 req/s for Polymarket)
- Retry logic uses exponential backoff
- All API clients have rule-based fallbacks when API unavailable
- Cache TTLs aligned with upstream refresh rates (ACLED: 15min, GDELT: 5min)

## Environment Variables

Required:
- `MISTRAL_API_KEY`: For classification pipeline

Optional OSINT sources:
- `ACLED_ACCESS_TOKEN`: Armed conflict data
- `NASA_FIRMS_API_KEY`: Fire detection
