# Implementation Guide 3: Real-Time Adaptive Fraud Detection Pipeline

> **Source Paper:** Nweze, Avickson & Ekechukwu (2024), "The Role of AI and Machine Learning in Fraud Detection: Enhancing Risk Management in Corporate Finance"
> **Target System:** Sentinel -- Prediction Market Integrity Monitor
> **Goal:** Implement the paper's architecture for real-time monitoring, NLP-based communication analysis, multi-source data fusion, and continuous adaptive learning -- applied to Sentinel's prediction market surveillance domain.

---

## 1. Architecture Overview

The paper describes a layered fraud detection architecture. Mapped to Sentinel:

```
Paper Layer             Sentinel Implementation              Status
-----------             -----------------------              ------
Data Aggregation   -->  Polymarket + OSINT + WebSocket       [DONE]
Real-Time Monitor  -->  main.py monitor --live               [DONE, enhance]
ML Detection       -->  RF Classifier + Game Theory          [Guide 1 & 2]
NLP Analysis       -->  OSINT text analysis + trade context  [NEW]
Deep Learning      -->  Anomaly autoencoder                  [NEW]
Feedback Loop      -->  Arena votes -> model retraining      [PARTIAL]
Alert System       -->  Dashboard + API + (voice)            [DONE]
Compliance/Audit   -->  SAR generation + Sentinel Index      [DONE]
```

This guide focuses on the **NEW** and **ENHANCE** components.

---

## 2. Real-Time Monitoring Architecture

### 2.1 Multi-Source Data Fusion

The paper emphasizes correlating **disparate data sources** to build a comprehensive view. Sentinel already ingests multiple sources; this section formalizes the fusion.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

class DataSourceType(Enum):
    POLYMARKET_TRADE = "polymarket_trade"
    POLYMARKET_PRICE = "polymarket_price"
    OSINT_RSS = "osint_rss"
    OSINT_GDELT = "osint_gdelt"
    OSINT_GDACS = "osint_gdacs"
    OSINT_ACLED = "osint_acled"
    OSINT_FIRMS = "osint_firms"
    WALLET_PROFILE = "wallet_profile"
    CLUSTER_ANALYSIS = "cluster_analysis"
    ARENA_VOTE = "arena_vote"

@dataclass
class FusedDataPoint:
    """
    Single unified data record combining all source signals.
    Paper reference: "correlate disparate data sources to create
    a comprehensive view of user activity" (Section 2.2)
    """
    timestamp: datetime
    source_type: DataSourceType
    market_id: Optional[str] = None
    wallet_address: Optional[str] = None

    # Trade data
    trade_amount_usd: Optional[float] = None
    trade_direction: Optional[str] = None
    price_before: Optional[float] = None
    price_after: Optional[float] = None

    # OSINT data
    osint_headline: Optional[str] = None
    osint_source: Optional[str] = None
    osint_severity: Optional[str] = None
    osint_keywords: list = field(default_factory=list)

    # Computed signals
    volume_z_score: Optional[float] = None
    price_move_pct: Optional[float] = None
    temporal_gap_hours: Optional[float] = None

    # Metadata
    raw_data: Optional[dict] = None


