# SENTINEL: Prediction Market Integrity Monitor
## Unified Hackathon PRD
### Mistral Worldwide Hackathon | Feb 28 - Mar 1, 2026

---

## 1. Executive Summary

### One-Liner

Sentinel is an AI-powered surveillance system that detects information asymmetry in prediction markets, classifies whether suspicious trades stem from insider knowledge or legitimate OSINT edge, and maintains the world's first open, curated database of potential insider trading cases across prediction market platforms.

### The Problem

Prediction markets like Polymarket are becoming critical infrastructure for information discovery. Journalists cite them. Businesses use them for forecasting. Governments monitor them. But their value depends entirely on market integrity. When actors with privileged information trade before news breaks publicly, it corrupts the signal and undermines trust in the entire system.

Today, there is no public tool that systematically monitors prediction markets for information asymmetry. The markets are essentially unpoliced. And even among those who notice suspicious activity, nobody can answer the harder question: was this an insider, or just a sharper analyst reading public data?

### The Solution

An autonomous monitoring, classification, and archival agent powered by Mistral that:

1. Continuously ingests Polymarket price/volume data and global news feeds
2. Detects abnormal trading patterns (volume spikes, sharp probability shifts)
3. Correlates those patterns with the timing of subsequent public news events
4. Classifies each flagged trade into one of four categories -- INSIDER, OSINT_EDGE, FAST_REACTOR, or SPECULATOR -- using a fine-tuned Mistral Small model trained on 500 game-theoretic trade scenarios
5. Uses Magistral to provide deep reasoning that confirms or challenges the classification
6. Generates structured Suspicious Activity Reports with evidence timelines
7. Archives every case into the **Sentinel Index** -- the first open, curated database of potential insider trading on prediction markets, with standardized evidence packages, classifications, human consensus scores, and full audit trails
8. Delivers real-time voice alerts via ElevenLabs when anomalies are detected
9. Hosts a live Sentinel Arena where humans validate AI classifications as a human-in-the-loop ground truth layer
10. Logs all monitoring activity, agent reasoning, and fine-tuning evaluation in Weights & Biases

### The Pitch (in one breath)

"Prediction markets are becoming the world's real-time truth layer. But right now, nobody is watching the watchers, nobody can tell the difference between someone with classified intel and someone who just reads flight-tracking data better than you do, and nobody is keeping score. We built the first AI system that detects insider trading on prediction markets, classifies the trader type, and archives every case into the largest open database of prediction market integrity violations. In 48 hours. On Mistral."

### Hackathon Prize Targeting

| Prize | Eligibility Strategy |
|-------|---------------------|
| **Global Winner / Main Podium** | High-impact narrative + live demo + technical depth (5 Mistral models + fine-tuning) + strong pitch |
| **Best Use of Agent Skills** (Hugging Face) | Autonomous monitoring agent with multi-step reasoning; human-in-the-loop validation layer |
| **Best Use of ElevenLabs** | Real-time voice alerts for detected anomalies + voice Q&A |
| **Best Vibe Usage** | AI-assisted development process, screen-recorded throughout |
| **W&B Global Track** | Full agent tracing with Weave, fine-tuning metrics, anomaly detection logging, Arena eval dashboard |
| **Next Unicorns** (Giant) | "The Bloomberg Terminal for prediction market integrity" -- clear path to SaaS revenue + compounding data moat via the Index |
| **Best Architectural Modification** (Tilde) | Fine-tuned Mistral Small for game-theoretic trade classification; two-model pipeline (fast triage + deep reasoning) |

---

## 2. Core Concept: How Information Asymmetry Detection Works

### The Signal

The fundamental detection pattern:

```
Timeline:
  T-6h: Unusual volume spike on Polymarket contract "Will X happen?"
  T-4h: Price moves sharply from 30% to 65%
  T-0h: Reuters/AP/BBC breaks the news that X happened
  
  Gap between trading anomaly and public news = INFORMATION ASYMMETRY SIGNAL
```

### What Makes This Detectable

1. **Prediction markets have public order books and price history** -- every trade is timestamped and visible
2. **News events have clear publication timestamps** -- wire services, major outlets, official announcements
3. **The temporal gap between "market moved" and "news broke" is measurable**
4. **Normal market behavior has patterns** -- gradual price discovery looks different from sudden informed trading

### Detection Categories

**Category 1: Pre-News Volume Spike**
Trading volume on a specific contract surges 3x+ above baseline with no corresponding public news event at that time. News event matching the contract's subject breaks hours/days later. Confidence: HIGH (most detectable pattern).

**Category 2: Price Dislocation**
Contract price moves >15 percentage points in <2 hours. Movement direction correctly predicts the eventual outcome. No public information available at time of movement to justify the shift. Confidence: HIGH.

**Category 3: Correlated Cross-Market Movement**
Multiple related contracts move simultaneously (e.g., "Will sanctions be imposed?" + "Will oil prices exceed $X?" + "Will diplomatic talks collapse?"). Correlated movement suggests a single actor or group with knowledge of a connected event. Confidence: MEDIUM.

**Category 4: Liquidity Withdrawal**
Market makers pull liquidity from a contract just before adverse news. The absence of normal trading activity can itself be a signal. Confidence: MEDIUM-LOW.

---

## 3. The OSINT vs. Insider Distinction: Sentinel's Intellectual Moat

When Sentinel flags a suspicious market movement, the next question is: **was this person trading on private information (insider) or on public information the market was too slow to price (OSINT edge)?**

This distinction matters to every stakeholder:

| Stakeholder | Why They Care |
|-------------|---------------|
| **Regulators** | Insiders may be breaking laws. OSINT traders are doing exactly what markets reward. Regulating them identically is bad policy. |
| **Polymarket** | They *want* OSINT-informed trading (it makes prices accurate). They *don't want* insider trading (it erodes trust). They need to tell the difference. |
| **Journalists** | "Pentagon employee bets on military strike" is a story. "OSINT analyst reads public flight data and bets on military strike" is not. |
| **Traders** | If a suspicious trade is OSINT-explainable, other traders can replicate the edge. If it's insider-driven, they can't. |

No existing tool makes this distinction. Polysights flags suspicious wallets. Bubblemaps maps wallet clusters. Neither asks "was public information available that could explain this?"

### The Four Classifications

**INSIDER** (Public Explainability low, Behavioral Suspicion high)
No public signal existed that could explain the trade. Wallet behavior matches insider patterns (fresh, concentrated, single-use). The trader had access to information the public did not.

**OSINT_EDGE** (Public Explainability high, Behavioral Suspicion low)
Public signals DID exist before the trade. Wallet has established trading history. The trader was faster or more sophisticated at processing public information.

**FAST_REACTOR** (Public Explainability high, Behavioral Suspicion low, trade placed after news broke)
Trade placed within minutes of a news event becoming public. The trader simply reacted faster than the market adjusted. Completely legitimate.

**SPECULATOR** (Public Explainability low, Behavioral Suspicion low)
No public signal, but wallet behavior doesn't match insider patterns either. Long trading history, mixed win rate, pattern of big bold bets. Got lucky or had a strong thesis.

### The Information Timeline

```
T-72h    T-24h    T-6h     T-1h     T-0      T+1h
  |        |        |        |        |        |
  |        |        |        |        | NEWS   |
  |        |        |        |        | BREAKS |
  |        |     INSIDER   FAST     PUBLIC   MARKET
  |      OSINT   TRADES   REACTOR  KNOWS    ADJUSTS
  |      SIGNALS          TRADES            FULLY
  |      APPEAR
PRIVATE INFO
EXISTS
```

The model's job: given a trade timestamp and the available evidence, determine where on this timeline the trader was operating and what information they likely had access to.

### The Prediction Market as a Game

```
PLAYER TYPES:
+----------------------------------------------------------+
|  INFORMED PLAYERS          UNINFORMED PLAYERS             |
|  +-----------+             +---------------+              |
|  | INSIDER   |             | SPECULATOR    |              |
|  | Has priv  |             | No edge, bets |              |
|  | info      |             | on thesis     |              |
|  +-----------+             +---------------+              |
|  +-----------+             +---------------+              |
|  | OSINT     |             | NOISE TRADER  |              |
|  | Has pub   |             | Small bets,   |              |
|  | info edge |             | follows crowd |              |
|  +-----------+             +---------------+              |
|  +-----------+                                            |
|  | FAST      |             STRUCTURAL PLAYERS             |
|  | REACTOR   |             +---------------+              |
|  | Speed     |             | MARKET MAKER  |              |
|  | edge      |             | Provides      |              |
|  +-----------+             | liquidity     |              |
|                            +---------------+              |
+----------------------------------------------------------+
```

Binary "insider or not" is too crude. The fine-tuned model learns to identify which game is being played based on the evidence.

---

## 4. User Personas

