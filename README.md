# SENTINEL

**AI-powered surveillance for prediction market integrity**

Built with Mistral AI for the| [Mistral Worldwide Hackathon 2026](https://worldwide-hackathon.mistral.ai/)

---

In January 2024, an anonymous wallet deposited $60,000 into a freshly created Polymarket account and bet everything on an Iranian military strike — **8 hours before anyone knew it was coming.** The wallet was 3 days old. Zero prior trades. Part of a 6-wallet cluster that all bet the same way. Return: **812%.**
This wasn't speculation. This was insider trading on a prediction market.
Sentinel would have caught it in real time.

## What Sentinel Does

Sentinel monitors prediction markets for information asymmetry. It watches every trade, checks it against live OSINT signals, and decides: did this trader know something the public didn't?

The bet: **the time gap between a trade and the first public signal IS the evidence.**

```
Trade at 2:00 AM ──────── 8 hours ──────── News breaks 10:00 AM
       ^                                           ^
   No public signals exist                   OSINT signals appear
   BSS: 94/100 (suspicious)                 PES: 15/100 (unexplainable)
   Classification: INSIDER                   SAR Report generated
```
## The Four Classifications

| Classification | BSS | PES | Description |
|---------------|-----|-----|-------------|
| **INSIDER** | High (>70) | Low (<30) | Trade based on material non-public information |
| **OSINT_EDGE** | Low (<30) | High (>70) | Legitimate research edge from public intelligence |
| **FAST_REACTOR** | Low (<30) | High (>70) | Quick reaction to breaking news |
| **SPECULATOR** | Low (<30) | Mid (40-60) | Normal speculation, no timing correlation |

**BSS** = Behavioral Suspicion Score (0-100) &nbsp;|&nbsp; **PES** = Public Explainability Score (0-100)

---

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
  │              5-GATE FALSE POSITIVE CASCADE                          │
  │  Statistical (20%) → RF (25%) → Autoencoder (15%)                   │
  │  → Game Theory (20%) → Mistral LLM (20%)                            │
  │  Dismiss < 0.25 ─── Escalate > 0.60                                 │
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

## Deep Dives
Each module has its own README with implementation details:

| Module | README | What's covered |
|--------|--------|----------------|
| **Classification Pipeline** | [`src/classification/`](src/classification/README.md) | 3-stage AI pipeline, fine-tuning, gold-standard cases, model deployment |
| **Detection Engine** | [`src/detection/`](src/detection/README.md) | Anomaly detection, wallet profiling, DBSCAN clustering, RF, game theory, 5-gate FP cascade |
| **OSINT Intelligence** | [`src/osint/`](src/osint/README.md) | 5 data sources, temporal correlation, vector store, RSS aggregation |
| **Real-time Pipeline** | [`src/pipeline/`](src/pipeline/README.md) | Live trade processing, evidence packets, mock/live modes |
| **REST API** | [`src/api/`](src/api/README.md) | All endpoints, authentication, request/response shapes |
| **Fine-tuning Data** | [`data/finetuning/`](data/finetuning/README.md) | Training data format, distribution, gold examples, deployment |
---

**4 Mistral models in the loop:**

| Model | Role | Latency |
|-------|------|---------|
| **Mistral Small** | Stage 1 triage — 4-class classification with BSS/PES scoring | ~1s |
| **Mistral Large** | Stage 2 deep analysis — Fraud Triangle + chain-of-thought reasoning | ~30s |
| **Mistral Large** | Stage 3 SAR — Generates regulatory-grade Suspicious Activity Reports | ~45s |
| **Mistral Embed** | OSINT vector store — Semantic search across 150+ news sources via ChromaDB | ~2s |

---
## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm (for the dashboard)
- A [Mistral AI API key](https://console.mistral.ai/)

### Installation

```bash
git clone <repo-url> && cd mistral-monitor

# Python
pip install -r requirements.txt

# Dashboard
cd ui && npm install && cd ..

# Environment
cp .env.template .env
# Edit .env and add your MISTRAL_API_KEY (required)
```

### Quick Demo

```bash
# 1. Seed the database with demo data
python main.py init

# 2. Start the API server (keep running)
python main.py api

# 3. In a new terminal, start the dashboard
cd ui && npm run dev
```

Open **http://localhost:5173** to see the dashboard.

### Running with Live Data

**Pipeline mode** grabs the top Polymarket markets, gathers OSINT, and classifies the top 5:

```bash
python main.py pipeline --live
```

**Monitor mode** connects to Polymarket's WebSocket and processes trades continuously:

```bash
python main.py monitor --live    # Ctrl+C to stop
```

**Mock mode** skips external data sources (still needs `MISTRAL_API_KEY`):

```bash
python main.py pipeline --mock       # 4 synthetic anomalies
python main.py monitor --mock 50     # 50 mock trades
```

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `MISTRAL_API_KEY` | **Yes** | All AI models (classification + embedding) |
| `ACLED_ACCESS_TOKEN` | No | Armed conflict OSINT data ([register](https://acleddata.com/)) |
| `NASA_FIRMS_API_KEY` | No | Fire/thermal detection OSINT ([register](https://firms.modaps.eosdis.nasa.gov/)) |
| `WANDB_API_KEY` | No | W&B Weave tracing for pipeline observability |
| `SENTINEL_FINETUNED_MODEL` | No | Use a fine-tuned model for Stage 1 triage |
| `SENTINEL_API_KEY` | No | Protect the vote endpoint (unset = open demo mode) |

---

## All Commands

| Command | Description |
|---------|-------------|
| `python main.py init` | Initialize database + seed demo data |
| `python main.py api` | Start FastAPI server on :8000 |
| `python main.py dashboard` | Start legacy Streamlit dashboard |
| `python main.py metrics` | Print evaluation metrics |
| `python main.py pipeline --mock\|--live\|--backfill` | Run classification pipeline |
| `python main.py monitor --mock [N]\|--live` | Real-time trade monitoring |
| `cd ui && npm run dev` | Start React dashboard on :5173 |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Dashboard | React 19, TypeScript, Tailwind CSS 4, Framer Motion, Recharts, Vite |
| API | FastAPI, Uvicorn |
| AI Classification | Mistral Small, Mistral Large, Mistral Embed |
| Vector Search | ChromaDB with Mistral Embed |
| ML Detection | scikit-learn (Random Forest, DBSCAN, PCA) |
| Anomaly Detection | Custom autoencoder (numpy) |
| Database | SQLite with WAL mode |
| OSINT Sources | RSS feeds, GDELT, GDACS, ACLED, NASA FIRMS |
| Observability | W&B Weave |
| Data | Polymarket CLOB API + WebSocket |

## Project Structure

```
mistral-monitor/
├── main.py                          # CLI entry point
├── requirements.txt
├── ui/                              # React dashboard
│   ├── src/
│   │   ├── pages/                   # LiveMonitor, CaseDetail, SentinelIndex, Arena, SystemHealth
│   │   ├── components/              # Charts, layout, UI primitives
│   │   └── api/                     # Client, hooks, types
│   └── dist/                        # Production build
├── web/                             # Landing page (Vercel)
├── src/
│   ├── api/                         # FastAPI REST endpoints
│   ├── classification/              # 3-stage AI pipeline + fine-tuning
│   ├── detection/                   # Anomaly detection, clustering, ML models
│   ├── osint/                       # Intelligence sources + correlation
│   ├── pipeline/                    # Real-time evidence processing
│   ├── data/                        # Database, Polymarket client, WebSocket
│   └── dashboard/                   # Legacy Streamlit dashboard
└── data/
    ├── sentinel.db                  # SQLite database
    └── finetuning/                  # Training data (JSONL)
```

## Attribution

Adapted from:
- [polymarket-insider-tracker](https://github.com/pselamy/polymarket-insider-tracker) (MIT) — Rate limiting, wallet detection, cluster analysis patterns
- [worldmonitor](https://github.com/koala73/worldmonitor) — OSINT source integrations, threat classification

Data sources: [Polymarket](https://polymarket.com) | [GDELT](https://www.gdeltproject.org/) | [GDACS](https://www.gdacs.org/) | [ACLED](https://acleddata.com/) | [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/)

---

*Built for the [Mistral AI Worldwide Hackathon 2026](https://worldwide-hackathon.mistral.ai/)*