class DataFusionEngine:
    """
    Combines real-time streams from all sources into a unified
    event timeline for each market.

    Paper: "cross-reference multiple data streams to generate a
    much clearer picture of potential fraud risks" (Section 2.2)
    """

    def __init__(self, window_hours: int = 72):
        self.window_hours = window_hours
        self.event_buffer = {}  # market_id -> list[FusedDataPoint]
        self.correlation_cache = {}

    def ingest(self, data_point: FusedDataPoint):
        """Add a new data point to the fusion buffer."""
        if data_point.market_id:
            if data_point.market_id not in self.event_buffer:
                self.event_buffer[data_point.market_id] = []
            self.event_buffer[data_point.market_id].append(data_point)
            self._prune_old_events(data_point.market_id)

    def get_market_timeline(self, market_id: str) -> list[FusedDataPoint]:
        """Get all events for a market, sorted chronologically."""
        events = self.event_buffer.get(market_id, [])
        return sorted(events, key=lambda e: e.timestamp)

    def compute_cross_source_signals(self, market_id: str) -> dict:
        """
        Analyze relationships between different data sources
        for a specific market.

        Paper: "analysing not just the transaction details, but also
        the user's past behaviour, geographic location, social media
        activity, and even communications" (Section 2.2)
        """
        timeline = self.get_market_timeline(market_id)
        if not timeline:
            return {}

        trades = [e for e in timeline
                  if e.source_type == DataSourceType.POLYMARKET_TRADE]
        osint = [e for e in timeline
                 if e.source_type.value.startswith('osint')]

        signals = {}

        # Signal 1: Trade-before-OSINT ratio
        if trades and osint:
            earliest_osint = min(e.timestamp for e in osint)
            trades_before = [t for t in trades
                            if t.timestamp < earliest_osint]
            signals['trades_before_osint_pct'] = (
                len(trades_before) / len(trades) if trades else 0
            )
            signals['earliest_osint_gap_hours'] = max(0,
                (earliest_osint - min(t.timestamp for t in trades)
                ).total_seconds() / 3600
            ) if trades_before else 0

        # Signal 2: Volume acceleration
        if len(trades) >= 5:
            volumes = [t.trade_amount_usd or 0 for t in trades]
            half = len(volumes) // 2
            first_half_avg = sum(volumes[:half]) / max(half, 1)
            second_half_avg = sum(volumes[half:]) / max(
                len(volumes) - half, 1
            )
            signals['volume_acceleration'] = (
                second_half_avg / max(first_half_avg, 1)
            )

        # Signal 3: Unique wallets concentration
        wallets = set(t.wallet_address for t in trades
                     if t.wallet_address)
        signals['unique_wallets'] = len(wallets)
        if trades:
            top_wallet_trades = max(
                sum(1 for t in trades if t.wallet_address == w)
                for w in wallets
            ) if wallets else 0
            signals['top_wallet_concentration'] = (
                top_wallet_trades / len(trades)
            )

        # Signal 4: OSINT severity escalation
        severity_order = {
            'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'INFO': 0
        }
        if osint:
            severities = [severity_order.get(e.osint_severity, 0)
                         for e in osint]
            signals['max_osint_severity'] = max(severities)
            signals['osint_event_count'] = len(osint)

        return signals

    def _prune_old_events(self, market_id: str):
        """Remove events outside the rolling window."""
        cutoff = datetime.utcnow() - timedelta(hours=self.window_hours)
        self.event_buffer[market_id] = [
            e for e in self.event_buffer[market_id]
            if e.timestamp > cutoff
        ]
```

### 2.2 Streaming Anomaly Detection

The paper stresses real-time detection. Enhance Sentinel's existing WebSocket handler with an online anomaly detector:

```python
from collections import deque
import numpy as np
from datetime import timedelta

class StreamingAnomalyDetector:
    """
    Online anomaly detection that processes each trade as it arrives.
    No batch processing -- immediate scoring.

    Paper: "continuously analysing incoming data streams, organizations
    can detect anomalies, identify suspicious activities, and take
    immediate action" (Section 2.2)
    """

    def __init__(self, baseline_window: int = 1000,
                 z_threshold: float = 3.0,
                 price_threshold: float = 0.15):
        self.baseline_window = baseline_window
        self.z_threshold = z_threshold
        self.price_threshold = price_threshold

        # Rolling statistics per market
        self.market_stats = {}

    def _get_stats(self, market_id: str):
        if market_id not in self.market_stats:
            self.market_stats[market_id] = {
                'volumes': deque(maxlen=self.baseline_window),
                'prices': deque(maxlen=self.baseline_window),
                'timestamps': deque(maxlen=self.baseline_window),
                'trade_intervals': deque(maxlen=self.baseline_window),
            }
        return self.market_stats[market_id]

    def process_trade(self, trade: dict) -> dict:
        """
        Process a single incoming trade and return anomaly signals.

        Returns dict with:
          - is_anomalous: bool
          - anomaly_type: str or None
          - volume_z: float
          - price_move: float
          - interval_z: float (unusual trade timing)
          - severity: str (CRITICAL/HIGH/MEDIUM/LOW)
        """
        market_id = trade.get('market_id', 'unknown')
        stats = self._get_stats(market_id)

        amount = trade.get('amount_usd', 0)
        price = trade.get('price', 0)
        timestamp = trade.get('timestamp')

        result = {
            'is_anomalous': False,
            'anomaly_types': [],
            'volume_z': 0,
            'price_move': 0,
            'interval_z': 0,
            'severity': 'LOW',
        }

        # Volume z-score
        if len(stats['volumes']) >= 20:
            mean_vol = np.mean(stats['volumes'])
            std_vol = np.std(stats['volumes'])
            if std_vol > 0:
                result['volume_z'] = (amount - mean_vol) / std_vol
                if result['volume_z'] > self.z_threshold:
                    result['is_anomalous'] = True
                    result['anomaly_types'].append('VOLUME_SPIKE')

        # Price move
        if stats['prices']:
            last_price = stats['prices'][-1]
            if last_price > 0:
                result['price_move'] = abs(price - last_price) / last_price
                if result['price_move'] > self.price_threshold:
                    result['is_anomalous'] = True
                    result['anomaly_types'].append('PRICE_DISLOCATION')

        # Trade interval anomaly (burst detection)
        if timestamp and stats['timestamps']:
            interval = (timestamp - stats['timestamps'][-1]).total_seconds()
            stats['trade_intervals'].append(interval)

            if len(stats['trade_intervals']) >= 20:
                mean_int = np.mean(stats['trade_intervals'])
                std_int = np.std(stats['trade_intervals'])
                if std_int > 0:
                    result['interval_z'] = (mean_int - interval) / std_int
                    # High z = trade came much faster than normal
                    if result['interval_z'] > self.z_threshold:
                        result['is_anomalous'] = True
                        result['anomaly_types'].append('TRADE_BURST')

        # Severity classification
        if result['is_anomalous']:
            n_signals = len(result['anomaly_types'])
            max_z = max(abs(result['volume_z']),
                       abs(result['interval_z']))
            if n_signals >= 2 and max_z > 5:
                result['severity'] = 'CRITICAL'
            elif n_signals >= 2 or max_z > 4:
                result['severity'] = 'HIGH'
            elif max_z > self.z_threshold:
                result['severity'] = 'MEDIUM'

        # Update rolling stats
        stats['volumes'].append(amount)
        stats['prices'].append(price)
        if timestamp:
            stats['timestamps'].append(timestamp)

        return result
