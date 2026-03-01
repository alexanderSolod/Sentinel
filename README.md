# SENTINEL

**AI-powered surveillance for prediction market integrity**

Built with Mistral AI | Mistral Worldwide Hackathon 2026

---

## The Problem

In January 2024, an anonymous wallet deposited $60,000 into a freshly created Polymarket account and bet everything on an Iranian military strike — **8 hours before anyone knew it was coming.** The wallet was 3 days old. Zero prior trades. Part of a 6-wallet cluster that all bet the same way. Return: **812%.**

This wasn't speculation. This was insider trading on a prediction market.

Sentinel would have caught it in real time.

## What Sentinel Does

Sentinel monitors prediction markets for information asymmetry. It watches every trade, correlates it against live OSINT signals, and classifies whether a trader is acting on **insider knowledge** or **superior public research.**

The core insight: **the time gap between a trade and the first public signal IS the evidence.** If someone bets big on an event hours before any news exists — that's a smoking gun.

```
Trade at 2:00 AM ──────── 8 hours ──────── News breaks 10:00 AM
       ^                                           ^
   No public signals exist                   OSINT signals appear
   BSS: 94/100 (suspicious)                 PES: 15/100 (unexplainable)
   Classification: INSIDER                   SAR Report generated
```

## Architecture

```
                         ┌─────────────────────────────────────────────┐
                         │              SENTINEL PIPELINE              │
                         └─────────────────────────────────────────────┘

  ┌──────────────┐       ┌──────────────┐       ┌──────────────────────┐
  │  POLYMARKET  │──────▶│   DETECTION  │──────▶│    OSINT CORRELATOR  │
  │  WebSocket   │       │              │       │                      │
  │  REST API    │       │ Volume Spikes│       │ RSS (Reuters, AP,    │
  └──────────────┘       │ Price Jumps  │       │      BBC, Bloomberg) │
                         │ Fresh Wallets│       │ GDELT Intelligence   │
                         │ DBSCAN Sniper│       │ GDACS Disasters      │
                         │   Clusters   │       │ ACLED Conflict       │
                         └──────┬───────┘       │ NASA FIRMS Fire      │
                                │               └──────────┬───────────┘
                                │                          │
                                ▼                          ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │                    FEATURE EXTRACTION (13 features)                 │
  │  wallet_age · trade_count · win_rate · position_size · z_score     │
  │  hours_before_news · osint_signals · cluster_member · is_sniper    │
  │  fresh_wallet · funding_risk · composite_risk · is_fresh           │
  └────────────────────────────┬────────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
  ┌──────────────────┐ ┌──────────────┐ ┌──────────────┐
  │  Random Forest   │ │  Game Theory │ │  Autoencoder  │
  │  300 estimators  │ │  Entropy +   │ │  Unsupervised │
  │  PCA reduction   │ │  Player Types│ │  Anomaly Det. │
  └────────┬─────────┘ └──────┬───────┘ └──────┬───────┘
           │                  │                │
           ▼                  ▼                ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │              5-GATE FALSE POSITIVE CASCADE                         │
  │  Statistical (20%) → RF (25%) → Autoencoder (15%)                 │
  │  → Game Theory (20%) → Mistral LLM (20%)                         │
  │  Dismiss < 0.25 ─── Escalate > 0.60                               │
  └────────────────────────────┬────────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│    STAGE 1     │  │    STAGE 2     │  │    STAGE 3     │
│    TRIAGE      │  │ DEEP ANALYSIS  │  │ SAR GENERATION │
│                │  │                │  │                │
│ Mistral Small  │  │ Mistral Large  │  │ Mistral Large  │
│ 4-class + BSS  │  │ Fraud Triangle │  │ Regulatory SAR │
│ + PES scores   │  │ Chain-of-Thought│ │ Evidence Report │
│                │  │ XAI Narrative  │  │                │
│  < 1 second    │  │  Conditional   │  │  Conditional   │
└────────────────┘  └────────────────┘  └────────────────┘
                               │
                               ▼
                    ┌────────────────────┐
                    │  SENTINEL INDEX    │
                    │  Case Database +   │
                    │  Arena Voting +    │
                    │  W&B Weave Traces  │
                    └────────────────────┘
```

**4 Mistral models working together:**
| Model | Role | Latency |
|-------|------|---------|
| **Mistral Small** | Stage 1 triage — 4-class classification with BSS/PES scoring | ~1s |
| **Mistral Large** | Stage 2 deep analysis — Fraud Triangle + chain-of-thought reasoning | ~30s |
| **Mistral Large** | Stage 3 SAR — Generates regulatory-grade Suspicious Activity Reports | ~45s |
| **Mistral Embed** | OSINT vector store — Semantic search across 150+ news sources via ChromaDB | ~2s |

## Key Features

- **Temporal Gap Detection** — Measures the exact time between a trade and the first public signal. Trades before news = suspicious. Trades after news = legitimate.

- **Game Theory Behavioral Analysis** — Maps trader behavior to player types using entropy analysis across 5 dimensions (timing, markets, win rates, positions, hours).

