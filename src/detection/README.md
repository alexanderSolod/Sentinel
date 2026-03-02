# Detection Engine

Everything that runs before the AI classification. This module flags suspicious trades, profiles wallets, clusters coordinated behavior, and extracts the feature vectors that the [classification pipeline](../classification/README.md) uses to make decisions.

## How it fits together

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

## Anomaly detector (`anomaly_detector.py`)

Three detectors flag trades for further analysis:

### VolumeDetector
Z-score based volume spike detection. Flags trades where volume exceeds 3x the rolling baseline.

### PriceDetector
Detects price jumps exceeding 15 percentage points between `price_before` and `price_after`.

### FreshWalletDetector
Confidence scoring for fresh wallets:
- Nonce <= 5 (very few on-chain transactions)
- Account age < 48 hours
- Outputs a 0-1 confidence score

## Wallet profiler (`wallet_profiler.py`)

### WalletProfiler
Aggregates wallet trading history: total trade count and volume, win rate, market diversity, and activity timeline.

### FundingChain
Traces where a wallet's money came from. Checks against a known address registry (CEXes, DEXes, mixers), counts the hops from a known entity, and flags risk signals: `fresh_wallet`, `high_win_rate`, `mixer_funded`.

## Cluster analysis (`cluster_analysis.py`)

### SniperDetector
Uses **DBSCAN** to detect coordinated wallet groups. Looks for wallets entering the same market within minutes of each other, taking similar position sizes, betting in the same direction.

The Iran Strike case was caught by a **6-wallet cluster** that all bet the same way within a tight time window.

### CompositeRiskScorer
Combines wallet age, trade count, win rate, cluster membership, and timing into a single 0-100 risk score. Applies multiplicative bonuses when multiple signals converge — a fresh wallet in a cluster with perfect win rate scores much higher than any one of those signals alone.

## Feature extraction (`features.py`)

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

## Random forest classifier (`rf_classifier.py`)

### RFClassifier
- **300 estimators** with PCA dimensionality reduction
- Trained on the 13-feature vectors
- Outputs `rf_score` (0-1) — probability of suspicious activity
- Reports `top_features` — which features contributed most to the prediction

Runs before the AI classification. High RF scores push the BSS up in Stage 1 triage.

## Game theory engine (`game_theory.py`)

### GameTheoryEngine
Behavioral analysis based on information-theoretic metrics:

Measures entropy across 5 dimensions: trade timing, market selection, win rate, position sizing, and hour-of-day patterns. A wallet that always wins, always trades at the same time, and never diversifies has suspiciously low entropy.

Maps behavioral fingerprints to known player archetypes and flags anomalous patterns (e.g., perfect win rate with zero timing variance).

**Output:**
- `game_theory_suspicion_score` (0-100)
- `best_fit_type` — closest player archetype
- `entropy_anomaly` — boolean flag
- `pattern_confidence` — how well the behavior fits the assigned type

## Autoencoder (`autoencoder.py`)

### TradingAutoencoder
Learns to reconstruct "normal" trading patterns. When it can't reconstruct a trade well, that trade is probably anomalous. Outputs a normalized anomaly score (0-1). Built on pure numpy — no torch/tensorflow dependency.

## Streaming detector (`streaming_detector.py`)

### StreamingAnomalyDetector
The online version of anomaly detection for the real-time pipeline. Maintains rolling statistics (mean, variance) per market, updates incrementally as trades arrive, and flags anything that blows past dynamic thresholds.

## 5-gate false positive cascade (`fp_gate.py`)

### FalsePositiveGate
Keeps noise out of the AI pipeline. Five gates in sequence, each casting a weighted vote:

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
Tracks the false positive rate over time by recording (predicted, actual) pairs from arena votes. Target is < 10% FPR. Flags when the model needs retraining.

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