```

---

## 3. NLP Analysis for OSINT Enrichment

### 3.1 Concept

The paper highlights NLP as critical for analyzing unstructured data (communications, transaction narratives). For Sentinel, NLP applies to:
- OSINT news articles (matching to markets)
- Social media signals (pre-news chatter)
- Market descriptions (understanding what the contract is about)

### 3.2 Keyword and Semantic Matching

```python
import re
from collections import Counter
from typing import Optional

class OSINTTextAnalyzer:
    """
    NLP analysis for OSINT events and market descriptions.

    Paper: "NLP enables machines to understand, interpret, and respond
    to human language, making it an invaluable tool for identifying
    fraudulent activity within communications" (Section 2.1)

    For Sentinel: NLP bridges OSINT text to market relevance scoring.
    """

    def __init__(self, embedding_model=None):
        """
        embedding_model: callable that takes text -> vector
        If None, falls back to keyword matching.
        Use Mistral Embed or sentence-transformers for production.
        """
        self.embedding_model = embedding_model
        self._stop_words = set([
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'shall',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'as', 'into', 'through', 'during', 'before', 'after', 'that',
            'this', 'these', 'those', 'it', 'its', 'and', 'but', 'or',
            'not', 'no', 'if', 'then', 'than', 'so', 'very', 'just',
        ])

    def extract_keywords(self, text: str, top_n: int = 10) -> list[str]:
        """Extract significant keywords from text."""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        filtered = [w for w in words if w not in self._stop_words]
        counts = Counter(filtered)
        return [word for word, _ in counts.most_common(top_n)]

    def compute_relevance_score(self, osint_text: str,
                                 market_description: str,
                                 market_keywords: list[str]) -> dict:
        """
        Score how relevant an OSINT event is to a specific market.

        Returns:
          - keyword_overlap: fraction of market keywords found in OSINT
          - semantic_similarity: cosine similarity of embeddings (if available)
          - composite_relevance: weighted combination
          - matched_keywords: which keywords matched
        """
        osint_keywords = set(self.extract_keywords(osint_text, top_n=30))
        market_kw_set = set(k.lower() for k in market_keywords)

        # Keyword overlap
        matched = osint_keywords & market_kw_set
        keyword_overlap = len(matched) / max(len(market_kw_set), 1)

        result = {
            'keyword_overlap': keyword_overlap,
            'matched_keywords': list(matched),
            'semantic_similarity': None,
            'composite_relevance': keyword_overlap,
        }

        # Semantic similarity via embeddings
        if self.embedding_model:
            try:
                osint_vec = self.embedding_model(osint_text)
                market_vec = self.embedding_model(market_description)
                similarity = self._cosine_similarity(osint_vec, market_vec)
                result['semantic_similarity'] = similarity
                # Weighted composite
                result['composite_relevance'] = (
                    0.4 * keyword_overlap + 0.6 * similarity
                )
            except Exception:
                pass

        return result

    def classify_information_type(self, text: str) -> dict:
        """
        Classify what type of information an OSINT event contains.
        Used to determine if the information could explain a trade.

        Categories:
          - BREAKING_NEWS: first report of an event
          - ANALYSIS: expert opinion or analysis
          - RUMOR: unconfirmed report
          - OFFICIAL: government/corporate announcement
          - DATA_RELEASE: economic data, earnings, etc.
        """
        text_lower = text.lower()

        indicators = {
            'BREAKING_NEWS': [
                'breaking', 'just in', 'happening now', 'confirmed',
                'sources say', 'reuters reports', 'ap reports',
                'exclusive', 'developing'
            ],
            'OFFICIAL': [
                'announces', 'announced', 'statement', 'press release',
                'official', 'government', 'white house', 'ministry',
                'department of', 'federal', 'regulation'
            ],
            'DATA_RELEASE': [
                'data shows', 'report shows', 'statistics',
                'quarterly', 'earnings', 'gdp', 'inflation',
                'unemployment', 'survey', 'index'
            ],
            'RUMOR': [
                'reportedly', 'alleged', 'unconfirmed', 'rumor',
                'sources claim', 'may', 'might', 'could',
                'speculation', 'expected to'
            ],
            'ANALYSIS': [
                'analysis', 'opinion', 'editorial', 'commentary',
                'experts say', 'analysts', 'forecast', 'predict',
                'outlook', 'assessment'
            ],
        }

        scores = {}
        for category, keywords in indicators.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[category] = score

        best_category = max(scores, key=scores.get) if any(
            scores.values()
        ) else 'UNKNOWN'

        return {
            'category': best_category,
            'confidence': scores.get(best_category, 0) / max(
                sum(scores.values()), 1
            ),
            'all_scores': scores,
        }

    def compute_information_asymmetry_indicators(
        self, osint_text: str, trade_timestamp, osint_timestamp
    ) -> dict:
        """
        Analyze whether the OSINT text could have been known
        BEFORE the trade occurred.

        Key question: "Was this person trading on private information
        or on public information the market was too slow to price?"
        (from Sentinel PRD Section 3)
        """
        info_type = self.classify_information_type(osint_text)

        gap_hours = (
            trade_timestamp - osint_timestamp
        ).total_seconds() / 3600

        result = {
            'info_type': info_type['category'],
            'temporal_gap_hours': gap_hours,
            'trade_before_info': gap_hours < 0,  # Trade happened first
            'info_was_public': gap_hours > 0,     # Info was available
        }

        # Information asymmetry classification
        if gap_hours < -24:
            result['asymmetry_class'] = 'STRONG_INSIDER_SIGNAL'
            result['asymmetry_score'] = 95
        elif gap_hours < -6:
            result['asymmetry_class'] = 'MODERATE_INSIDER_SIGNAL'
            result['asymmetry_score'] = 75
        elif gap_hours < -1:
            result['asymmetry_class'] = 'WEAK_INSIDER_SIGNAL'
            result['asymmetry_score'] = 55
        elif gap_hours < 0:
            result['asymmetry_class'] = 'POSSIBLE_FAST_REACTOR'
            result['asymmetry_score'] = 35
        elif gap_hours < 1:
            result['asymmetry_class'] = 'FAST_REACTOR'
            result['asymmetry_score'] = 15
        else:
            result['asymmetry_class'] = 'POST_INFO_TRADE'
            result['asymmetry_score'] = 5

        # Adjust for information type
        if info_type['category'] == 'RUMOR' and gap_hours > -6:
            result['asymmetry_score'] = max(
                0, result['asymmetry_score'] - 20
            )
            result['note'] = ('OSINT was a rumor, potentially available '
                            'to sophisticated analysts')

        return result

    @staticmethod
    def _cosine_similarity(a, b) -> float:
        import numpy as np
        a, b = np.array(a), np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