### Primary: Prediction Market Researcher / Journalist
Investigating market integrity for publications. Needs evidence-backed timelines showing suspicious patterns and the OSINT-vs-insider distinction. Wants exportable reports with clear visualizations.

### Secondary: Polymarket / Exchange Integrity Team
Internal market surveillance. Needs automated monitoring at scale across hundreds of contracts. Wants severity scoring, prioritized alerts, and trader classification.

### Tertiary: Regulatory Observer (CFTC, academic researchers)
Studying whether prediction markets need regulation. Needs systematic data on information asymmetry frequency and severity. Wants historical analysis and game-theoretic classification to inform policy.

---

## 5. Feature Specification

### 5.1 Data Ingestion Layer

**Polymarket Data (Primary Market Source):**
Contract list with metadata (topic, category, resolution criteria), historical price data (probability over time), volume data (trade counts, dollar volume per time period), order book depth (if available via API), and resolution timestamps.

**News Data (Public Information Baseline):**
Real-time RSS feeds from Tier 1 sources (Reuters, AP, BBC, Al Jazeera), GDELT (Global Database of Events, Language, and Tone) for real-time event detection with timestamps, Google News API or similar aggregator for broader coverage, and social media signals (Twitter/X trending topics) as supplementary timing data.

**Supplementary Data (Stretch Goals):**
Blockchain data (Polymarket runs on Polygon -- wallet analysis for whale tracking), other prediction platforms (Kalshi, Metaculus), and government press release feeds.

**For hackathon scope:** Polymarket API + 10-15 RSS feeds from major wire services + GDELT. Everything else is stretch.

### 5.2 Anomaly Detection Engine

**Step 1: Baseline Computation**
For each active Polymarket contract, compute rolling average volume (7-day, 24-hour), rolling price volatility (standard deviation of hourly price changes), typical daily trading pattern, and category-specific baselines.

**Step 2: Real-Time Anomaly Flagging**
Trigger an investigation when any of these conditions are met:

```
VOLUME_SPIKE: current_hour_volume > 3x rolling_24h_average
PRICE_JUMP:   abs(price_change_2h) > 15 percentage points
VELOCITY:     rate_of_price_change > 2x historical_max_velocity
CROSS_MARKET: 3+ related contracts move >10pp in same direction within 4h window
```

**Step 3: News Correlation**
When an anomaly is flagged, record the anomaly timestamp and contract details, monitor news feeds for the next 24-48 hours, use Mistral (with RAG over news) to determine if/when public information emerged, compute the temporal gap, and score the information asymmetry signal.

**Step 4: Two-Model AI Assessment**

This is where the fine-tuned model and Magistral work together:

```
Anomaly + News + Public Signals + Wallet Behavior
    |
    v
Fine-tuned Mistral Small (fast classification)
    -> INSIDER / OSINT_EDGE / FAST_REACTOR / SPECULATOR
    -> Public Explainability Score (PES): 0.0-1.0
    -> Behavioral Suspicion Score (BSS): 0.0-1.0
    -> Game-theoretic reasoning
    |
    v
Magistral (deep reasoning, informed by classification)
    -> Confirms or challenges the classification
    -> Detailed prose reasoning and alternative explanations
    -> Recommendations for further investigation
    |
    v
Combined Assessment (machine-parseable scores + human-readable narrative)
```

The fine-tuned model gives you the classification and scores. Magistral gives you the prose explanation and counter-arguments. Together they produce a complete assessment.

### 5.3 Suspicious Activity Report (SAR) Generator

Each confirmed anomaly produces a structured report:

```json
{
  "report_id": "SAR-2026-0228-001",
  "severity": "HIGH",
  "contract": {
    "id": "polymarket_contract_id",
    "question": "Will the US impose tariffs on Canadian goods by March 2026?",
    "category": "geopolitics",
    "current_price": 0.82,
    "resolution_date": "2026-03-15"
  },
  "anomaly": {
    "type": "VOLUME_SPIKE + PRICE_JUMP",
    "detected_at": "2026-02-27T14:23:00Z",
    "volume_multiple": 4.7,
    "price_movement": "+32pp (0.35 -> 0.67) in 90 minutes",
    "estimated_dollar_volume": "$2.3M"
  },
  "news_correlation": {
    "first_public_report": "2026-02-27T21:15:00Z",
    "source": "Reuters",
    "headline": "US announces new tariff package on Canadian imports",
    "time_gap_hours": 6.87,
    "additional_sources": ["AP (21:18)", "Bloomberg (21:22)", "NYT (21:45)"]
  },
  "classification": {
    "type": "INSIDER",
    "confidence": 0.92,
    "public_explainability_score": 0.15,
    "behavioral_suspicion_score": 0.94
  },
  "ai_assessment": {
    "informed_trading_likelihood": "HIGH (0.84)",
    "reasoning": "Volume spike of 4.7x baseline occurred 6.9 hours before any public reporting. No social media discussion, leaked documents, or analyst predictions found in the pre-news window. The concentrated nature of the volume (87% of spike in a 30-minute window) suggests a small number of actors.",
    "alternative_explanations": [
      {"explanation": "Possible leak from government officials", "probability": "HIGH"},
      {"explanation": "Pattern trading based on historical tariff announcements", "probability": "LOW"},
      {"explanation": "Social media signal not captured by monitoring", "probability": "MEDIUM"}
    ],
    "confidence": 0.78,
    "estimated_information_advantage": "$1.2M profit on $2.3M position"
  },
  "evidence_timeline": [
    {"time": "T-24h", "event": "Normal trading volume, price stable at 0.33-0.36"},
    {"time": "T-7h", "event": "First unusual buy order: $150K at 0.38"},
    {"time": "T-6.5h", "event": "Volume spike begins, 4.7x baseline"},
    {"time": "T-5h", "event": "Price reaches 0.67, volume remains elevated"},
    {"time": "T-3h", "event": "Price stabilizes at 0.64-0.67"},
    {"time": "T-0h", "event": "Reuters breaks tariff announcement"},
    {"time": "T+1h", "event": "Price jumps to 0.89 on public confirmation"}
  ]
}
```

### 5.4 Dashboard UI

**Main View: Market Surveillance Feed**
A real-time feed of monitored contracts with anomaly indicators. Bloomberg Terminal meets fraud detection dashboard.

```
LIVE MONITORING                                          Active Contracts: 247
------------------------------------------------------------------------
[!!! HIGH] US-Canada Tariffs by March     | INSIDER   | Gap: 6.9h | $2.3M
[!! MED]   Fed Rate Cut Q2 2026           | OSINT     | Gap: 3.2h | $890K  
[! LOW]    UK General Election Before 2027 | SPECULATOR| Gap: 12h  | $340K
------------------------------------------------------------------------
Normal:    Iran Nuclear Deal              | --        | --        | $120K
Normal:    Bitcoin > $100K by June        | --        | --        | $2.1M
```

**Anomaly Deep-Dive View:**
Split-screen timeline with price/volume chart on the left and news timeline on the right. The "gap" between market movement and news is highlighted visually. Below that: the four-class classification with PES/BSS scores, AI assessment with reasoning chain, and evidence quality indicators.

**The 2x2 Classification Grid (Key Visual):**

```
                    LOW public signals    HIGH public signals
                    +--------------------+--------------------+
  SUSPICIOUS        | RED: INSIDER       | YELLOW: TEMPORALLY |
  wallet behavior   |                    |    SUSPICIOUS      |
                    | Iran Wallet A      |                    |
                    | PES: 0.15          |                    |
                    | BSS: 0.94          |                    |
                    | Profit: $494K      |                    |
                    +--------------------+--------------------+
  NORMAL            | ORANGE: SPECULATOR | GREEN: OSINT EDGE  |
  wallet behavior   |                    |                    |
                    | anoin123           | Vivaldi007         |
                    | PES: 0.10          | PES: 0.72          |
                    | BSS: 0.15          | BSS: 0.12          |
                    | Loss: -$6.5M       | Profit: $385K      |
                    +--------------------+--------------------+
```

**Historical Analysis View:**
Leaderboard of most suspicious historical patterns, statistics on detection frequency, and category breakdown.

### 5.5 Voice Interface

**Alerts (ElevenLabs output):**
"Alert: High-severity anomaly detected on the US-Canada tariff contract. Trading volume spiked to 4.7 times baseline 6.9 hours before Reuters reported the tariff announcement. Our classification: probable INSIDER activity with 92% confidence. Public signal score is 0.15 -- no public information could explain this trade. Full report is available on the dashboard."

**Query (Voxtral input + Mistral processing + ElevenLabs output):**
"What's the most suspicious contract right now?" / "Show me all INSIDER classifications this week" / "What public signals existed before the Iran strike trades?"

### 5.6 Sentinel Arena -- Human-in-the-Loop Validation Layer

