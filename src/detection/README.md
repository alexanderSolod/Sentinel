# Detection Engine

Everything that runs before the AI classification. This module flags suspicious trades, profiles wallets, clusters coordinated behavior, and extracts the feature vectors that the [classification pipeline](../classification/README.md) uses to make decisions.

## Module Overview

```
Trade Data ─→ Anomaly Detector ─→ Wallet Profiler ─→ Cluster Analysis
                                                           │
                ┌──────────────────────────────────────────┘
                ▼
        Feature Extraction (13 features)
                │
       ┌────────┼────────┐
       ▼        ▼        ▼
  Random     Game      Autoencoder
  Forest    Theory     (unsupervised)
       │        │        │
       └────────┼────────┘
                ▼
      5-Gate False Positive Cascade
                │
                ▼
         Classification Pipeline
```

## Anomaly Detector (`anomaly_detector.py`)

Three detectors that flag trades for further analysis:

### VolumeDetector
Z-score based volume spike detection. Flags trades where volume exceeds 3x the rolling baseline.

### PriceDetector
Detects price jumps exceeding 15 percentage points between `price_before` and `price_after`.

### FreshWalletDetector
Confidence scoring for fresh wallets:
- Nonce <= 5 (very few on-chain transactions)
- Account age < 48 hours
- Outputs a 0-1 confidence score

## Wallet Profiler (`wallet_profiler.py`)

### WalletProfiler
Aggregates wallet trading history:
- Total trade count and volume
- Win rate calculation
- Market diversity
- Activity timeline

### FundingChain
Traces the funding origins of a wallet:
- Known address registry (centralized exchanges, DEXes, mixers)
- Funding depth (hops from a known entity)
- Risk flags: `fresh_wallet`, `high_win_rate`, `mixer_funded`

## Cluster Analysis (`cluster_analysis.py`)

### SniperDetector
Uses **DBSCAN** (Density-Based Spatial Clustering) to detect coordinated wallet groups:
- Wallets entering the same market within minutes of each other
- Similar position sizes across a group
- Clustering by timing, market, and bet direction

The Iran Strike case was caught by a **6-wallet cluster** that all bet the same way within a tight time window.

### CompositeRiskScorer
Weighted signal aggregation with multi-signal bonuses:
- Combines wallet age, trade count, win rate, cluster membership, timing
- Applies multiplicative bonuses when multiple risk signals converge
- Outputs a composite risk score (0-100)

## Feature Extraction (`features.py`)

### FeatureExtractor
Extracts a standardized **13-feature vector** from raw anomaly data:

| Feature | Type | Description |
|---------|------|-------------|
| `wallet_age_days` | int | Days since wallet creation |
| `wallet_trade_count` | int | Total prior trades |
| `wallet_win_rate` | float | Historical win rate (0-1) |
| `is_fresh_wallet` | bool | Age < 7 days AND trades < 5 |
| `funding_risk` | float | Risk score from funding chain analysis |
| `trade_size_usd` | float | Trade size in USD |
| `position_size_pct` | float | Position as % of market liquidity |
| `z_score` | float | Volume z-score |
| `hours_before_news` | float | Hours between trade and first OSINT signal (negative = before) |
| `osint_signal_count` | int | Number of OSINT signals before trade |
| `cluster_member` | bool | Part of a DBSCAN cluster |
| `is_sniper` | bool | Entered market within minutes of creation |
| `composite_risk_score` | float | Weighted composite (0-100) |

### FeatureVector
Dataclass with helper methods:
- `.to_classifier_input()` — dict for the AI pipeline
- `.to_array()` — numpy array for ML models
- `.suspicion_heuristic` — quick rule-based suspicion score

## Random Forest Classifier (`rf_classifier.py`)

### RFClassifier
- **300 estimators** with PCA dimensionality reduction
- Trained on the 13-feature vectors
- Outputs `rf_score` (0-1) — probability of suspicious activity
- Reports `top_features` — which features contributed most to the prediction

Runs before the AI classification. High RF scores push the BSS up in Stage 1 triage.

## Game Theory Engine (`game_theory.py`)

### GameTheoryEngine
Behavioral analysis based on information-theoretic metrics:

**Entropy analysis across 5 dimensions:**
1. Timing entropy — how predictable is the wallet's trade timing?
2. Market entropy — how diverse is market selection?
3. Win rate entropy — is the win rate abnormally high?
4. Position entropy — are position sizes consistent?
5. Hour-of-day entropy — does the wallet trade at unusual hours?

**Player type mapping:**
- Maps behavioral fingerprints to known player archetypes
- Identifies anomalous entropy patterns (e.g., a "perfect" win rate with zero timing variance)

**Output:**
- `game_theory_suspicion_score` (0-100)
- `best_fit_type` — closest player archetype
- `entropy_anomaly` — boolean flag
- `pattern_confidence` — how well the behavior fits the assigned type

## Autoencoder (`autoencoder.py`)

### TradingAutoencoder
Unsupervised anomaly detection using a numpy-based autoencoder:
- Learns to reconstruct "normal" trading patterns
- High reconstruction error = anomalous behavior
- Outputs a normalized anomaly score (0-1)

No external dependencies beyond numpy.

## Streaming Detector (`streaming_detector.py`)

### StreamingAnomalyDetector
Online anomaly detection for the real-time pipeline:
- Maintains rolling statistics (mean, variance) per market
- Updates incrementally as new trades arrive
- Flags trades that exceed dynamic thresholds

## 5-Gate False Positive Cascade (`fp_gate.py`)

### FalsePositiveGate
Filters out noise before it hits the AI pipeline. Five gates in sequence, each with a weighted vote:

```
Trade ─→ Statistical (20%) ─→ RF (25%) ─→ Autoencoder (15%)
              │                    │              │
              ▼                    ▼              ▼
         Game Theory (20%) ─→ Mistral LLM (20%)
```

**Rules:**
- Each gate has a weighted vote (weights sum to 1.0)
- Score < 0.25 at any gate = **DISMISS** (early exit, classified as LEGITIMATE)
- Cumulative score >= 0.60 = **SUSPICIOUS** (escalate to classification)
- Between 0.25-0.60 = **PASS** (continue to next gate)

### FPRTracker
Tracks false positive rate over time:
- Records (predicted, actual) pairs from arena votes
- Computes FPR with a target of < 10%
- Flags when retraining is needed

## Files

| File | Purpose |
|------|---------|
| `anomaly_detector.py` | Volume, price, and fresh wallet detection |
| `wallet_profiler.py` | Trade history + funding chain tracing |
| `cluster_analysis.py` | DBSCAN sniper clustering + composite risk |
| `features.py` | 13-feature vector extraction |
| `rf_classifier.py` | Random Forest with PCA |
| `game_theory.py` | Behavioral entropy analysis |
| `autoencoder.py` | Unsupervised anomaly detection (numpy) |
| `streaming_detector.py` | Online detection for real-time pipeline |
| `fp_gate.py` | 5-gate false positive cascade + FPR tracking |