```

### 3.3 Integration with Sentinel's OSINT Pipeline

```python
# In src/osint/correlator.py, enhance EvidenceCorrelator:

class EnhancedEvidenceCorrelator:
    def __init__(self, text_analyzer: OSINTTextAnalyzer, ...):
        self.text_analyzer = text_analyzer

    def correlate(self, anomaly, osint_events):
        """Enhanced correlation with NLP analysis."""
        correlations = []

        market_desc = anomaly.get('market_description', '')
        market_keywords = self.text_analyzer.extract_keywords(
            market_desc, top_n=15
        )

        for event in osint_events:
            # Relevance scoring
            relevance = self.text_analyzer.compute_relevance_score(
                event['text'], market_desc, market_keywords
            )

            if relevance['composite_relevance'] < 0.2:
                continue  # Not relevant

            # Information asymmetry analysis
            asymmetry = (
                self.text_analyzer
                .compute_information_asymmetry_indicators(
                    event['text'],
                    anomaly['timestamp'],
                    event['timestamp']
                )
            )

            correlations.append({
                'osint_event': event,
                'relevance': relevance,
                'asymmetry': asymmetry,
                'combined_score': (
                    relevance['composite_relevance'] * 0.4 +
                    asymmetry['asymmetry_score'] / 100 * 0.6
                )
            })

        return sorted(correlations, key=lambda x: -x['combined_score'])