A live, public dashboard where Sentinel presents its flagged trades and classifications, and humans vote on whether they agree with the AI's assessment. Think of it as a crowdsourced ground truth layer -- the system proposes, humans validate.

**How It Works:**
1. Sentinel surfaces a flagged trade as an **evidence card**: market data, timeline, wallet stats, public signal landscape, and the AI's classification (INSIDER / OSINT_EDGE / FAST_REACTOR / SPECULATOR) with its PES/BSS scores and reasoning.
2. Humans (hackathon attendees, judges, anyone with the URL) review the evidence and the AI's call, then vote: **AGREE** or **DISAGREE**. If they disagree, they select which classification they think is correct and optionally explain why.
3. Votes aggregate in real time. The dashboard shows consensus rates -- where humans overwhelmingly agree with the AI, and where they don't.
4. Disagreement cases become the most interesting data points: they surface edge cases where the model's reasoning is weakest, or where the evidence is genuinely ambiguous.

**Pre-loaded Cases (5 cases from real events):**

| Case | AI Classification | Expected Human Consensus |
|------|------------------|--------------------------|
| Iran strike -- Wallet A ($60K -> $494K, 3-day wallet) | INSIDER (0.92) | High agreement -- obvious red flags |
| Iran strike -- Vivaldi007 ($385K profit, 47 prior trades) | OSINT_EDGE (0.88) | Mixed -- this is the hard one that proves the product |
| Iran strike -- anoin123 (-$6.5M loss, bet against) | SPECULATOR (0.85) | High agreement -- the loss makes it intuitive |
| Axiom/ZachXBT -- predictorxyz ($65K -> $477K at 13.8% odds) | INSIDER (0.95) | High agreement -- confirmed by ZachXBT |
| Iran strike -- Roeyha2026 ($50K bet, wallet created 11h before) | INSIDER (0.89) | Moderate -- some may argue speculator |

**Why It Matters:**

This is more powerful than a competition for three reasons:

1. **It's a real product feature, not a gimmick.** Human-in-the-loop validation is how you build ground truth for a system like this. Regulators won't act on AI-only classifications -- they need human consensus backing the call. The Arena is the mechanism for that.
2. **Disagreement is the interesting signal.** When 80% of humans agree the AI got it right, that's validation. When only 50% agree, that's where the model needs improvement -- and where the OSINT-vs-insider distinction is genuinely hard. Showing both to judges demonstrates intellectual honesty.
3. **Judges experience the product's core tension.** When a judge reviews the Vivaldi007 case and has to decide whether it's OSINT or insider, they viscerally understand why this tool needs to exist. The classification is hard for humans too -- that's the whole point.

---

### 5.7 The Sentinel Index -- Curated Insider Trading Database

The Sentinel Index is the world's first open, structured database of potential insider trading cases on prediction markets. Every case Sentinel detects, classifies, and validates flows into the Index as a permanent, searchable record.

**Why This Matters:**

Right now, knowledge of prediction market insider trading is scattered across crypto Twitter threads, one-off news articles, and Reddit posts. There is no canonical source. No one has aggregated, standardized, and classified these cases. The Sentinel Index is the CVE database of prediction market manipulation -- a shared, growing record that regulators, journalists, researchers, and platforms can all reference.

This is the asset that compounds over time. The detection engine is impressive but ephemeral. The fine-tuned model is a technical achievement. The Index is what makes Sentinel indispensable -- because once you have the largest collection of documented cases, you become the citation source for everyone working on prediction market integrity.

**What Each Index Entry Contains:**

```json
{
  "index_id": "SI-2026-0047",
  "status": "CONFIRMED | UNDER_REVIEW | DISPUTED",
  "detected_at": "2026-02-27T14:23:00Z",

  "market": {
    "platform": "Polymarket",
    "contract": "Will the US impose tariffs on Canadian goods by March 2026?",
    "category": "geopolitics",
    "resolution": "YES",
    "total_volume": "$14.2M"
  },

  "anomaly_summary": {
    "type": "VOLUME_SPIKE + PRICE_JUMP",
    "volume_multiple": 4.7,
    "price_movement": "+32pp in 90 minutes",
    "time_gap_to_news_hours": 6.87,
    "estimated_position_value": "$2.3M",
    "estimated_profit": "$1.2M"
  },

  "classification": {
    "ai_classification": "INSIDER",
    "ai_confidence": 0.92,
    "public_explainability_score": 0.15,
    "behavioral_suspicion_score": 0.94,
    "human_consensus": {
      "agree_pct": 0.87,
      "total_votes": 34,
      "most_common_disagreement": "SPECULATOR"
    }
  },

  "evidence_package": {
    "price_timeline": "[time-series data]",
    "volume_timeline": "[time-series data]",
    "news_correlation": {
      "first_report": "Reuters, 2026-02-27T21:15:00Z",
      "headline": "US announces new tariff package on Canadian imports"
    },
    "public_signal_landscape": {
      "government_calendars": "NONE",
      "analyst_predictions": "WEAK",
      "social_media": "NONE",
      "osint_signals": "NONE"
    },
    "wallet_behavior": {
      "wallet_age_days": 3,
      "prior_trades": 0,
      "cluster_indicators": "Part of 6-wallet cluster"
    }
  },

  "ai_reasoning": {
    "fine_tuned_model_output": "...",
    "magistral_deep_reasoning": "...",
    "alternative_explanations": ["..."]
  },

  "metadata": {
    "added_to_index": "2026-02-28T03:00:00Z",
    "last_updated": "2026-02-28T18:30:00Z",
    "source_sar_id": "SAR-2026-0228-001",
    "tags": ["geopolitics", "tariffs", "pre-news-spike", "wallet-cluster"]
  }
}
```

**Index Statistics Dashboard:**

```
SENTINEL INDEX                                    Total Cases: 127
-------------------------------------------------------------------
Cases by Classification:
  INSIDER:      43 (34%)    | Avg profit: $312K  | Avg time gap: 7.2h
  OSINT_EDGE:   31 (24%)    | Avg profit: $189K  | Avg time gap: 48h+
  FAST_REACTOR: 22 (17%)    | Avg profit: $67K   | Avg time gap: <0.5h
  SPECULATOR:   31 (24%)    | Avg P&L: -$41K     | Avg time gap: N/A

Cases by Category:
  Geopolitics: 47  |  Crypto: 33  |  US Politics: 28  |  Other: 19

Human Consensus:
  Avg agreement with AI: 78%
  Most disputed: OSINT_EDGE (61% agreement)
  Least disputed: INSIDER w/ fresh wallets (93% agreement)

Estimated Total Insider Profit (all indexed cases): $13.4M
-------------------------------------------------------------------
```

**How the Index Gets Populated:**

For the hackathon, the Index is seeded three ways:

1. **Autonomous research agent (launched hour 1, runs all day).** A Mistral Large-powered agent searches the web for documented cases of suspicious Polymarket activity, extracts structured data, and outputs Index entries. Human review and curation happens Sunday morning. This is itself a demo of agent capabilities.

2. **Live detection pipeline.** Any anomaly that Sentinel detects, classifies, and generates a SAR for during the hackathon automatically gets an Index entry. The pipeline writes directly to the Index.

3. **Arena validation.** As humans vote on cases in the Arena, their consensus scores flow back into the Index entry, upgrading the case's status from UNDER_REVIEW to CONFIRMED (if >75% human agreement) or DISPUTED (if <50%).

**For the hackathon demo:** Aim for 20-30 indexed cases. Even at that scale, it is the largest structured collection of prediction market insider trading cases that exists anywhere. The number itself is a pitch line.

**Searchable and Filterable:**

The Index is browsable by classification type, by category (geopolitics, crypto, politics), by platform, by date range, by severity, by profit size, and by human consensus level. Journalists can find all INSIDER cases involving geopolitics. Regulators can filter by estimated profit above $500K. Researchers can analyze patterns across categories.

**Why Judges Should Care:**

The detection engine answers "is something suspicious happening right now?" The Index answers "how often does this happen, who does it, and how much money is involved?" That second question is what regulators need to justify oversight, what journalists need to write investigative series, and what platforms need to argue they take integrity seriously. The Index is the durable asset that outlives any single detection.

---

## 6. Fine-Tuning Specification

### Model Choice

**Mistral Small (mistral-small-latest)** via Mistral's fine-tuning API.

Why Small, not Large: faster to fine-tune, fast inference (runs on every flagged anomaly), the task is classification + structured reasoning rather than open-ended generation, and if Small is good enough after fine-tuning it proves the fine-tuning added real value.

### Training Data

**500 total examples. Distribution:**