- **DBSCAN Sniper Clustering** — Detects coordinated wallet groups entering markets within minutes of creation. The Iran Strike case had a 6-wallet cluster.

- **5-Gate False Positive Cascade** — Statistical → Random Forest → Autoencoder → Game Theory → Mistral LLM. Each gate has a weighted vote. Cases below 0.25 are dismissed early; above 0.60 escalate to deep analysis.

- **Fraud Triangle Mapping** — Classic fraud framework (Pressure, Opportunity, Rationalization) applied to every flagged case via Mistral Large chain-of-thought.

- **Real-time OSINT Correlation** — Aggregates 5 intelligence sources (RSS, GDELT, GDACS, ACLED, NASA FIRMS) and correlates them to markets using Mistral Embed semantic search.

- **Human-in-the-Loop Arena** — Community voting interface where reviewers validate or dispute AI classifications with confidence levels.

- **W&B Weave Observability** — Full tracing on all 3 AI pipeline stages for decision auditability.

## Quick Start

```bash
# Clone and install
git clone <repo-url> && cd mistral-monitor
pip install -r requirements.txt

# Configure
cp ../.env.template .env
# Edit .env → add MISTRAL_API_KEY (required)
# Optional: WANDB_API_KEY, ACLED_ACCESS_TOKEN, NASA_FIRMS_API_KEY

# Initialize database with demo data
python main.py init

# Launch dashboard
python main.py dashboard
```