```

---

## 4. Deep Learning Anomaly Autoencoder

### 4.1 Concept

The paper recommends deep learning for detecting "complex patterns and subtle anomalies that traditional methods might overlook" (Section 7.1). An autoencoder learns the distribution of normal trading behavior, then flags trades that it cannot reconstruct well (high reconstruction error = anomaly).

### 4.2 Implementation

```python
import numpy as np

class TradingAutoencoder:
    """
    Autoencoder for unsupervised anomaly detection on trade features.
    Learns to reconstruct "normal" trades; high reconstruction error
    indicates anomalous behavior.

    Paper: "Deep learning techniques, particularly for anomaly detection,
    are becoming increasingly sophisticated" (Section 7.1)

    Uses numpy only (no PyTorch dependency for hackathon).
    For production, replace with PyTorch implementation.
    """

    def __init__(self, input_dim: int, encoding_dim: int = 8,
                 learning_rate: float = 0.001):
        self.input_dim = input_dim
        self.encoding_dim = encoding_dim
        self.lr = learning_rate

        # Simple 3-layer autoencoder: input -> hidden -> bottleneck -> hidden -> output
        hidden_dim = (input_dim + encoding_dim) // 2

        # Xavier initialization
        self.W1 = np.random.randn(input_dim, hidden_dim) * np.sqrt(
            2.0 / input_dim
        )
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, encoding_dim) * np.sqrt(
            2.0 / hidden_dim
        )
        self.b2 = np.zeros(encoding_dim)
        self.W3 = np.random.randn(encoding_dim, hidden_dim) * np.sqrt(
            2.0 / encoding_dim
        )
        self.b3 = np.zeros(hidden_dim)
        self.W4 = np.random.randn(hidden_dim, input_dim) * np.sqrt(
            2.0 / hidden_dim
        )
        self.b4 = np.zeros(input_dim)

        self.threshold = None  # Set after training

    def _relu(self, x):
        return np.maximum(0, x)

    def _relu_deriv(self, x):
        return (x > 0).astype(float)

    def _sigmoid(self, x):
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

    def encode(self, X):
        h1 = self._relu(X @ self.W1 + self.b1)
        encoding = self._relu(h1 @ self.W2 + self.b2)
        return encoding

    def decode(self, encoding):
        h3 = self._relu(encoding @ self.W3 + self.b3)
        reconstruction = self._sigmoid(h3 @ self.W4 + self.b4)
        return reconstruction

    def forward(self, X):
        h1 = self._relu(X @ self.W1 + self.b1)
        encoding = self._relu(h1 @ self.W2 + self.b2)
        h3 = self._relu(encoding @ self.W3 + self.b3)
        reconstruction = self._sigmoid(h3 @ self.W4 + self.b4)
        return reconstruction, h1, encoding, h3

    def train(self, X_normal: np.ndarray, epochs: int = 100,
              batch_size: int = 32, percentile_threshold: float = 95):
        """
        Train on NORMAL trades only. The autoencoder learns the
        distribution of legitimate trading behavior.

        After training, set anomaly threshold at the given percentile
        of reconstruction errors on the training set.
        """
        n = X_normal.shape[0]

        for epoch in range(epochs):
            # Shuffle
            indices = np.random.permutation(n)
            epoch_loss = 0

            for i in range(0, n, batch_size):
                batch = X_normal[indices[i:i+batch_size]]
                reconstruction, h1, encoding, h3 = self.forward(batch)

                # MSE loss
                error = reconstruction - batch
                loss = np.mean(error ** 2)
                epoch_loss += loss

                # Backpropagation (simplified)
                d_output = 2 * error / batch.shape[0]
                d_output *= reconstruction * (1 - reconstruction)  # sigmoid deriv

                d_W4 = h3.T @ d_output
                d_b4 = np.sum(d_output, axis=0)
                d_h3 = d_output @ self.W4.T * self._relu_deriv(h3)

                d_W3 = encoding.T @ d_h3
                d_b3 = np.sum(d_h3, axis=0)
                d_encoding = d_h3 @ self.W3.T * self._relu_deriv(encoding)

                d_W2 = h1.T @ d_encoding
                d_b2 = np.sum(d_encoding, axis=0)
                d_h1 = d_encoding @ self.W2.T * self._relu_deriv(h1)

                d_W1 = batch.T @ d_h1
                d_b1 = np.sum(d_h1, axis=0)

                # Update weights
                self.W4 -= self.lr * d_W4
                self.b4 -= self.lr * d_b4
                self.W3 -= self.lr * d_W3
                self.b3 -= self.lr * d_b3
                self.W2 -= self.lr * d_W2
                self.b2 -= self.lr * d_b2
                self.W1 -= self.lr * d_W1
                self.b1 -= self.lr * d_b1

        # Set threshold
        reconstructions, _, _, _ = self.forward(X_normal)
        errors = np.mean((X_normal - reconstructions) ** 2, axis=1)
        self.threshold = np.percentile(errors, percentile_threshold)

        return {
            'final_loss': epoch_loss / (n / batch_size),
            'threshold': self.threshold,
            'mean_error': np.mean(errors),
            'std_error': np.std(errors),
        }

    def score_anomaly(self, X: np.ndarray) -> dict:
        """
        Score new trades. Returns reconstruction error and anomaly flag.
        """
        reconstruction, _, encoding, _ = self.forward(X)
        errors = np.mean((X - reconstruction) ** 2, axis=1)

        return {
            'reconstruction_errors': errors,
            'is_anomalous': errors > self.threshold if self.threshold else np.zeros(len(errors), dtype=bool),
            'anomaly_scores': errors / max(self.threshold, 1e-10),
            'encodings': encoding,  # Useful for clustering in latent space
        }