| Classification | Count | Rationale |
|---------------|-------|-----------|
| INSIDER | 125 | Core detection target. Needs the most training signal. |
| OSINT_EDGE | 125 | Equally important -- the model must learn to acquit legitimate traders. |
| FAST_REACTOR | 75 | Simpler pattern (trade after news). Less training needed. |
| SPECULATOR | 75 | Simpler pattern (no edge, mixed history). Less training needed. |
| Ambiguous/Hard | 100 | Edge cases where classification is uncertain. Trains calibrated confidence. |

**Generation method:** Use `mistral-large-latest` with a meta-prompt to generate training examples. Randomized parameters (market topic, timing, wallet stats, signal levels) ensure diversity.

**Three gold-standard examples are hardcoded from real, published events:**

**Gold 1: Iran Strike -- Wallet A (INSIDER)**
Contract: "US strikes Iran by February 28, 2026?" / Anomaly: 5x baseline, $560K in 2-hour window / Time gap: ~8 hours / Public signals: WEAK (general diplomatic tension, no specific-date indicators) / Wallet: 3 days old, 0 prior trades, $60K single deposit, part of 6-wallet cluster / Profit: $494,375 (812% return) / Classification: INSIDER, confidence 0.92, PES 0.15, BSS 0.94

**Gold 2: Iran Strike -- Vivaldi007 (OSINT_EDGE)**
Contract: Same event / Trading started Feb 8, 20 days before / Public signals: MODERATE-STRONG (diplomatic breakdown, analyst commentary, satellite imagery, Trump rhetoric) / Wallet: 4+ months old, 47 prior trades, 62% win rate, lost money on earlier date contracts / Profit: $385,000 / Classification: OSINT_EDGE, confidence 0.88, PES 0.72, BSS 0.12

**Gold 3: Axiom/ZachXBT -- predictorxyz (INSIDER)**
Contract: "Which crypto company will ZachXBT expose?" / Anomaly: Axiom odds surged from 13% to 46% / Time gap: ~9 hours / Public signals: NONE for specific Axiom outcome (Meteora was the public frontrunner) / Wallet: recently created, minimal history, $65.8K position at 13.8% odds / Profit: $411,400 (625% return) / Classification: INSIDER, confidence 0.95, PES 0.05, BSS 0.91

### Fine-Tuning Execution

```python
from mistralai import Mistral
import wandb

wandb.init(
    project="sentinel-fine-tune",
    config={
        "base_model": "mistral-small-latest",
        "examples": 500,
        "task": "trade-classification-game-theory",
        "steps": 100,
        "lr": 1e-4
    }
)

client = Mistral(api_key=MISTRAL_API_KEY)

# Upload training and validation data
with open("train.jsonl", "rb") as f:
    train_file = client.files.upload(
        file={"file_name": "sentinel_train.jsonl", "content": f}
    )
with open("val.jsonl", "rb") as f:
    val_file = client.files.upload(
        file={"file_name": "sentinel_val.jsonl", "content": f}
    )

# Submit fine-tuning job
job = client.fine_tuning.jobs.create(
    model="mistral-small-latest",
    training_files=[{"file_id": train_file.id, "weight": 1}],
    validation_files=[{"file_id": val_file.id}],
    hyperparameters={"training_steps": 100, "learning_rate": 1e-4},
    suffix="sentinel-v1"
)

# Poll until complete
import time
while job.status not in ["SUCCESS", "FAILED"]:
    time.sleep(60)
    job = client.fine_tuning.jobs.get(job.id)
    print(f"Status: {job.status}")

wandb.log({"model_id": job.fine_tuned_model, "status": job.status})
wandb.finish()
```

**Timeline:** Generate data in hours 0-3, submit job in hour 3, model ready by hour 5-7. Fine-tuning runs in the background while the core pipeline is built.

### Fallback

If fine-tuning fails or quality is poor, use `magistral-medium-latest` with the full system prompt and few-shot examples. The demo works either way. Fine-tuning is the cherry on top that makes it eligible for the Best Architectural Modification track and proves deeper technical work.

### Evaluation Plan

Hold out 50 examples (10 per classification) as a test set.

**Metrics:** Classification accuracy, PES calibration, BSS calibration, confidence calibration.

**Comparison (the money chart for the pitch):**

| Model | Classification Accuracy | Avg Confidence (Correct) | Avg Confidence (Incorrect) |
|-------|------------------------|--------------------------|----------------------------|
| Base Mistral Small (few-shot) | X% | X | X |
| Fine-tuned Mistral Small | Y% | Y | Y |
| Magistral (zero-shot) | Z% | Z | Z |

Fine-tuned Small beating base Small proves fine-tuning worked. Fine-tuned Small approaching Magistral proves it learned genuine reasoning.

---

## 7. Technical Architecture

### System Diagram

```
[Data Ingestion Layer]
    |-- Polymarket API (price, volume, contracts)
    |-- RSS Feeds (Reuters, AP, BBC, etc.)
    |-- GDELT API (real-time events)
    v
[Stream Processing]
    |-- Contract Monitor (per-contract baseline + anomaly detection)
    |-- News Monitor (real-time event extraction + timestamping)
    |-- Correlation Engine (temporal matching: anomaly <-> news)
    v
[AI Assessment Layer]
    |-- Fine-tuned Mistral Small (fast classification: 4-class + PES/BSS)
    |-- Magistral (deep reasoning, confirms/challenges classification)
    |-- Mistral Large (function calling for structured SAR generation)
    |-- Mistral Embed + ChromaDB (RAG over news archive for context)
    v
[Output Layer]
    |-- Dashboard (React + Tailwind / Streamlit)
    |-- Sentinel Index (curated case database + statistics + search)
    |-- Sentinel Arena (human validation UI + consensus dashboard)
    |-- SAR Generator (structured reports)
    |-- Voice Alerts (ElevenLabs)
    |-- Voice Q&A (Voxtral -> Mistral -> ElevenLabs)
    |-- W&B Logging (all agent decisions traced via Weave)
```

### Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Frontend | Streamlit or React + Tailwind + Recharts | Fast to build; good charting for price/volume data |
| Backend | Python + FastAPI | Best for data processing + ML tooling |
| Market Data | Polymarket API (CLOB API) | Public, well-documented, real-time |
| News Data | RSS feeds + GDELT API | Free, timestamped, broad coverage |
| Anomaly Detection | Python (numpy/scipy) | Z-score, rolling baselines |
| Trade Classification | Fine-tuned Mistral Small | Fast 4-class classification with PES/BSS scores |
| Deep Reasoning | Magistral (reasoning model) | Chain-of-thought for nuanced assessment |
| Structured Output | Mistral Large (function calling) | SAR generation with structured JSON |
| Embeddings/RAG | Mistral Embed + ChromaDB | News archive search for correlation |
| Speech-to-Text | Voxtral Mini Transcribe V2 | Voice queries |
| Text-to-Speech | ElevenLabs API | Voice alerts and responses |
| Observability | Weights & Biases (Weave) | Agent tracing, fine-tuning metrics, Arena eval |
| Deployment | Local / Vercel / Railway | Whatever is fastest |

### Mistral Model Usage Map (6 models)

| Component | Model | Feature | Purpose |
|-----------|-------|---------|---------|
| Trade Classification | Fine-tuned Mistral Small | Structured classification | Fast 4-class game-theoretic triage |
| Pattern Assessment | Magistral | Chain-of-thought reasoning | Deep reasoning about trading patterns |
| SAR Generation | Mistral Large | Function calling (JSON) | Consistent, structured report output |
| News Matching | Mistral Small (base) | Fast text classification | Quickly determine if news relates to a contract |
| News Archive RAG | Mistral Embed | Semantic search | Find relevant prior reporting for context |
| Voice Queries | Voxtral Mini | Speech-to-text | Voice input processing |

### Polymarket API Integration

```python
# Key endpoints
GET https://clob.polymarket.com/markets
GET https://clob.polymarket.com/prices-history?market={token_id}&interval=1h
GET https://clob.polymarket.com/book?token_id={token_id}
GET https://clob.polymarket.com/trades?market={token_id}
```

Polling frequency for hackathon: every 5 minutes for active contracts, every 30 minutes for inactive ones.

### Core Detection Algorithm

```python
class ContractMonitor:
    def __init__(self, contract_id):
        self.baseline_volume = RollingWindow(24h)
        self.baseline_volatility = RollingWindow(7d)
        self.price_history = TimeSeries()
        self.anomalies = []
    
    def ingest(self, timestamp, price, volume):
        self.price_history.add(timestamp, price)
        self.baseline_volume.add(volume)
        
        if volume > 3 * self.baseline_volume.mean():
            self.flag_anomaly("VOLUME_SPIKE", {...})
        
        price_2h_ago = self.price_history.get(timestamp - 2h)
        if price_2h_ago and abs(price - price_2h_ago) > 0.15:
            self.flag_anomaly("PRICE_JUMP", {...})
        
        velocity = self.price_history.rate_of_change(window=1h)
        if velocity > 2 * self.baseline_volatility.max():
            self.flag_anomaly("VELOCITY", {...})
    
    def flag_anomaly(self, anomaly_type, details):
        anomaly = Anomaly(contract_id=self.contract_id, type=anomaly_type, ...)
        self.anomalies.append(anomaly)
        NewsCorrelator.watch(anomaly)
```

