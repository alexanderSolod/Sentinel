# Implementation Guide 1: Random Forest Transaction Classification Engine

> **Source Paper:** Neupane & Griva (2024), "A Random Forest approach to detect and identify Unlawful Insider Trading"
> **Target System:** Sentinel -- Prediction Market Integrity Monitor
> **Goal:** Replace or augment the rule-based suspicion heuristic in `src/detection/features.py` with a trained PCA-RF classifier that scores transactions as INSIDER vs. LEGITIMATE with interpretable feature importance.

---

## 1. Core Concept

The paper demonstrates that Random Forest (RF) classifiers achieve 96-99% accuracy on insider trading detection when fed properly engineered financial and behavioral features. The key insights to port to Sentinel:

1. **PCA dimensionality reduction** before RF reduces noise and decorrelates features, improving classification on high-dimensional data.
2. **Balanced datasets** (50:50 lawful/unlawful) are critical -- the paper explicitly constructs balanced training sets.
3. **Feature importance via permutation** (not just Gini impurity) reveals that **governance/ownership features** dominate after decorrelation -- analogous to Sentinel's wallet profile and behavioral features.
4. **110 features outperform 25 features** -- more signal helps, provided you control overfitting via cross-validation.

---

## 2. Feature Engineering

### 2.1 Mapping Paper Features to Sentinel's Domain

The paper uses SEC Form 4 financial features. Sentinel operates on Polymarket trades. Here is the translation table:

| Paper Feature Category | Paper Examples | Sentinel Equivalent | Source |
|---|---|---|---|
| **Ownership/Governance** | IsDirector, IsOfficer, IsTenPercentOwner | `wallet_age_days`, `is_fresh_wallet`, `funding_risk_flag`, `known_address_match` | `wallet_profiler.py` |
| **Risk/Returns** | Market Beta, Idiosyncratic Volatility, Return | `price_move_pct`, `volume_z_score`, `market_volatility_baseline` | `anomaly_detector.py` |
| **Activity Ratios** | Asset Turnover, Acquisition/Disposition | `trade_count`, `avg_position_size_pct`, `win_rate`, `buy_sell_ratio` | `wallet_profiler.py` |
| **Valuation** | Price-to-Book, Shiller P/E | `market_liquidity`, `order_book_depth`, `contract_age_days` | `polymarket_client.py` |
| **Timing** | (not in paper, added for Sentinel) | `hours_before_news`, `temporal_gap_score`, `osint_signal_count` | `correlator.py` |
| **Cluster Behavior** | (not in paper, added for Sentinel) | `cluster_id`, `cluster_size`, `sniper_flag`, `coordinated_wallet_flag` | `cluster_analysis.py` |

### 2.2 Full Feature Vector Specification

Build a `FeatureVector` with these features (extends the existing 13-feature vector in `src/detection/features.py`):

```python
@dataclass
class ExtendedFeatureVector:
    # --- Wallet Profile (analogous to Ownership/Governance) ---
    wallet_age_days: float          # Days since first transaction
    total_trade_count: int          # Lifetime trades
    win_rate: float                 # Historical accuracy (0-1)
    avg_position_size_usd: float    # Mean position in USD
    max_position_size_usd: float    # Largest single position
    unique_markets_traded: int      # Breadth of activity
    is_fresh_wallet: bool           # < 7 days old
    funding_chain_depth: int        # Hops from known exchange
    funding_risk_score: float       # 0-1 based on funding source
    known_address_match: bool       # Matches known entity registry

    # --- Trade Behavior (analogous to Activity Ratios) ---
    position_size_pct_of_market: float   # This trade vs market cap
    buy_sell_ratio_30d: float            # Buys/sells last 30 days
    concentration_score: float           # % of portfolio in one market
    time_of_day_zscore: float            # Unusual trading hour?
    trade_frequency_zscore: float        # Unusual burst of trades?

    # --- Market Signal (analogous to Risk/Returns) ---
    volume_z_score: float                # Z-score vs 7-day baseline
    price_move_pct: float                # Price change in detection window
    price_move_velocity: float           # Price change per minute
    market_liquidity_score: float        # Order book depth proxy
    contract_age_days: float             # How long market has existed
    pre_event_volume_ratio: float        # Volume before vs after event

    # --- Temporal/OSINT (Sentinel-specific, no paper analog) ---
    hours_before_news: float             # Gap between trade and news
    osint_signal_count: int              # Number of matching OSINT events
    osint_earliest_signal_hours: float   # Earliest public signal timing
    temporal_gap_category: str           # TRADE_BEFORE_INFO, TRADE_AFTER_INFO, etc.
    public_explainability_score: float   # 0-100 PES from Stage 1

    # --- Cluster Analysis (Sentinel-specific) ---
    cluster_id: Optional[int]            # DBSCAN cluster assignment
    cluster_size: int                    # Number of wallets in cluster
    sniper_flag: bool                    # Entered < 1h after market creation
    coordinated_entry_score: float       # How synchronized with cluster
    composite_risk_score: float          # Multi-signal bonus from cluster_analysis.py
```

