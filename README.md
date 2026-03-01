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

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm (for the dashboard UI)
- A [Mistral AI API key](https://console.mistral.ai/)

### Installation

```bash
# Clone the repository
git clone <repo-url> && cd mistral-monitor

# Install Python dependencies
pip install -r requirements.txt

# Install dashboard UI dependencies
cd ui && npm install && cd ..

# Configure environment variables
cp .env.template .env
# Edit .env and add your MISTRAL_API_KEY (required)
```

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `MISTRAL_API_KEY` | **Yes** | Powers all 4 AI models (classification, embedding) |
| `ACLED_ACCESS_TOKEN` | No | Armed conflict OSINT data (free, [register here](https://acleddata.com/)) |
| `NASA_FIRMS_API_KEY` | No | Fire/thermal detection OSINT ([register here](https://firms.modaps.eosdis.nasa.gov/)) |
| `WANDB_API_KEY` | No | W&B Weave tracing for AI pipeline observability |
| `SENTINEL_FINETUNED_MODEL` | No | Use a fine-tuned Mistral model for Stage 1 triage |
| `SENTINEL_API_KEY` | No | Protect the vote endpoint (if unset, runs in open demo mode) |
| `DATABASE_PATH` | No | Custom SQLite database path (default: `./data/sentinel.db`) |

---

## Running the Project

### Quick Demo (Fastest Way to See Everything)

```bash
# 1. Seed the database with demo data
python main.py init

# 2. Start the API server (keep running in background)
python main.py api

# 3. In a new terminal, start the dashboard
cd ui && npm run dev
```

Open **http://localhost:5173** to see the dashboard with pre-seeded demo data.

### Running with Live Data

There are two ways to populate the dashboard with real data from Polymarket:

#### Option A: Pipeline Mode (One-Shot Analysis)

Best for: Getting 5 fully classified cases with SAR reports quickly.

```bash
# Terminal 1: API server
python main.py api

# Terminal 2: Dashboard
cd ui && npm run dev

# Terminal 3: Run the live pipeline
python main.py pipeline --live
```

This fetches the top 20 Polymarket markets by volume, gathers OSINT from all sources (RSS, GDELT, GDACS, ACLED, NASA FIRMS), correlates the top 5 markets with intelligence signals, and classifies each through the 3-stage AI pipeline. Results are saved to the database and appear in the dashboard on page refresh.

#### Option B: Monitor Mode (Continuous Real-Time Stream)

Best for: Watching trades flow in continuously.

```bash
# Terminal 1: API server
python main.py api

# Terminal 2: Dashboard
cd ui && npm run dev

# Terminal 3: Live trade stream
python main.py monitor --live
```

This connects to Polymarket's WebSocket and processes each trade through the full enrichment pipeline (wallet profiling, cluster analysis, OSINT correlation, AI classification). Press Ctrl+C to stop. Evidence packets appear in the dashboard's Live Monitor page.

### Running with Mock Data (No External APIs Needed)

For development, demos, or when you don't want to hit external APIs:

```bash
# Mock pipeline: 4 synthetic anomalies through full classification
python main.py pipeline --mock

# Mock monitor: N mock trades with 0.25s delay each
python main.py monitor --mock        # 20 trades (default)
python main.py monitor --mock 50     # 50 trades
python main.py monitor --mock 200    # 200 trades
```

Both mock modes still require `MISTRAL_API_KEY` since they run through the AI classification pipeline.

---

## All Commands

### Core Commands

| Command | Description | Requires |
|---------|-------------|----------|
| `python main.py init` | Initialize SQLite database and seed with demo data | Nothing |
| `python main.py api` | Start FastAPI server on http://localhost:8000 | Nothing |
| `python main.py metrics` | Print evaluation metrics (FPR/FNR/confusion matrix/consensus) | Seeded DB |

### Pipeline Commands

| Command | Description | Requires |
|---------|-------------|----------|
| `python main.py pipeline --mock` | Process 4 synthetic anomalies through the full pipeline | `MISTRAL_API_KEY` |
| `python main.py pipeline --live` | Fetch live Polymarket markets, gather OSINT, classify top 5 | `MISTRAL_API_KEY` |
| `python main.py pipeline --backfill` | Reprocess the last 100 DB anomalies through the classifier | `MISTRAL_API_KEY` |

### Monitor Commands

| Command | Description | Requires |
|---------|-------------|----------|
| `python main.py monitor --mock` | Generate 20 mock trades through real-time pipeline | `MISTRAL_API_KEY` |
| `python main.py monitor --mock N` | Generate N mock trades (e.g., `--mock 100`) | `MISTRAL_API_KEY` |
| `python main.py monitor --live` | Connect to Polymarket WebSocket, process live trades (Ctrl+C to stop) | `MISTRAL_API_KEY` |

### Dashboard Commands

| Command | Description | URL |
|---------|-------------|-----|
| `cd ui && npm run dev` | Start React dashboard (development mode with hot reload) | http://localhost:5173 |
| `cd ui && npm run build` | Build production bundle to `ui/dist/` | — |
| `cd ui && npm run preview` | Preview production build locally | http://localhost:4173 |
| `python main.py dashboard` | Start legacy Streamlit dashboard | http://localhost:8501 |

### Classification Pipeline Commands

| Command | Description |
|---------|-------------|
| `python -m src.classification.pipeline` | Test classification pipeline on sample data |
| `python -m src.classification.finetuning --generate-only` | Generate 500 training examples for fine-tuning |
| `python -m src.classification.finetuning` | Submit fine-tuning job to Mistral API |
| `python -m src.classification.finetuning --check-job <id>` | Check fine-tuning job status |

### Module Test Commands

| Command | Description |
|---------|-------------|
| `python -m src.data.polymarket_client` | Test Polymarket API connection |
| `python -m src.detection.anomaly_detector` | Test anomaly detection module |
| `python -m src.osint.sources` | Test OSINT source integrations |
| `python -m src.osint.vector_store` | Test ChromaDB vector store |
| `python -m src.osint.correlator` | Test market-OSINT correlation |

---

## Dashboard Pages

The React dashboard (`ui/`) provides 5 pages accessible from the sidebar:

### 1. Live Monitor (`/`)
Real-time anomaly feed with KPI cards (active anomalies, insider cases, cases under review, evidence packets, total cases), a scrollable anomaly list with classification badges and BSS/PES score bars, and an evidence packets table with correlation scores.

### 2. Case Detail (`/case/:caseId`)
**The money shot.** Deep-dive into a single case with:
- **Temporal Gap Chart** (hero visualization) — horizontal timeline showing trade timing vs. OSINT signals, with suspicious gaps shaded red
- **Wallet Profile** — address, age, trade count, win rate, risk score
- **Classification Quadrant** — BSS vs PES scatter plot with four colored quadrants
- **AI Analysis** — XAI narrative, RF analysis, game theory scores
- **Fraud Triangle** — Pressure, Opportunity, Rationalization breakdown
- **OSINT Signals** — Related intelligence events with timestamps
- **SAR Report** — Collapsible Suspicious Activity Report

### 3. Sentinel Index (`/index`)
Searchable database of all flagged cases. Filter by classification, status, or market name. Sortable columns for Case ID, Market, Classification, BSS, PES, Consensus, Status, and Created date. Includes pagination and CSV export.

### 4. Arena (`/arena`)
Human-in-the-loop voting interface. Review AI classifications and vote Agree, Disagree, or Uncertain. See the consensus donut chart and total vote count. Consensus scores feed back into evaluation metrics.

### 5. System Health (`/health`)
System status dashboard with connection indicators, database statistics, classification distribution pie chart, evaluation metrics (FPR, FNR, accuracy, confusion matrix), and case status summary.

---

## API Endpoints

The FastAPI server (port 8000) provides these endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | System health check with database stats |
| `GET` | `/api/metrics` | Evaluation metrics (FPR/FNR/confusion matrix) |
| `GET` | `/api/anomalies` | List/filter anomalies (supports `classification`, `market_id`, `wallet_address`, `min_bss`, `max_bss`, `min_confidence`, `limit`, `offset`) |
| `GET` | `/api/cases/{case_id}` | Full case details with anomaly, evidence packet, and votes |
| `GET` | `/api/index` | Query Sentinel Index (supports `classification`, `status`, `search`, `min_bss`, `min_consensus`, `limit`, `offset`) |
| `GET` | `/api/evidence` | List evidence packets with pagination |
| `GET` | `/api/evidence/{case_id}` | Get evidence packet for a specific case |
| `POST` | `/api/vote` | Submit an Arena vote (requires API key if `SENTINEL_API_KEY` is set) |

---

## Fine-Tuning Pipeline

Sentinel includes a complete fine-tuning pipeline for creating a custom Mistral classifier:

```bash
# Generate 500 training examples
# Distribution: 25% INSIDER, 25% OSINT_EDGE, 15% FAST_REACTOR, 15% SPECULATOR, 20% Hard/Ambiguous
python -m src.classification.finetuning --generate-only

# Submit fine-tuning job (requires Mistral fine-tuning access)
python -m src.classification.finetuning

# Check job status
python -m src.classification.finetuning --check-job <job-id>

# Deploy: set SENTINEL_FINETUNED_MODEL=<model_id> in .env
```

Training data includes 3 gold-standard examples from real events and 497 synthetic examples with controlled difficulty distribution.

## Gold-Standard Cases

These real, documented events are embedded in Sentinel's training data:

| Case | Wallet | Classification | Evidence |
|------|--------|---------------|----------|
| **Iran Strike (Jan 2024)** | Wallet A — 3-day-old, $60K, 6-wallet cluster | INSIDER (BSS: 94) | Trade 8h before news, zero public signals, 812% return |
| **Iran Strike (Jan 2024)** | Vivaldi007 — 120-day-old, 47 trades, 62% win rate | OSINT_EDGE (BSS: 12) | Multiple public signals existed: satellite imagery, diplomatic breakdown, analyst commentary |
| **Axiom/ZachXBT (2024)** | predictorxyz — 5-day-old, $65.8K at 13.8% odds | INSIDER (BSS: 91) | No public signals pointed to Axiom specifically. Confirmed by ZachXBT. 625% return |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Dashboard** | React 19, TypeScript, Tailwind CSS 4, Framer Motion, Recharts, Vite |
| **API** | FastAPI, Uvicorn |
| **AI Classification** | Mistral Small, Mistral Large, Mistral Embed |
| **Vector Search** | ChromaDB with Mistral Embed |
| **ML Detection** | scikit-learn (Random Forest, DBSCAN, PCA) |
| **Anomaly Detection** | Custom autoencoder (numpy implementation) |
| **Database** | SQLite with WAL mode |
| **OSINT Sources** | RSS feeds, GDELT, GDACS, ACLED, NASA FIRMS |
| **Observability** | W&B Weave |
| **Data** | Polymarket CLOB API + WebSocket |

## Project Structure

```
mistral-monitor/
├── main.py                          # CLI entry point (8 commands)
├── requirements.txt                 # Python dependencies
├── ui/                              # React dashboard (Bloomberg terminal-style)
│   ├── package.json
│   ├── vite.config.ts               # Vite + API proxy to FastAPI
│   ├── src/
│   │   ├── App.tsx                  # Router setup (5 routes)
│   │   ├── index.css                # Design tokens (colors, fonts, scanlines)
│   │   ├── api/                     # API client, TypeScript types, React hooks
│   │   ├── pages/                   # LiveMonitor, CaseDetail, SentinelIndex, Arena, SystemHealth
│   │   ├── components/
│   │   │   ├── layout/              # Sidebar, DashboardLayout
│   │   │   ├── ui/                  # Card, ClassificationBadge, ScoreBar, StatusBadge, WalletAddress
│   │   │   ├── charts/              # TemporalGapChart, ClassificationQuadrant, VoteDonut
│   │   │   └── effects/             # DotGrid (interactive canvas background)
│   │   └── lib/                     # Constants, formatters
│   └── dist/                        # Production build output
├── web/                             # Landing page (Vercel deployment)
├── src/
│   ├── api/
│   │   └── main.py                  # FastAPI REST endpoints (8 routes)
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
│   └── dashboard/
│       └── app.py                   # Legacy Streamlit dashboard
└── data/
    ├── sentinel.db                  # SQLite database
    └── finetuning/                  # Generated training data
```

## Attribution

Built on the shoulders of:
- [polymarket-insider-tracker](https://github.com/pselamy/polymarket-insider-tracker) (MIT) — Rate limiting, wallet detection, cluster analysis patterns
- [worldmonitor](https://github.com/koala73/worldmonitor) — OSINT source integrations, threat classification

Data sources: [Polymarket](https://polymarket.com), [GDELT](https://www.gdeltproject.org/), [GDACS](https://www.gdacs.org/), [ACLED](https://acleddata.com/), [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/)

---

*Built for the [Mistral AI Worldwide Hackathon 2026](https://worldwide-hackathon.mistral.ai/)*