### Two-Model Assessment Pipeline

```python
import weave
from mistralai import Mistral

weave.init("sentinel")
client = Mistral(api_key=MISTRAL_API_KEY)

FINE_TUNED_MODEL = "ft:mistral-small-latest:sentinel-v1:xxx"
MAGISTRAL_MODEL = "magistral-medium-latest"

@weave.op
def classify_trade(scenario: str) -> dict:
    """Fast classification via fine-tuned model"""
    response = client.chat.complete(
        model=FINE_TUNED_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": scenario}
        ]
    )
    return parse_structured_output(response.choices[0].message.content)

@weave.op
def deep_reasoning(scenario: str, classification: dict) -> str:
    """Deep reasoning via Magistral, informed by classification"""
    response = client.chat.complete(
        model=MAGISTRAL_MODEL,
        messages=[
            {"role": "system", "content": MAGISTRAL_SYSTEM_PROMPT},
            {"role": "user", "content": f"""
{scenario}

PRELIMINARY CLASSIFICATION: {classification['classification']}
PUBLIC EXPLAINABILITY SCORE: {classification['pes']}
BEHAVIORAL SUSPICION SCORE: {classification['bss']}

Provide a detailed assessment. Do you agree with the preliminary classification?
What are the strongest alternative explanations?
"""}
        ]
    )
    return response.choices[0].message.content

@weave.op
def full_assessment(scenario: str) -> dict:
    """Complete two-stage assessment"""
    classification = classify_trade(scenario)
    reasoning = deep_reasoning(scenario, classification)
    return {**classification, "detailed_reasoning": reasoning}
```

Every call traced by `@weave.op` -- judges can open W&B and see the full chain.

---

## 8. Hackathon Build Plan (48-Hour Sprint)

### Pre-Hackathon Prep

**There is no pre-hackathon. The hackathon is live. All prep happens inside the 48 hours.**

The Index research that would ideally be pre-work gets handled by an **autonomous research agent** running in the background while the core pipeline is built. This agent uses Mistral Large + web search to find, structure, and classify historical cases of suspicious Polymarket activity, outputting structured Index entries without human intervention. Details in the build plan below.

### Saturday Feb 28: Build Day 1

**9:00-10:00 | Welcome + Briefing + Setup Sprint**
- [ ] Listen for announcements, confirm API access, note any surprise prize categories
- [ ] Initialize repo, set up Mistral API key, ElevenLabs key, W&B project
- [ ] **Launch the Index Research Agent** (see below) -- this runs autonomously in background for the rest of the day while you build

**The Index Research Agent (runs autonomously):**
A script that uses Mistral Large + web search (or manual search feeding results to Mistral) to find and structure historical cases of suspicious Polymarket activity. It searches for "Polymarket insider trading," "Polymarket suspicious wallet," "Polymarket front-running" across crypto press (The Block, CoinDesk, Decrypt), Twitter/X threads, and Reddit. For each case found, it extracts contract details, price/volume context, news correlation, wallet info, and generates a preliminary classification with PES/BSS scores. Output: structured JSON Index entries saved to a file. Target: 10-20 cases by end of day. This agent is itself a demo of Mistral's agent capabilities.

**10:00-12:00 | Data Layer + Training Data Generation (2 hrs)**
- [ ] Build Polymarket API client (fetch contracts, prices, volumes)
- [ ] Build RSS feed ingester (10 sources, timestamped articles)
- [ ] **Generate 500 training examples using Mistral Large meta-prompt**
- [ ] Store data in simple in-memory structures (no DB needed for hackathon)
- [ ] Start W&B logging, start screen recording for Vibe prize

**12:00-1:00 | Lunch**

**1:00-1:30 | Submit Fine-Tuning Job**
- [ ] **Format training data as JSONL, upload, submit fine-tuning job**
- [ ] Fine-tuning runs in background for the next 2-4 hours

**1:30-4:00 | Anomaly Detection + News Correlation (2.5 hrs)**
- [ ] Implement ContractMonitor class (baseline computation, spike detection)
- [ ] Implement NewsCorrelator (topic matching using Mistral Small)
- [ ] Build temporal correlation logic (gap computation)
- [ ] Test with historical data: can it detect known suspicious patterns?
- [ ] This is the core -- spend the time here to get it right

**4:00-6:00 | AI Assessment Layer (2 hrs)**
- [ ] Build Magistral reasoning prompt for pattern assessment
- [ ] Build SAR generator using Mistral Large function calling
- [ ] Set up ChromaDB for news archive RAG
- [ ] **When fine-tuned model is ready: swap it in, build two-model pipeline**
- [ ] Test end-to-end: anomaly -> correlation -> classification -> assessment -> SAR

**6:00-7:00 | Dinner**

**7:00-11:00 | Dashboard + Visualization (4 hrs)**
- [ ] Build surveillance feed view (live monitoring table)
- [ ] Build anomaly deep-dive view (split timeline: price chart + news timeline)
- [ ] Build the "gap visualization" (the visual evidence of information asymmetry)
- [ ] **Build the 2x2 classification grid (PES vs. BSS)**
- [ ] Connect backend to frontend via API
- [ ] Test full pipeline live

**11:00 PM | Assessment:**
If core pipeline works: sleep, tackle voice + Arena + polish tomorrow.
If behind: focus on making one complete anomaly detection + classification work perfectly.

### Sunday Mar 1: Build Day 2

**9:00-12:00 | Voice + Index + Arena + Polish (3 hrs)**
- [ ] ElevenLabs voice alerts for detected anomalies
- [ ] Voxtral voice Q&A for querying the system
- [ ] **Run evaluation: fine-tuned vs. base vs. Magistral. Log to W&B.**
- [ ] **Weave trace the full two-model pipeline**
- [ ] **Import Index Research Agent output -- review, curate, and load into dashboard**
- [ ] **Build Index statistics dashboard and search/filter UI**
- [ ] **Build Sentinel Arena** (evidence card display + agree/disagree voting + consensus dashboard + 5 pre-loaded cases)
- [ ] UI polish (severity colors, animations, responsive)

**12:00-1:00 | Lunch + Pitch Rehearsal**

**1:00-3:00 | Demo Prep (2 hrs)**
- [ ] Seed the system with 2-3 pre-analyzed historical examples
- [ ] **Add the 2x2 grid + Arena consensus dashboard to the pitch**
- [ ] Record backup demo video
- [ ] Write comprehensive README
- [ ] Final W&B dashboard screenshot
- [ ] Practice pitch (aim for 3 minutes)
- [ ] Prepare for judge Q&A

**3:00-5:00 | Presentations**

---

## 9. The Demo Strategy

### Demo Flow (3 minutes)

**[0:00-0:15] HOOK**
"On February 12th, someone put $1.8 million into a Polymarket contract about US trade policy. Six hours later, Reuters broke the news. By then, that position was worth $2.4 million. Nobody noticed. Until now."

**[0:15-0:30] WHAT IS IT**
"Sentinel is the first AI-powered market integrity monitor for prediction markets. It watches every trade, correlates it with every news event, and flags when someone knew something before the rest of us. And it can tell the difference between someone who had classified intelligence and someone who just reads flight-tracking data better than you do."

**[0:30-1:00] LIVE DEMO: Detection**
Show surveillance dashboard with live contracts being monitored. Click into a flagged anomaly (pre-seeded historical example). Show the split timeline: trading spike on the left, news break on the right.

**[1:00-1:45] LIVE DEMO: Classification**
Show fine-tuned model output for Wallet A: "INSIDER, confidence 0.92, public signal score 0.15."
Show fine-tuned model output for Vivaldi007: "OSINT_EDGE, confidence 0.88, public signal score 0.72."
Show Magistral's deeper reasoning confirming the classification.
**The moment:** "Same market. Same news event. Same profit. But our system knows one is a probable insider and the other is a legitimate trader. That distinction is what regulators need."

**[1:45-2:15] VOICE + REPORT**
ElevenLabs reads the alert. Show downloadable integrity report with both classifications.

**[2:15-2:45] TECHNICAL DEPTH + INDEX + ARENA**
"We fine-tuned Mistral Small on 500 game-theoretic trade analysis examples. Under the hood, Sentinel uses 6 Mistral models in a detection pipeline."
Flash W&B: training curves, evaluation comparison, Weave traces.
Flip to the Sentinel Index: "Every case flows into the Sentinel Index -- the first curated database of prediction market insider trading. We've already indexed [X] cases. This is the largest structured collection of prediction market integrity violations that exists anywhere."
Show the Index stats dashboard -- cases by classification, by category, total estimated insider profit.
Flip to Arena: "And we built a human-in-the-loop validation layer. Sentinel presents its classifications, humans vote on whether they agree. Here's what happened when we ran it during this hackathon."
Show the consensus dashboard -- high agreement on obvious cases, split opinions on the hard ones.