### 2.3 Normalization

Per the paper, apply z-score normalization to all numeric features:

```python
import numpy as np

def normalize_features(feature_matrix: np.ndarray) -> np.ndarray:
    """Z-score normalize each column: (x - mean) / std"""
    means = np.mean(feature_matrix, axis=0)
    stds = np.std(feature_matrix, axis=0)
    # Avoid division by zero for constant features
    stds[stds == 0] = 1.0
    return (feature_matrix - means) / stds
```

One-hot encode categorical features (`temporal_gap_category`, `sniper_flag`, `is_fresh_wallet`, etc.) before normalization:

```python
from sklearn.preprocessing import OneHotEncoder

categorical_cols = ['temporal_gap_category', 'sniper_flag',
                    'is_fresh_wallet', 'known_address_match',
                    'coordinated_wallet_flag']
```

---

## 3. PCA Dimensionality Reduction

### 3.1 When to Use PCA

The paper shows PCA helps most when:
- Feature count is high (110 features >> 25)
- Features are highly correlated (financial ratios share variance)

For Sentinel's ~30 features, PCA is optional but useful for the visualization story. Implement both paths (with/without PCA) and compare.

### 3.2 Implementation

```python
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

def apply_pca(X_train: np.ndarray, X_test: np.ndarray,
              variance_threshold: float = 0.95):
    """
    Reduce dimensions, retaining components that explain
    >= variance_threshold of total variance.

    Paper reference: 10 PCs captured 94.76% of variance on 110 features.
    """
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    pca = PCA(n_components=variance_threshold, svd_solver='full')
    X_train_pca = pca.fit_transform(X_train_scaled)
    X_test_pca = pca.transform(X_test_scaled)

    return X_train_pca, X_test_pca, pca, scaler
```

### 3.3 Component Analysis for Explainability

After fitting PCA, extract which original features drive each component:

```python
def get_pca_loadings(pca, feature_names: list) -> dict:
    """Map each PC to its top contributing features."""
    loadings = {}
    for i, component in enumerate(pca.components_):
        sorted_idx = np.argsort(np.abs(component))[::-1]
        loadings[f'PC{i}'] = [
            (feature_names[j], round(component[j], 4))
            for j in sorted_idx[:5]  # Top 5 contributors
        ]
    return loadings
```

This feeds into Sentinel's XAI narrative generation (Stage 2 Magistral analysis).

---

## 4. Random Forest Classifier

### 4.1 Hyperparameter Search Space

The paper's optimal configuration (Table 5, 3984 transactions, 110 features):

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import RandomizedSearchCV

param_distributions = {
    'n_estimators': [100, 300, 500, 700, 1000],     # Paper: 100-1030
    'max_depth': [6, 10, 14, 18, None],              # Paper: up to 18
    'max_features': ['sqrt', 0.35, 0.5, 0.7, 0.95], # Paper: mtry 0.35-0.95
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'bootstrap': [True],
    'class_weight': ['balanced'],  # Handle any residual imbalance
}

rf = RandomForestClassifier(oob_score=True, random_state=42, n_jobs=-1)