Open [http://localhost:8501](http://localhost:8501) and explore the 5-page dashboard.

### Run the AI Pipeline

```bash
# Mock data (no external APIs needed except Mistral)
python main.py pipeline --mock

# Live Polymarket data + real OSINT
python main.py pipeline --live

# Real-time trade monitoring
python main.py monitor --mock 20
```

## The Four Classifications

Sentinel classifies every flagged trade into one of four categories using a dual-score system:

| Classification | BSS | PES | Description |
|---------------|-----|-----|-------------|
| **INSIDER** | High (>70) | Low (<30) | Trade based on material non-public information. Fresh wallet, no public signals, high conviction bet. |
| **OSINT_EDGE** | Low (<30) | High (>70) | Legitimate research edge. Established wallet, public signals existed before trade. |
| **FAST_REACTOR** | Low (<30) | High (>70) | Quick reaction to breaking news. Trade placed minutes after public announcement. |
| **SPECULATOR** | Low (<30) | Mid (40-60) | Normal speculation. No timing correlation with news events. |

**BSS** = Behavioral Suspicion Score (0-100): How suspicious is the wallet's behavior?
**PES** = Public Explainability Score (0-100): Could public information explain this trade?

The 2x2 grid of BSS vs PES is the key visualization — INSIDER cases cluster in the high-BSS, low-PES quadrant.

## Dashboard Pages

### 1. Live Monitor
Real-time anomaly feed with classification badges, gate funnel visualization, and evidence packet summaries.

### 2. Case Detail
**The money shot.** Temporal gap timeline showing:
- Red diamond: The suspicious trade
- Green circles: OSINT signals (news, reports, alerts)
- Orange star: Major news break
- Red shaded zone: The information gap (no public info existed)

Plus: 2x2 classification grid, Fraud Triangle breakdown, full XAI narrative, and SAR report.

### 3. Sentinel Index
Searchable database of all flagged cases with filtering by classification, severity, and market. Export to CSV.

### 4. Arena
Vote on AI classifications. Agree, disagree, or flag as uncertain. Consensus scores drive evaluation metrics.

### 5. System Health
Model drift tracking, gate throughput analysis, NLP relevance heatmap, and pipeline performance stats.

## Commands Reference

| Command | Description |
|---------|-------------|
| `python main.py init` | Initialize database + seed demo data |
| `python main.py dashboard` | Launch Streamlit dashboard |
| `python main.py pipeline --mock` | Run pipeline with synthetic data |
| `python main.py pipeline --live` | Run pipeline with live Polymarket data |
| `python main.py pipeline --backfill` | Reprocess existing DB anomalies |
| `python main.py monitor --mock [n]` | Process n mock trades in real-time |
| `python main.py monitor --live` | WebSocket stream from Polymarket |
| `python main.py api` | Launch FastAPI backend (port 8000) |
| `python main.py metrics` | Print evaluation metrics |
| `python -m src.classification.pipeline` | Test classification pipeline directly |
| `python -m src.classification.finetuning --generate-only` | Generate fine-tuning training data |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Classification | Mistral Small, Mistral Large, Mistral Embed |
| Vector Search | ChromaDB with Mistral Embed |
| ML Detection | scikit-learn (Random Forest, DBSCAN, PCA) |
| Anomaly Detection | Custom autoencoder (PyTorch-style, numpy impl) |
| Dashboard | Streamlit + Plotly |
| API | FastAPI + Uvicorn |
| Database | SQLite with WAL mode |
| OSINT Sources | RSS, GDELT, GDACS, ACLED, NASA FIRMS |
| Observability | W&B Weave |
| Data | Polymarket CLOB API + WebSocket |

## Project Structure

```
mistral-monitor/
├── main.py                          # CLI entry point (7 commands)
├── run_dashboard.py                 # Streamlit launcher
├── requirements.txt
├── src/
│   ├── classification/
│   │   ├── stage1_triage.py         # Mistral Small — 4-class classifier
│   │   ├── stage2_magistral.py      # Mistral Large — Fraud Triangle + XAI
│   │   ├── stage3_sar.py            # Mistral Large — SAR generation
│   │   ├── pipeline.py              # 3-stage orchestrator
│   │   ├── finetuning.py            # Fine-tuning data gen + job submission
│   │   └── evaluation.py            # FPR/FNR/confusion matrix
│   ├── detection/
│   │   ├── anomaly_detector.py      # Volume/price/fresh wallet detection
│   │   ├── wallet_profiler.py       # Trade history + funding chain
│   │   ├── cluster_analysis.py      # DBSCAN sniper clustering
│   │   ├── rf_classifier.py         # Random Forest with PCA
│   │   ├── game_theory.py           # Behavioral entropy analysis
│   │   ├── features.py              # 13-feature extraction
│   │   ├── fp_gate.py               # 5-gate false positive cascade
│   │   └── autoencoder.py           # Unsupervised anomaly detection
│   ├── osint/
│   │   ├── sources.py               # GDELT, GDACS, ACLED, FIRMS clients
│   │   ├── rss_aggregator.py        # 12-feed RSS aggregation
│   │   ├── vector_store.py          # ChromaDB + Mistral Embed
│   │   ├── correlator.py            # Market-OSINT temporal matching
│   │   └── text_analyzer.py         # NLP relevance scoring
│   ├── pipeline/
│   │   └── evidence_correlator.py   # Real-time trade processing
│   ├── data/
│   │   ├── database.py              # SQLite schema (8 tables)
│   │   ├── polymarket_client.py     # Polymarket API + rate limiting
│   │   ├── websocket_handler.py     # Real-time trade WebSocket
│   │   └── mock_data.py             # Demo data generator
│   ├── dashboard/
│   │   └── app.py                   # 5-page Streamlit app (932 lines)
│   └── api/
│       └── main.py                  # FastAPI REST endpoints
├── data/
│   ├── sentinel.db                  # SQLite database
│   └── finetuning/                  # Generated training data
└── tests/                           # 13 test modules
```

## Gold-Standard Cases

These real, documented events are embedded in Sentinel's training data:

| Case | Wallet | Classification | Evidence |
|------|--------|---------------|----------|
| **Iran Strike (Jan 2024)** | Wallet A — 3-day-old, $60K, 6-wallet cluster | INSIDER (BSS: 94) | Trade 8h before news, zero public signals, 812% return |
| **Iran Strike (Jan 2024)** | Vivaldi007 — 120-day-old, 47 trades, 62% win rate | OSINT_EDGE (BSS: 12) | Multiple public signals existed: satellite imagery, diplomatic breakdown, analyst commentary |
| **Axiom/ZachXBT (2024)** | predictorxyz — 5-day-old, $65.8K at 13.8% odds | INSIDER (BSS: 91) | No public signals pointed to Axiom specifically. Confirmed by ZachXBT. 625% return |

## Fine-Tuning Pipeline

Sentinel includes a complete fine-tuning pipeline for creating a custom Mistral classifier:

```bash
# Generate 500 training examples (25% INSIDER, 25% OSINT_EDGE, 15% FAST_REACTOR, 15% SPECULATOR, 20% Hard)
python -m src.classification.finetuning --generate-only

# Submit fine-tuning job (requires Mistral fine-tuning access)
python -m src.classification.finetuning

# Deploy: set SENTINEL_FINETUNED_MODEL=<model_id> in .env
```

Training data includes 3 gold-standard examples from real events and 497 synthetic examples with controlled difficulty distribution.

## API Endpoints

```
GET  /api/anomalies          List/filter anomalies
GET  /api/cases/{id}         Get case details + evidence
GET  /api/index              Query Sentinel Index
POST /api/vote               Submit Arena vote
GET  /api/health             System health check
```

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `MISTRAL_API_KEY` | Yes | Powers all 4 AI models |
| `WANDB_API_KEY` | No | W&B Weave tracing |
| `ACLED_ACCESS_TOKEN` | No | Armed conflict OSINT |
| `NASA_FIRMS_API_KEY` | No | Fire detection OSINT |
| `SENTINEL_FINETUNED_MODEL` | No | Use fine-tuned classifier |

## Attribution

Built on the shoulders of:
- [polymarket-insider-tracker](https://github.com/pselamy/polymarket-insider-tracker) (MIT) — Rate limiting, wallet detection, cluster analysis patterns
- [worldmonitor](https://github.com/koala73/worldmonitor) — OSINT source integrations, threat classification

Data sources: [Polymarket](https://polymarket.com), [GDELT](https://www.gdeltproject.org/), [GDACS](https://www.gdacs.org/), [ACLED](https://acleddata.com/), [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/)

---

*Built for the [Mistral AI Worldwide Hackathon 2026](https://worldwide-hackathon.mistral.ai/)*