**[2:45-3:00] CLOSE**
"Prediction markets need integrity infrastructure. Sentinel watches the market, understands the game, and keeps the receipts. We built the SEC for prediction markets -- complete with its first case database. In 48 hours. On Mistral."

### Backup Demo Plan

If live data isn't cooperating, have 3 pre-analyzed historical examples ready. If fine-tuning failed, show Magistral with few-shot examples performing the same classification. The story is just as compelling either way.

---

## 10. Index Seeding Strategy (Autonomous Research Agent)

Since the hackathon is live, Index seeding is handled by an autonomous research agent launched in the first hour and running in the background throughout Day 1.

**The Agent's Job:**
Search the web for documented cases of suspicious Polymarket activity, extract structured data, classify each case, and output Index-ready JSON entries. This is itself a compelling demo of Mistral's agent capabilities.

**Search Targets:**
1. **Iran strike betting patterns (Feb 2026)** -- Wallet A, Vivaldi007, anoin123, Roeyha2026, and other flagged wallets (documented extensively in crypto press)
2. **Axiom/ZachXBT (Feb 2026)** -- predictorxyz and other trades. Confirmed insider by ZachXBT himself.
3. **US election betting patterns (Nov 2024)** -- widely reported unusual activity, large whale wallets, French trader narrative
4. **Trump tariff markets (Jan-Feb 2026)** -- high volume, frequent news
5. **Crypto regulatory announcements** -- SEC actions, ETF approvals
6. **Any geopolitical event** where Polymarket prices moved before official announcements

**Search Queries the Agent Runs:**
"Polymarket insider trading," "Polymarket suspicious wallet," "Polymarket front-running," "Polymarket whale trading," "prediction market manipulation," "Polymarket [specific event] before news"

**Agent Output Format:** One structured JSON Index entry per case (matching the schema in Section 5.7). The agent flags confidence level on each entry -- HIGH for cases with published wallet data and confirmed news correlation, MEDIUM for cases with partial evidence, LOW for cases based only on community speculation.

**Human Review:** Sunday morning, review the agent's output. Curate the best 15-20 cases. Discard low-confidence junk. Load into the Index. This should take 30-45 minutes.

**Target:** 10-20 curated Index cases by demo time. Even 10 real, structured cases is more than anyone has ever assembled in one place.

**The pitch line:** "While we built the detection pipeline, we had an autonomous Mistral agent researching and cataloging every documented case of suspicious prediction market activity it could find. The Sentinel Index now contains [X] structured cases. This is the largest curated collection of prediction market integrity data that exists."

---

## 11. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Polymarket API rate limits or downtime | MEDIUM | HIGH | Cache aggressively; have pre-fetched historical data; build "replay mode" |
| No live anomalies during demo window | HIGH | HIGH | Pre-seed with historical examples; the system's value is showing past detection |
| Fine-tuning fails or quality is poor | MEDIUM | MEDIUM | Use Magistral with full prompt + few-shot examples. Demo still works. Classification still happens. |
| Fine-tuned model gives bad classifications | LOW | MEDIUM | Run both fine-tuned + Magistral. Show Magistral as primary, fine-tuned as "fast triage." |
| Training data is too synthetic | MEDIUM | MEDIUM | The 3 gold examples are from real, published events. Lean on these in the demo. |
| False positives undermine credibility | MEDIUM | HIGH | Show confidence scores; always present alternatives; "flagging for investigation, not conviction" |
| Judges question legality/ethics | MEDIUM | MEDIUM | Frame as market integrity (not surveillance of individuals); all public data; compare to SEC surveillance |
| Judges don't understand game theory | LOW | MEDIUM | The 2x2 grid is visual and intuitive even without terminology. Lead with the grid, not the theory. |
| News correlation is too loose | MEDIUM | HIGH | Use Mistral Small with tight prompts; require >0.8 confidence for correlation |
| Scope creep | MEDIUM | LOW | Hard scope boundary: Polymarket API data only. No on-chain analysis. |

---

## 12. Evaluation Criteria Mapping

### Impact (25%)
"Prediction markets are becoming critical information infrastructure. $3.5B was traded on Polymarket in 2024 alone. If insiders can front-run news, the entire value proposition collapses. Sentinel is the integrity layer -- it detects suspicious trading, classifies the trader type, validates with human consensus, and archives every case into the first open database of prediction market manipulation. The Sentinel Index already contains [X] documented cases representing an estimated $[Y]M in suspicious profits."

Nobody else is building market surveillance for prediction markets. Nobody else is curating a structured database of cases. This is a genuinely new category with a compounding data asset.

### Technical Implementation (25%)
"We use 6 Mistral models in a detection pipeline: a fine-tuned Mistral Small for game-theoretic trade classification, Magistral for deep reasoning, Mistral Large for structured report generation, base Mistral Small for real-time news classification, Embed for news archive search, and Voxtral for voice input. Every detection decision is traced in Weights & Biases."

The two-model pipeline (fast triage + deep reasoning), the fine-tuning on game-theoretic scenarios, and the temporal correlation engine are genuinely sophisticated. This isn't a chatbot wrapper.

### Creativity (25%)
"Everyone at this hackathon is building tools that use AI. We built a tool that watches markets watching the world. It's meta-intelligence. And then we built a human-in-the-loop layer where people validate the AI's calls -- turning every user into a ground truth contributor. And every case goes into the Sentinel Index -- the first open database of prediction market insider trading."

The 2x2 classification grid, the split-screen gap visualization, the Index as a compounding data asset, and the Arena as validation layer are novel and immediately engaging. No one else will have a live, searchable database of real cases.

### Pitch Quality (25%)
Structure: real example hook -> detection demo -> classification demo (the wow moment) -> human validation layer -> technical depth -> close.
The wow moment: the 2x2 grid showing the same market, same news event, but fundamentally different trader types -- and the AI classifying them correctly, backed by human consensus.

---

## 13. Judge Q&A Preparation

**"Is insider trading on Polymarket actually illegal?"**
"The legal framework is evolving. The CFTC has taken enforcement action against Polymarket before. But our tool doesn't require illegality to be valuable -- it detects information asymmetry and classifies the type, which is useful regardless of legal status. Think of it as a transparency tool for an emerging market."

**"How do you handle false positives?"**
"Every detection includes a confidence score, PES/BSS scores, and alternative explanations. The fine-tuned model outputs a classification with confidence, and Magistral provides counter-arguments. We explicitly tell the user 'here are the reasons this might NOT be suspicious.' The system flags for investigation, not conviction."

**"What's your accuracy?"**
"On our held-out test set of 50 examples, the fine-tuned model achieves X% classification accuracy, compared to Y% for base Mistral Small with few-shot prompting and Z% for Magistral zero-shot. The temporal correlation -- did a market move before news broke? -- is binary and verifiable."

**"Couldn't someone just use Twitter rumors to predict markets?"**
"That's exactly one of our classification categories. An OSINT_EDGE trader processes public signals (including social media) faster than the market. Our system checks the public signal landscape and distinguishes between 'market moved because of a viral tweet' (OSINT_EDGE) and 'market moved with no public signal' (potential INSIDER). The absence of public information is what makes a detection interesting."

**"What data do you have access to?"**
"All public data. Polymarket's API is open. News feeds are public RSS. Wallet behavior data is from published analyses. We don't access private order book data, personal information, or blockchain wallet identities. This is OSINT-level surveillance using publicly available information."

**"Why fine-tune rather than just prompt Magistral?"**
"Two reasons. First, speed: the fine-tuned Small model classifies in under a second vs. Magistral's multi-second reasoning. For real-time monitoring across hundreds of contracts, that matters. Second, consistency: fine-tuning produces structured, calibrated outputs (PES/BSS scores) that are machine-parseable. We use both together -- fast triage + deep reasoning."

**"How big is the Index, and where does the data come from?"**
"We've seeded the Sentinel Index with [X] cases from published reports, crypto press, and community research -- every case where someone publicly flagged suspicious Polymarket activity, we structured and classified it. From here, every new anomaly Sentinel detects automatically enters the Index, and human validation from the Arena upgrades case statuses. This is the first time anyone has aggregated prediction market integrity data into a single, searchable, structured database. The Index grows with every market event."

**"What stops this from being a witch hunt?"**
"Three things. First, every case includes alternative explanations and confidence scores -- we're explicit about uncertainty. Second, the four-class system means the Index doesn't just collect accusations; it distinguishes between insiders, OSINT traders, fast reactors, and speculators. Most flagged cases will be legitimate trading, and we classify them as such. Third, the human-in-the-loop Arena adds consensus validation. Cases where humans and AI disagree are marked DISPUTED, not CONFIRMED. This is designed for investigation, not conviction."