```

### 4.3 Using the Autoencoder in Sentinel

```python
# Training: use trades that Arena confirmed as LEGITIMATE
normal_trades = load_arena_confirmed_legitimate_trades()
feature_matrix = extract_features(normal_trades)
normalized = normalize_features(feature_matrix)

autoencoder = TradingAutoencoder(input_dim=normalized.shape[1])
train_stats = autoencoder.train(normalized, epochs=200)

# Inference: score new trades
new_trade_features = extract_features([new_trade])
result = autoencoder.score_anomaly(normalize_features(new_trade_features))

if result['is_anomalous'][0]:
    # High reconstruction error = doesn't look like normal trading
    # Feed into classification pipeline with elevated priority
    pass
```

---

## 5. Continuous Learning & Feedback Loop

### 5.1 Concept

The paper emphasizes: "Continuous learning mechanisms allow organizations to stay ahead of emerging threats" (Section 7.2). For Sentinel, the Arena provides the feedback signal.

### 5.2 Arena-Driven Model Retraining

```python
from datetime import datetime, timedelta

class ContinuousLearningManager:
    """
    Manages the feedback loop from Arena votes to model improvement.

    Paper: "implementing feedback loops within fraud detection systems
    can enhance their adaptability" (Section 5.2)

    Flow:
    1. Anomaly detected -> classified by AI pipeline
    2. Case appears in Arena -> humans vote
    3. When consensus reached -> label added to training set
    4. Periodically retrain models with new labels
    """

    def __init__(self, db, rf_classifier, autoencoder,
                 retrain_interval_hours: int = 24,
                 min_new_labels: int = 10):
        self.db = db
        self.rf_classifier = rf_classifier
        self.autoencoder = autoencoder
        self.retrain_interval = timedelta(hours=retrain_interval_hours)
        self.min_new_labels = min_new_labels
        self.last_retrain = None

    def check_and_retrain(self):
        """
        Check if retraining is needed based on:
        1. Enough new Arena labels since last retrain
        2. Sufficient time has passed
        3. Model drift detected
        """
        if (self.last_retrain and
            datetime.utcnow() - self.last_retrain < self.retrain_interval):
            return False

        new_labels = self._get_new_arena_labels()
        if len(new_labels) < self.min_new_labels:
            return False

        # Check for drift: are recent predictions less accurate?
        drift_detected = self._detect_drift(new_labels)

        if drift_detected or len(new_labels) >= self.min_new_labels * 3:
            self._retrain_models(new_labels)
            self.last_retrain = datetime.utcnow()
            return True

        return False

    def _get_new_arena_labels(self) -> list[dict]:
        """Get Arena cases with consensus since last retrain."""
        since = self.last_retrain or datetime(2020, 1, 1)
        # Query Arena votes with >= 3 votes and > 66% agreement
        return self.db.query("""
            SELECT ae.*, av.consensus_label, av.agreement_pct
            FROM anomaly_events ae
            JOIN (
                SELECT anomaly_id,
                       MODE() WITHIN GROUP (ORDER BY vote) as consensus_label,
                       COUNT(*) as vote_count,
                       MAX(vote_count_per_label) * 100.0 / COUNT(*) as agreement_pct
                FROM arena_votes
                GROUP BY anomaly_id
                HAVING COUNT(*) >= 3 AND agreement_pct > 66
            ) av ON ae.id = av.anomaly_id
            WHERE av.created_at > ?
        """, [since])

    def _detect_drift(self, new_labels: list[dict]) -> bool:
        """
        Compare model predictions against Arena consensus.
        If accuracy drops below threshold, trigger retrain.
        """
        correct = 0
        total = 0
        for label in new_labels:
            model_pred = label.get('ai_classification')
            human_label = label.get('consensus_label')
            if model_pred and human_label:
                total += 1
                if model_pred == human_label:
                    correct += 1

        if total < 5:
            return False

        accuracy = correct / total
        return accuracy < 0.7  # Below 70% agreement = drift

    def _retrain_models(self, new_labels: list[dict]):
        """Retrain RF classifier and autoencoder with new labels."""
        # Get full training set (old + new labels)
        all_labeled = self.db.get_all_labeled_cases()

        # Retrain RF
        X, y = self._prepare_rf_data(all_labeled)
        self.rf_classifier.train(X, y, feature_names=self._feature_names())

        # Retrain autoencoder on legitimate cases only
        legitimate = [c for c in all_labeled
                     if c['label'] in ('FAST_REACTOR', 'SPECULATOR')]
        X_normal = self._prepare_autoencoder_data(legitimate)
        self.autoencoder.train(X_normal, epochs=100)

    def process_arena_vote(self, anomaly_id: str, vote: str,
                           voter_id: str):
        """Record a vote and check if consensus triggers retraining."""
        self.db.insert_arena_vote(anomaly_id, vote, voter_id)

        # Check if this vote creates consensus
        votes = self.db.get_votes_for_anomaly(anomaly_id)
        if len(votes) >= 3:
            consensus = self._check_consensus(votes)
            if consensus:
                self.db.update_anomaly_label(
                    anomaly_id, consensus['label']
                )