search = RandomizedSearchCV(
    rf,
    param_distributions,
    n_iter=50,
    cv=5,                # Paper uses 5-fold CV
    scoring='f1',        # Balance precision/recall
    random_state=42,
    n_jobs=-1,
    verbose=1
)
```

### 4.2 Training Pipeline

```python
def train_classifier(X: np.ndarray, y: np.ndarray,
                     use_pca: bool = False,
                     n_repeats: int = 10):
    """
    Train RF classifier with repeated stratified k-fold.
    Paper repeats 100 times; for Sentinel, 10-20 is practical.
    """
    from sklearn.model_selection import RepeatedStratifiedKFold

    cv = RepeatedStratifiedKFold(
        n_splits=5,
        n_repeats=n_repeats,
        random_state=42
    )

    results = {
        'accuracy': [], 'tpr': [], 'tnr': [],
        'fpr': [], 'fnr': [], 'precision': [], 'f1': []
    }

    for train_idx, test_idx in cv.split(X, y):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        if use_pca:
            X_train, X_test, pca, scaler = apply_pca(X_train, X_test)

        model = RandomForestClassifier(
            **best_params,  # From hyperparameter search
            oob_score=True,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        # Compute all confusion matrix components
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        results['accuracy'].append((tp + tn) / (tp + tn + fp + fn))
        results['tpr'].append(tp / (tp + fn))  # Sensitivity/Recall
        results['tnr'].append(tn / (tn + fp))  # Specificity
        results['fpr'].append(fp / (fp + tn))   # False alarm rate
        results['fnr'].append(fn / (fn + tp))   # Miss rate
        results['precision'].append(tp / (tp + fp))
        results['f1'].append(2 * tp / (2 * tp + fp + fn))

    return {k: (np.mean(v), np.std(v)) for k, v in results.items()}
```

### 4.3 Target Metrics (from Paper Table 5)

For Sentinel, aim for the following thresholds (paper achieved these on 3984 transactions, 110 features, no PCA):

| Metric | Paper Best | Sentinel Target | Why It Matters |
|---|---|---|---|
| **Accuracy** | 99.13% | > 90% | Overall correctness |
| **FPR (False Alarm)** | 1.03% | < 10% | Don't overwhelm analysts |
| **FNR (Miss Rate)** | 0.70% | < 5% | Don't miss real insiders |
| **TPR (Sensitivity)** | 99.30% | > 90% | Catch legitimate trades correctly |
| **TNR (Specificity)** | 98.97% | > 90% | Catch insiders correctly |

Note: Paper's numbers are on SEC data with clear labels. Sentinel operates on noisier prediction market data with synthetic/Arena labels, so lower targets are realistic.

---

## 5. Feature Importance & Explainability

### 5.1 Dual Importance Method

The paper's key contribution: use BOTH Gini impurity AND permutation importance, then compare.

```python
from sklearn.inspection import permutation_importance

def get_dual_importance(model, X_test, y_test, feature_names):
    """
    Returns both MDI (Gini) and permutation-based rankings.
    Paper shows ownership/governance features rise in permutation
    ranking after decorrelation -- analogous to wallet profile
    features in Sentinel.
    """
    # Method 1: Gini Impurity (built-in, biased toward high-cardinality)
    gini_importance = dict(zip(feature_names, model.feature_importances_))

    # Method 2: Permutation Importance (model-agnostic, uses test data)
    perm_result = permutation_importance(
        model, X_test, y_test,
        n_repeats=30,
        random_state=42,
        n_jobs=-1
    )
    perm_importance = dict(zip(
        feature_names,
        perm_result.importances_mean
    ))

    return gini_importance, perm_importance
```

### 5.2 Hierarchical Clustering for Correlated Features

The paper uses Spearman rank correlation + Ward linkage to group correlated features, then picks one representative per cluster:

```python
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.stats import spearmanr
from scipy.spatial.distance import squareform

def decorrelate_features(X: np.ndarray, feature_names: list,
                         threshold: float = 0.7):
    """
    Cluster correlated features and select one representative per cluster.
    Paper uses Spearman rank correlation with Ward's minimum variance.
    """
    corr_matrix, _ = spearmanr(X)
    # Convert correlation to distance
    distance_matrix = 1 - np.abs(corr_matrix)
    dist_condensed = squareform(distance_matrix)

    Z = linkage(dist_condensed, method='ward')
    clusters = fcluster(Z, t=threshold, criterion='distance')

    # Select feature with highest variance per cluster as representative
    selected = []
    for cluster_id in np.unique(clusters):
        mask = clusters == cluster_id
        cluster_features = np.array(feature_names)[mask]
        cluster_data = X[:, mask]
        # Pick feature with highest variance
        variances = np.var(cluster_data, axis=0)
        best_idx = np.argmax(variances)
        selected.append(cluster_features[best_idx])

    return selected
```

### 5.3 Integration with Sentinel's XAI Narrative

Feed feature importance rankings into Stage 2 (Magistral) prompt context:

```python
def build_xai_context(gini_ranks: dict, perm_ranks: dict,
                      top_n: int = 5) -> str:
    """
    Generate human-readable feature importance summary
    for the Magistral deep analysis prompt.
    """
    gini_top = sorted(gini_ranks.items(), key=lambda x: -x[1])[:top_n]
    perm_top = sorted(perm_ranks.items(), key=lambda x: -x[1])[:top_n]

    lines = ["## Feature Importance Analysis (Random Forest)"]
    lines.append("\n### Gini Impurity Ranking (training-based):")
    for feat, score in gini_top:
        lines.append(f"  - {feat}: {score:.4f}")

    lines.append("\n### Permutation Importance (test-based, decorrelated):")
    for feat, score in perm_top:
        lines.append(f"  - {feat}: {score:.4f}")

    # Flag divergence (paper's key finding)
    gini_set = {f for f, _ in gini_top}
    perm_set = {f for f, _ in perm_top}
    if gini_set != perm_set:
        divergent = (perm_set - gini_set)
        lines.append(f"\n### Note: Permutation ranking elevated: "
                     f"{', '.join(divergent)}")
        lines.append("These features may be more predictive than "
                     "Gini scores suggest (correlated features mask "
                     "their importance in MDI).")

    return '\n'.join(lines)
```

---

## 6. Training Data Generation

### 6.1 Label Sources for Sentinel

The paper uses SEC court complaints for ground truth labels. Sentinel needs:

| Label Source | Label Type | Volume | Quality |
|---|---|---|---|
| **Arena Votes** | Human consensus from Arena UI | Growing over time | High (human judgment) |
| **Known Cases** | Iran strike, ZachXBT Axiom, etc. | 3-5 gold standard | Very high |
| **Synthetic** | Generated by `finetuning.py` | 500 examples | Medium (LLM-generated) |
| **Heuristic Labels** | From `suspicion_heuristic` in features.py | Unlimited | Low (bootstrapping only) |

### 6.2 Balanced Dataset Construction

Following the paper's 50:50 split:

```python
from sklearn.utils import resample

def build_balanced_dataset(df, label_col='is_suspicious',
                           target_size=None):
    """
    Paper: balanced 50:50 lawful/unlawful.
    Randomly sample from majority class to match minority.
    """
    positive = df[df[label_col] == 1]
    negative = df[df[label_col] == 0]

    minority_size = min(len(positive), len(negative))
    if target_size:
        minority_size = min(minority_size, target_size // 2)

    pos_sample = resample(positive, n_samples=minority_size,
                          random_state=42)
    neg_sample = resample(negative, n_samples=minority_size,
                          random_state=42)

    return pd.concat([pos_sample, neg_sample]).sample(
        frac=1, random_state=42
    ).reset_index(drop=True)
```

---

## 7. Integration Points with Sentinel Codebase

### 7.1 Where This Fits

```
Detection Pipeline (existing):
  anomaly_detector.py -> wallet_profiler.py -> cluster_analysis.py -> features.py
                                                                         |
                                                                    [NEW: rf_classifier.py]
                                                                         |
Classification Pipeline (existing):
  stage1_triage.py -> stage2_magistral.py -> stage3_sar.py
```

The RF classifier sits between feature extraction and AI classification. It provides:
- A **numeric suspicion score** (RF probability) that can replace or supplement the existing `suspicion_heuristic`
- A **feature importance report** that enriches Stage 2's reasoning context
- A **binary pre-screen** that can skip the Mistral API for obvious non-suspicious cases (saving API calls)

### 7.2 New File: `src/detection/rf_classifier.py`

```python
class RFClassifier:
    def __init__(self, model_path: str = None):
        self.model = None
        self.pca = None
        self.scaler = None
        self.feature_names = None

    def train(self, X, y, feature_names, use_pca=False):
        """Full training pipeline with CV and hyperparameter search."""
        ...

    def predict(self, feature_vector: ExtendedFeatureVector) -> dict:
        """
        Returns:
          {
            'rf_score': 0.87,          # P(suspicious)
            'rf_label': 'SUSPICIOUS',  # Binary classification
            'top_features': [...],      # Top 5 driving features
            'confidence': 0.92         # Model confidence
          }
        """
        ...

    def save(self, path: str): ...
    def load(self, path: str): ...
```

### 7.3 Pipeline Integration in `pipeline.py`

```python
# In SentinelPipeline.process_anomaly():

# Step 1: Extract features (existing)
features = self.feature_extractor.extract(anomaly, wallet, osint_events)

# Step 2: RF pre-classification (NEW)
rf_result = self.rf_classifier.predict(features)

# Step 3: Decide if AI classification is needed
if rf_result['rf_score'] < 0.2:
    # Very likely legitimate -- skip expensive Mistral calls
    return quick_classification(anomaly, rf_result)

# Step 4: Pass RF context to Stage 1
stage1_input = {
    **features.to_classifier_input(),
    'rf_suspicion_score': rf_result['rf_score'],
    'rf_top_features': rf_result['top_features'],
}

# Step 5: Run AI classification with enriched context
result = self.stage1.classify(stage1_input)
```

---

## 8. Evaluation Framework

### 8.1 Confusion Matrix for Sentinel's 4-Class Problem

The paper solves binary classification (lawful/unlawful). Sentinel has 4 classes. Implement a two-stage evaluation:

**Stage A: Binary** -- Is this transaction suspicious? (maps to paper directly)
**Stage B: Multi-class** -- If suspicious, which type? (INSIDER / OSINT_EDGE / FAST_REACTOR / SPECULATOR)

```python
from sklearn.metrics import classification_report, confusion_matrix

def evaluate_sentinel(y_true_binary, y_pred_binary,
                      y_true_multi, y_pred_multi):
    """
    Paper metrics (Table 1-2) adapted for Sentinel.
    """
    # Binary evaluation (paper's direct analog)
    print("=== Binary: Suspicious vs Legitimate ===")
    print(classification_report(y_true_binary, y_pred_binary,
                                target_names=['Legitimate', 'Suspicious']))

    # Multi-class evaluation (Sentinel extension)
    print("=== Multi-class: Trader Type ===")
    print(classification_report(y_true_multi, y_pred_multi,
                                target_names=['INSIDER', 'OSINT_EDGE',
                                              'FAST_REACTOR', 'SPECULATOR']))
```

### 8.2 Repeated Experiment Protocol

Following the paper's 100-repetition protocol:

```python
def run_evaluation_suite(X, y, n_repeats=20):
    """
    Paper runs 100 experiments to control variability.
    For Sentinel demo, 10-20 is sufficient to show stable metrics.
    Records mean +/- std for each metric.
    """
    all_metrics = []
    for i in range(n_repeats):
        # Resample balanced dataset each time (paper's approach)
        X_balanced, y_balanced = build_balanced_dataset(X, y)
        metrics = train_and_evaluate(X_balanced, y_balanced, seed=i)
        all_metrics.append(metrics)

    summary = {}
    for key in all_metrics[0]:
        values = [m[key] for m in all_metrics]
        summary[key] = {
            'mean': np.mean(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values)
        }
    return summary
```

---

## 9. Key Takeaways for Implementation

1. **Start with the existing 13-feature vector** from `features.py`, extend to ~30 features.
2. **Z-score normalize** all numeric features, one-hot encode categoricals.
3. **Train RF with 5-fold CV**, repeated 10-20 times for stable metrics.
4. **Use permutation importance** (not just Gini) to identify which Sentinel features actually drive detection -- this becomes the XAI story.
5. **PCA is optional** at Sentinel's feature count (~30) but useful for the visualization in the dashboard.
6. **The RF probability score** becomes a continuous "suspicion score" that can gate expensive Mistral API calls.
7. **The balanced dataset requirement** means Arena votes and known cases are precious -- every human label improves the classifier.