---

## 14. Competitive Landscape

**For traditional markets (stocks):** NASDAQ Market Surveillance, SMARTS, Eventus -- multi-million dollar enterprise platforms. None touch prediction markets.
**For crypto:** Chainalysis, Elliptic -- blockchain forensics, not market microstructure.
**For prediction markets:** Nothing public. Polymarket has internal tools but no public-facing integrity monitoring with trader classification or case archival.
**For data/databases:** No structured, searchable database of prediction market insider trading cases exists. Coverage is fragmented across Twitter threads, news articles, and Reddit posts. The Sentinel Index is the first attempt to aggregate and standardize this information.

**Sentinel's position:** First-of-its-kind for an emerging asset class. The OSINT-vs-insider distinction is the analytical moat. The Index is the data moat -- once you have the largest collection of documented cases, you become the citation source.

---

## 15. Post-Hackathon Vision

1. **Scale the Index:** Grow from 20-30 cases to hundreds through continuous monitoring and community contributions. Become the canonical reference for prediction market integrity data.
2. **Platform expansion:** Add Kalshi, Metaculus, PredictIt, and international prediction markets to both detection and the Index.
3. **On-chain analysis:** Wallet clustering on Polygon to identify coordinated trading groups, adding richer wallet behavior data to Index entries.
4. **Real-time alerting:** Telegram/Discord bot that pushes anomaly alerts to subscribers.
5. **API for platforms:** Polymarket, Kalshi integrate Sentinel as their compliance/surveillance layer, with Index access for auditing.
6. **Regulatory toolkit:** Package the Index data for CFTC, SEC, or international equivalents. The structured case database is exactly what regulators need to justify oversight.
7. **Journalist tool:** Exportable reports and Index search for investigative journalism. "Search all INSIDER-classified cases involving geopolitics with >$500K estimated profit."
8. **Arena as ground truth engine:** Crowdsourced human validation that builds labeled datasets for continuous model improvement, with consensus scores feeding back into Index entries.
9. **Community contributions:** Allow researchers and journalists to submit cases to the Index with evidence, creating a collaborative integrity monitoring ecosystem.

**Revenue model:** Freemium. Free tier: browse the Index, view detected anomalies, vote in Arena. Pro: real-time alerts, full Index API access, custom monitoring rules, export capabilities. Enterprise: white-label for platforms, regulatory reporting, bulk Index data access, human consensus data.

---

## 16. Definition of Done (Minimum Viable Demo)

**Must have:**
- [ ] Polymarket API ingestion (active contracts, prices, volumes)
- [ ] RSS news feed ingestion with timestamps (at least 5 sources)
- [ ] Anomaly detection (volume spike + price jump detection)
- [ ] News-to-contract matching (Mistral Small classification)
- [ ] Temporal gap computation (anomaly time vs. news time)
- [ ] Fine-tuned model classifying at least one flagged anomaly (INSIDER/OSINT_EDGE/FAST_REACTOR/SPECULATOR)
- [ ] Magistral assessment confirming or challenging the classification
- [ ] **Sentinel Index seeded with 10+ cases from research agent output (curated)**
- [ ] Dashboard showing surveillance feed with severity indicators and classifications
- [ ] One complete anomaly deep-dive with split timeline + 2x2 classification grid
- [ ] W&B trace of full detection + classification pipeline

**Should have:**
- [ ] **Index statistics dashboard (cases by classification, category, total estimated profit)**
- [ ] **Index search and filter UI**
- [ ] ElevenLabs voice alert for anomalies
- [ ] Voxtral voice Q&A
- [ ] 2-3 pre-analyzed historical examples covering all four classification quadrants
- [ ] Structured SAR output (downloadable JSON/PDF)
- [ ] Fine-tuning evaluation comparison (fine-tuned vs. base vs. Magistral) logged in W&B
- [ ] Sentinel Arena with 5 pre-loaded cases and human voting

**Nice to have:**
- [ ] Arena with live human voting during presentations and real-time consensus display
- [ ] **Arena consensus scores flowing back into Index entries (CONFIRMED/DISPUTED status)**
- [ ] **Index entries auto-generated from live detection pipeline**
- [ ] **20-30+ total indexed cases**
- [ ] Cross-market correlation detection (related contracts moving together)
- [ ] Geographic map overlay showing event locations
- [ ] Real-time monitoring animation in dashboard

---

## APPENDIX A: Prize Track Win Probability & Strategy

### Track-by-Track Analysis

**1. Global Winner ($10K cash + $15K credits + Mistral hiring opportunity)**
**Win Probability: 15-20%**
This is the hardest prize -- you're competing against 1000+ hackers across 7 locations, and the global winner is selected from location winners. Sentinel's concept is strong (genuinely novel, real-world impact, deep technical implementation), but the bar here is "best project in the entire hackathon." The narrative is compelling and the demo has multiple wow moments, which helps. The biggest risk is that a team with a more polished, simpler product with a slicker demo beats you on presentation. Your edge: nobody else will build anything close to this concept, and the fine-tuning + Index + Arena combination shows unusual depth.
**Key to winning:** Flawless 3-minute pitch. The gap visualization must land immediately. The OSINT-vs-insider classification must feel like a revelation. Practice the pitch 5+ times.

**2. 1st Place at Your Location ($1.5K + $3K credits)**
**Win Probability: 25-35%**
More winnable. You're competing against maybe 100-200 people at one location. Sentinel is a top-tier concept for any hackathon. The main risk is execution -- if the demo breaks or the pipeline isn't end-to-end functional, a simpler but polished project wins. Your edge: the concept is so differentiated that even a rough demo is memorable.
**Key to winning:** End-to-end pipeline working. One clean anomaly deep-dive. The 2x2 grid populated with real cases.

**3. Best Vibe Usage (Branded AirPods)**
**Win Probability: 20-30%**
This is about showing AI-assisted development process. You need screen recordings of yourself building with AI tools (Cursor, Claude, etc.). It's low effort but you MUST start recording from minute one. Many teams forget. The winning entry usually shows the most impressive "AI built this" narrative.
**Key to winning:** Start screen recording immediately. Use AI coding assistants visibly. Capture a few "wow the AI just built that" moments. Submit a compelling 2-3 minute compilation.

**4. Best Use of ElevenLabs ($2K credits per team member)**
**Win Probability: 35-45%**
One of your strongest tracks. Most teams bolt on ElevenLabs as an afterthought -- a text-to-speech wrapper on a chatbot. Sentinel's voice alerts are genuinely functional: "Alert: High-severity anomaly detected on the US-Canada tariff contract..." read in a professional, urgent tone is immediately compelling. Add Voxtral voice input for querying the system and you have a complete voice loop. ElevenLabs sponsors want to see their product used in a way that feels native and essential, not bolted on.
**Key to winning:** The voice alert must sound like a Bloomberg terminal alert -- professional, urgent, information-dense. Demo it live. Configure a serious, newscaster-like tone. If you can get the query loop working ("What's the most suspicious contract right now?" -> spoken response), that's the clincher.

**5. Best Video Game Project (Branded GameBoy Color)**
**Win Probability: 0%**
Not applicable. Skip entirely.

**6. Best Use of Agent Skills - Hugging Face (Reachy Mini robot)**
**Win Probability: 30-40%**
Another strong track. Sentinel IS an autonomous agent -- it monitors, detects, correlates, classifies, and reports without human intervention. The Index Research Agent running in the background adds another autonomous layer. HF judges want to see multi-step reasoning, tool use, and genuine autonomy -- not a chatbot with a fancy prompt. Sentinel's pipeline (ingest data -> detect anomaly -> correlate news -> classify trader -> generate report -> archive to Index) is a textbook agentic workflow.
**Key to winning:** Show the full autonomous chain in W&B traces. Emphasize that the system runs without human input. The Index Research Agent autonomously researching and cataloging cases is a strong secondary proof point. Frame it as "an agent that never sleeps, watching every trade on every contract."

**7. Next Unicorns - Giant (VC pitch opportunity)**
**Win Probability: 30-40%**
This is about business viability. Sentinel has a clear story: prediction markets are growing, integrity is a real problem, nobody else is building this, there's a regulatory tailwind (CFTC has already acted on Polymarket), and the Index creates a compounding data moat. The revenue model is clean (freemium SaaS + enterprise for platforms). VC judges want to see a market that's big and growing, a product with a moat, and a team that understands the business. The fine-tuning and game-theory framing might be too technical for this audience -- lead with the market size and the "Bloomberg Terminal for prediction market integrity" analogy.
**Key to winning:** Know your market numbers ($3.5B traded on Polymarket in 2024, growing rapidly). Have the revenue model ready. Emphasize the Index as the moat. "Once we have the largest database of documented cases, we become the citation source for every regulator, journalist, and platform." That's the line VCs want to hear.