```

---

## 6. False Positive Management

### 6.1 The Problem

The paper dedicates Section 5.1 to false positives: "False positives can erode trust in the organization's ability to protect financial interests." The Elicit report flags a 39% false alarm rate in one system. This is the primary operational risk.

### 6.2 Multi-Gate Architecture

Implement cascading gates that reduce false positives at each stage:

```python
class FalsePositiveGate:
    """
    Multi-stage gating to reduce false positive rate.

    Gate 1: Statistical threshold (fast, broad)
    Gate 2: RF classifier (medium speed, higher precision)
    Gate 3: Autoencoder (unsupervised, catches novel patterns)
    Gate 4: Game theory behavioral analysis
    Gate 5: Mistral AI classification (slow, most accurate)

    Each gate can DISMISS (definitely not suspicious)
    or ESCALATE (needs further analysis).

    Paper: "To mitigate the implications of false positives,
    organizations must invest in advanced fraud detection technologies
    that balance accuracy and sensitivity" (Section 5.1)
    """

    def __init__(self, streaming_detector, rf_classifier,
                 autoencoder, game_theory, mistral_pipeline):
        self.gates = [
            ('statistical', streaming_detector, 0.3),   # Very low bar
            ('rf_classifier', rf_classifier, 0.4),
            ('autoencoder', autoencoder, 0.5),
            ('game_theory', game_theory, 0.5),
            ('mistral', mistral_pipeline, 0.6),
        ]

    def evaluate(self, trade: dict, features: dict) -> dict:
        """
        Run trade through cascading gates.
        Returns at the first gate that makes a definitive decision.
        """
        results = []
        cumulative_score = 0

        for gate_name, gate, weight in self.gates:
            gate_result = gate.evaluate(trade, features)
            results.append({
                'gate': gate_name,
                'score': gate_result['score'],
                'decision': gate_result['decision'],
            })

            cumulative_score += gate_result['score'] * weight

            # Early exit: definitely not suspicious
            if gate_result['decision'] == 'DISMISS':
                return {
                    'final_decision': 'LEGITIMATE',
                    'dismissed_at_gate': gate_name,
                    'gates_passed': results,
                    'cumulative_score': cumulative_score,
                }

            # Early exit: definitely suspicious (very high confidence)
            if (gate_result['decision'] == 'ESCALATE'
                and gate_result.get('confidence', 0) > 0.95):
                return {
                    'final_decision': 'SUSPICIOUS',
                    'escalated_at_gate': gate_name,
                    'gates_passed': results,
                    'cumulative_score': cumulative_score,
                }

        # Passed all gates: use cumulative score
        total_weight = sum(w for _, _, w in self.gates)
        normalized_score = cumulative_score / total_weight

        return {
            'final_decision': (
                'SUSPICIOUS' if normalized_score > 0.5 else 'LEGITIMATE'
            ),
            'gates_passed': results,
            'cumulative_score': normalized_score,
        }
```

### 6.3 False Positive Rate Tracking

```python
class FPRTracker:
    """Track false positive rate over time using Arena feedback."""

    def __init__(self):
        self.predictions = []  # (predicted, actual_from_arena)

    def record(self, predicted: str, actual: str):
        self.predictions.append((predicted, actual))

    def compute_fpr(self) -> dict:
        """
        FPR = FP / (FP + TN)
        Where FP = flagged as suspicious but Arena says legitimate
        """
        if not self.predictions:
            return {'fpr': None, 'sample_size': 0}

        fp = sum(1 for p, a in self.predictions
                if p == 'SUSPICIOUS' and a in ('FAST_REACTOR', 'SPECULATOR'))
        tn = sum(1 for p, a in self.predictions
                if p == 'LEGITIMATE' and a in ('FAST_REACTOR', 'SPECULATOR'))

        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

        return {
            'fpr': fpr,
            'false_positives': fp,
            'true_negatives': tn,
            'sample_size': len(self.predictions),
            'target': '< 10%',
            'status': 'OK' if fpr < 0.10 else 'HIGH - retrain needed',
        }
```

---

## 7. Integration Map

### 7.1 New Files

```
src/
  detection/
    streaming_detector.py    # StreamingAnomalyDetector
    autoencoder.py           # TradingAutoencoder
    fp_gate.py               # FalsePositiveGate, FPRTracker
  osint/
    text_analyzer.py         # OSINTTextAnalyzer
  data/
    fusion_engine.py         # DataFusionEngine, FusedDataPoint
  classification/
    continuous_learning.py   # ContinuousLearningManager
```

### 7.2 Enhanced Pipeline Flow

```
[Real-Time Trades]
       |
       v
StreamingAnomalyDetector    <-- Gate 1: Statistical
       |
       v (if anomalous)
DataFusionEngine            <-- Combine with OSINT timeline
       |
       v
FeatureExtractor            <-- Extended feature vector (Guide 1)
       |
       v
RFClassifier                <-- Gate 2: Random Forest (Guide 1)
       |
       v
TradingAutoencoder          <-- Gate 3: Reconstruction error
       |
       v
GameTheoryAnalysis          <-- Gate 4: Behavioral analysis (Guide 2)
       |
       v
OSINTTextAnalyzer           <-- NLP relevance + asymmetry scoring
       |
       v
SentinelPipeline            <-- Gate 5: Mistral Stage 1/2/3
       |
       v
[Sentinel Index + Arena]    <-- Feedback loop
       |
       v
ContinuousLearningManager   <-- Periodic retraining
```

### 7.3 Dashboard Additions

- **FPR Gauge**: Real-time false positive rate from Arena feedback
- **Gate Funnel**: Visualization showing how many trades pass each gate
- **Model Drift Chart**: Accuracy over time, triggering retrain alerts
- **NLP Relevance Heatmap**: OSINT-to-market matching visualization

---

## 8. Key Takeaways for Implementation

1. **Data fusion is the foundation** -- unify all sources into a single timeline per market before analysis.
2. **Streaming detection must be O(1) per trade** -- use rolling statistics, not batch recomputation.
3. **NLP bridges OSINT text to market context** -- this is how Sentinel answers "was public information available?"
4. **The autoencoder catches what RF misses** -- unsupervised anomaly detection finds novel insider patterns not in the training data.
5. **Cascading gates are essential for managing FPR** -- dismiss obvious non-issues early, reserve expensive AI analysis for genuine signals.
6. **Arena feedback is the most valuable data** -- every human vote improves every model. Prioritize Arena UX.
7. **Continuous learning prevents drift** -- insider strategies evolve; the models must evolve too.