**8. Best Architectural Modification - Tilde ($500 cash + hiring opportunity)**
**Win Probability: 40-50%**
Your highest-probability win. The fine-tuned Mistral Small model is exactly what this track rewards. Most teams will use Mistral models off-the-shelf via API. You're fine-tuning one. The two-model pipeline (fast triage via fine-tuned Small + deep reasoning via Magistral) is a genuine architectural choice with clear rationale. The evaluation comparison (fine-tuned vs. base vs. Magistral) logged in W&B is exactly the kind of evidence Tilde wants to see. The game-theoretic classification task is non-trivial and domain-specific.
**Key to winning:** The W&B eval chart showing fine-tuned Small beating base Small and approaching Magistral. Explain the architectural rationale clearly: "Fast triage at the edge, deep reasoning when it matters. The fine-tuned model runs in under a second. Magistral takes 5-10 seconds. For real-time monitoring of hundreds of contracts, that difference matters."

**9. W&B Global Track**
**Win Probability: 25-35%**
W&B wants to see their platform used deeply -- not just basic logging, but Weave traces of agent reasoning chains, fine-tuning metrics, eval dashboards. Sentinel naturally produces rich traces: the detection pipeline, the two-model classification, the fine-tuning comparison. W&B judges love it when their product is integral to the story, not an afterthought.
**Key to winning:** Start W&B logging from hour one. Use `@weave.op` decorators on every pipeline function. Have a clean W&B dashboard ready for demo: fine-tuning curves, eval comparison table, trace of a full detection chain. The line "every detection decision is traced in W&B so you can audit the auditor" should be in the pitch.

### Summary Table

| Track | Win Probability | Effort to Optimize | Priority |
|-------|----------------|-------------------|----------|
| Best Architectural Modification (Tilde) | 40-50% | LOW (fine-tuning already planned) | **#1** |
| Best Use of ElevenLabs | 35-45% | LOW (2-3 hrs) | **#2** |
| Best Use of Agent Skills (HF) | 30-40% | LOW (already building an agent) | **#3** |
| Next Unicorns (Giant) | 30-40% | LOW (pitch prep, no extra code) | **#4** |
| 1st Place at Location | 25-35% | HIGH (full pipeline must work) | **#5** |
| W&B Global Track | 25-35% | LOW (logging from day one) | **#6** |
| Best Vibe Usage | 20-30% | VERY LOW (just record screen) | **#7** |
| Global Winner | 15-20% | VERY HIGH (everything perfect) | **#8** |

---

## APPENDIX B: Implementation Priority Guide

The goal: maximize prize tracks you're competitive for while ensuring a working demo. Features ranked by (prize impact x demo impact) / implementation effort.

### TIER 1: NON-NEGOTIABLE FOUNDATION (Hours 1-8)
*If these don't work, nothing else matters.*

**1. Polymarket API ingestion + data storage** (2 hrs)
Fetch active contracts, price history, volume data. Store in memory. This is the oxygen for everything else.
*Blocks: everything*

**2. Anomaly detection engine** (2 hrs)
Volume spike detection (3x baseline), price jump detection (>15pp in 2hrs). Don't over-engineer the statistics -- Z-scores on rolling windows are fine.
*Blocks: the entire demo narrative*

**3. News feed ingestion + correlation** (2 hrs)
RSS feeds from 5-10 sources. Mistral Small classifies relevance. Temporal gap computation.
*Blocks: the gap visualization, which is the core demo moment*

**4. Fine-tuning job submitted** (1.5 hrs)
Generate 500 training examples via Mistral Large meta-prompt (1 hr). Format, upload, submit (30 min). Then forget about it -- trains in background 2-4 hours. The single highest-ROI action: 1.5 hours of work unlocks the Tilde track (your highest-probability win).
*Blocks: Tilde prize, two-model pipeline*

**5. Dashboard with gap visualization** (2 hrs)
Split-screen timeline: price/volume chart left, news timeline right, gap highlighted. This single view IS your product. Everything else supports this visual.
*Blocks: every demo, every pitch*

### TIER 2: PRIZE MULTIPLIERS (Hours 8-16)
*Each makes you competitive for an additional prize track with low effort.*

**6. Two-model classification pipeline** (1.5 hrs)
Fine-tuned Small -> Magistral deep reasoning. The 2x2 grid with at least 2 real cases.
*Unlocks: Tilde track; dramatically strengthens main podium*

**7. W&B logging + Weave tracing** (1 hr spread across build)
`@weave.op` decorators on pipeline functions. Fine-tuning metrics. Eval comparison dashboard. Weave into code as you build, don't bolt on at end.
*Unlocks: W&B Global Track*

**8. ElevenLabs voice alerts** (1.5 hrs)
Professional urgent voice. Alert template. Trigger on anomaly detection. Add Voxtral voice input if time.
*Unlocks: ElevenLabs track*

**9. Screen recording for Vibe** (0 hrs active work)
Start OBS from minute one. Compile highlight reel Sunday.
*Unlocks: Vibe track*

**10. Launch Index Research Agent** (1 hr setup, then autonomous)
Search queries -> Mistral Large -> structured Index entries. Launch and forget. Curate Sunday morning.
*Unlocks: strengthens Agent Skills track; provides Index data*

### TIER 3: DEMO POLISH (Hours 16-30)
*Separates "good project" from "winning project."*

**11. SAR generator with structured output** (1 hr)
Mistral Large function calling -> structured JSON report. Downloadable.

**12. Index statistics dashboard** (1.5 hrs)
Import agent output. Stats view: cases by classification, category, total profit. Search/filter.

**13. Arena human validation UI** (2 hrs)
Evidence cards, agree/disagree buttons, consensus display. 5 pre-loaded cases. Streamlit.

**14. Voxtral voice Q&A** (1 hr)
Voice input -> Mistral -> ElevenLabs spoken response. Completes the voice loop for ElevenLabs track.

### TIER 4: IF TIME ALLOWS (Hours 30-38)
*Don't sacrifice pitch prep for these.*

**15. Cross-market correlation detection** (2 hrs)
**16. Arena consensus flowing back to Index** (1 hr)
**17. UI animations and polish** (1.5 hrs)

### TIER 5: SACRED AND UNTOUCHABLE (Hours 38-48)
*Do not build features during this time.*

**18. Seed demo with 2-3 bulletproof examples** (1 hr)
Pre-load your best cases so the demo never depends on live data.

**19. Record backup demo video** (30 min)

**20. Practice pitch 5+ times** (1.5 hrs)
Time it. Cut to 3 minutes. Nail transitions. Know exactly when to click what.

**21. Judge Q&A prep** (30 min)

**22. Write README** (30 min)

### The Critical Path

```
HOUR 1:   Screen recording ON + Index Research Agent launched + W&B init
          |
HOURS 1-3: Polymarket API + RSS feeds + training data generation
          |
HOUR 3:   Submit fine-tuning job ──────────────────────────┐
          |                                                 | (background)
HOURS 3-6: Anomaly detection + news correlation engine      |
          |                                                 |
HOURS 6-8: Dashboard + gap visualization                    |
          |                                                 |
HOURS 8-10: Fine-tuned model ready <────────────────────────┘
           Two-model pipeline + 2x2 grid
          |
HOURS 10-12: ElevenLabs voice alerts
          |
HOURS 12-14: SAR generator + W&B traces polished
          |
          ─── SLEEP ───
          |
HOURS 24-27: Index curation + stats dashboard
          |
HOURS 27-30: Arena UI
          |
HOURS 30-34: Voxtral voice Q&A + UI polish
          |
HOURS 34-38: Demo seeding + backup video
          |
HOURS 38-48: PITCH PREP ONLY. ZERO NEW FEATURES.
```

### If Things Go Wrong: Triage Decisions

**"Polymarket API is down or rate-limited"**
Use cached/pre-fetched data. Build "replay mode" from saved data. Don't waste time fighting the API.

**"Fine-tuning job failed"**
Use Magistral with full system prompt + 3 gold few-shot examples. You lose the Tilde track but everything else still works.

**"It's hour 8 and I don't have a working dashboard"**
Drop to Streamlit immediately. Abandon React. Functional in 2 hours. Ugly but working.

**"It's hour 12 and the detection pipeline doesn't work end-to-end"**
Hard-code 3 historical examples as pre-analyzed cases. Build dashboard around showing these with classification output. You're demoing classification capability, not live detection. Story still works.

**"It's Sunday morning and too many features are half-built"**
Kill everything that isn't: (1) one working anomaly deep-dive with gap visualization, (2) the 2x2 classification grid with at least 2 cases, (3) one voice alert. Three perfect features beat ten broken ones.
