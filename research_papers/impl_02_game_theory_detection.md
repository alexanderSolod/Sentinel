# Implementation Guide 2: Game Theory-Informed Adversarial Detection

> **Source:** Elicit AI Report (2025), "Game Theory in Insider Trading Detection" (synthesis of Lakshmi et al. 2025, Seth et al. 2020, Jakimowicz & Baklarz 2016, Sadiq et al. 2025, Al-khawaja et al. 2025)
> **Target System:** Sentinel -- Prediction Market Integrity Monitor
> **Goal:** Implement game-theoretic behavioral modeling, entropy-based anomaly scoring, and swarm intelligence pattern mining to detect strategic insider behavior that evades simple statistical thresholds.

---

## 1. Core Concepts from the Literature

The Elicit report synthesizes five systems. Three contain implementable techniques for Sentinel:

| System | Key Technique | Accuracy | Sentinel Application |
|---|---|---|---|
| **InvestoGuard** (Lakshmi et al.) | Game theory risk engine + behavioral entropy + sensor fusion | 95%, F1=0.89 | Behavioral Suspicion Score (BSS) calculation |
| **ACO Framework** (Sadiq et al.) | Ant Colony Optimization for pattern mining | 99.7% detection, 39% FPR | Coordinated trading pattern discovery |
| **GNN System** (Al-khawaja et al.) | Graph Neural Networks + RL for regulatory adaptation | Precision=0.91, AUC=0.94 | Wallet network analysis |

### Key Limitation to Address
The report flags that most studies use **synthetic data** and **unspecified baselines**. Sentinel has an advantage: real Polymarket trade data + Arena human labels. The implementation below uses game theory as a **modeling framework** for the classification pipeline, not as a standalone detector.

---

## 2. Game-Theoretic Player Model

### 2.1 The Prediction Market as a Game (from PRD Section 3)

Sentinel already defines player types. The game theory layer formalizes this with payoff matrices and equilibrium analysis.

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class PlayerType(Enum):
    INSIDER = "insider"
    OSINT_EDGE = "osint_edge"
    FAST_REACTOR = "fast_reactor"
    SPECULATOR = "speculator"
    NOISE_TRADER = "noise_trader"
    MARKET_MAKER = "market_maker"

@dataclass
class PlayerProfile:
    """
    Game-theoretic profile of a trader.
    Models the rational strategy each player type would follow.
    """
    player_type: PlayerType

    # Information state
    has_private_info: bool
    has_public_info_edge: bool
    info_arrival_time: Optional[float]  # Hours before news (None if no info)

    # Strategy parameters
    expected_payoff: float          # Expected profit from the trade
    detection_risk: float           # Probability of being caught (0-1)
    cost_of_detection: float        # Penalty if caught
    urgency: float                  # Time pressure to trade (0-1)

    # Behavioral predictions
    optimal_position_size: float    # Nash equilibrium position
    optimal_timing: float           # When a rational player would trade
    obfuscation_level: float        # How much they'd hide their tracks

    @property
    def risk_adjusted_payoff(self) -> float:
        """Expected value considering detection risk."""
        return (self.expected_payoff * (1 - self.detection_risk)
                - self.cost_of_detection * self.detection_risk)
```

### 2.2 Payoff Matrix Construction

Model the interaction between traders and the surveillance system:

```python
import numpy as np

def build_payoff_matrix(market_size_usd: float,
                        price_move_pct: float,
                        detection_probability: float) -> dict:
    """
    2-player game: Insider vs. Surveillance System

    Insider strategies: {Trade Aggressively, Trade Cautiously, Don't Trade}
    Surveillance strategies: {Monitor Closely, Standard Monitoring, No Monitoring}

    Returns payoff matrix for both players.

    Reference: InvestoGuard's game theory risk engine (Lakshmi et al. 2025)
    """
    profit_aggressive = market_size_usd * price_move_pct * 0.8
    profit_cautious = market_size_usd * price_move_pct * 0.3
    penalty = market_size_usd * 2.0  # Regulatory penalty multiplier

    # Insider payoffs: [aggressive, cautious, abstain]
    # Surveillance payoffs: [close, standard, none]

    insider_payoffs = np.array([
        # vs Close Monitor    vs Standard       vs No Monitor
        [profit_aggressive - penalty * 0.9,
         profit_aggressive - penalty * 0.4,
         profit_aggressive],                      # Aggressive
        [profit_cautious - penalty * 0.3,
         profit_cautious - penalty * 0.1,
         profit_cautious],                         # Cautious
        [0, 0, 0],                                 # Abstain
    ])

    surveillance_payoffs = np.array([
        # vs Aggressive    vs Cautious       vs Abstain
        [penalty * 0.9 - 100,
         penalty * 0.3 - 100,
         -100],                                    # Close monitor (costly)
        [penalty * 0.4 - 20,
         penalty * 0.1 - 20,
         -20],                                     # Standard (cheaper)
        [0, 0, 0],                                 # No monitoring
    ])

    return {
        'insider_payoffs': insider_payoffs,
        'surveillance_payoffs': surveillance_payoffs,
        'strategies': {
            'insider': ['aggressive', 'cautious', 'abstain'],
            'surveillance': ['close', 'standard', 'none']
        }
    }


def find_nash_equilibrium(insider_payoffs: np.ndarray,
                          surveillance_payoffs: np.ndarray) -> dict:
    """
    Find mixed-strategy Nash equilibrium.
    Used to predict: given market conditions, what would a rational
    insider do? Then compare actual behavior to equilibrium prediction.

    Deviation from Nash equilibrium = behavioral anomaly signal.
    """
    from scipy.optimize import linprog

    n_insider = insider_payoffs.shape[0]
    n_surv = insider_payoffs.shape[1]

    # Solve for surveillance mixed strategy (insider best-responds)
    # Using linear programming formulation of zero-sum approximation
    c = np.zeros(n_surv + 1)
    c[-1] = -1  # Maximize the value

    A_ub = np.hstack([-insider_payoffs, np.ones((n_insider, 1))])
    b_ub = np.zeros(n_insider)

    A_eq = np.ones((1, n_surv + 1))
    A_eq[0, -1] = 0
    b_eq = np.array([1.0])

    bounds = [(0, 1)] * n_surv + [(None, None)]

    try:
        result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                        bounds=bounds, method='highs')
        if result.success:
            return {
                'surveillance_mixed_strategy': result.x[:n_surv],
                'game_value': -result.fun,
                'converged': True
            }
    except Exception:
        pass

    return {'converged': False}
```

### 2.3 Behavioral Deviation Score

The key insight: compare **observed behavior** to **Nash equilibrium prediction**. Large deviations indicate either irrationality or strategic obfuscation.

```python
def compute_behavioral_deviation(observed_trade: dict,
                                 equilibrium: dict,
                                 player_profiles: dict) -> float:
    """
    How far does observed behavior deviate from game-theoretic prediction?

    High deviation from INSIDER equilibrium = less likely insider
    High deviation from SPECULATOR equilibrium = less likely speculator
    Low deviation from INSIDER equilibrium = more suspicious

    Returns deviation score 0-100 (higher = more anomalous).
    """
    deviations = {}

    for player_type, profile in player_profiles.items():
        # Compare observed position size to equilibrium prediction
        size_dev = abs(observed_trade['position_size']
                       - profile.optimal_position_size)
        size_dev_normalized = size_dev / max(
            profile.optimal_position_size, 1
        )

        # Compare observed timing to equilibrium prediction
        timing_dev = abs(observed_trade['hours_before_news']
                         - profile.optimal_timing)
        timing_dev_normalized = timing_dev / max(
            abs(profile.optimal_timing), 1
        )

        # Compare observed obfuscation to prediction
        obfusc_dev = abs(observed_trade['obfuscation_score']
                         - profile.obfuscation_level)

        deviations[player_type] = (
            0.4 * size_dev_normalized +
            0.4 * timing_dev_normalized +
            0.2 * obfusc_dev
        )

    # Score = how well it fits INSIDER profile vs alternatives
    insider_fit = 1.0 - deviations.get(PlayerType.INSIDER, 1.0)
    best_legit_fit = 1.0 - min(
        deviations.get(PlayerType.SPECULATOR, 1.0),
        deviations.get(PlayerType.OSINT_EDGE, 1.0),
        deviations.get(PlayerType.FAST_REACTOR, 1.0),
    )

    # Final score: how much better does insider model fit than legitimate?
    deviation_score = max(0, min(100,
        (insider_fit - best_legit_fit + 0.5) * 100
    ))

    return deviation_score
```

---

## 3. Behavioral Entropy Analysis

### 3.1 Concept

From InvestoGuard (Lakshmi et al.): behavioral entropy measures the **unpredictability** of a trader's actions. Legitimate traders have consistent patterns (low entropy). Insiders may show anomalous entropy -- either suspiciously low (single focused bet) or pattern-breaking high.

### 3.2 Implementation

```python
from scipy.stats import entropy as scipy_entropy
from collections import Counter
import numpy as np

class BehavioralEntropyAnalyzer:
    """
    Compute Shannon entropy of trader behavior across multiple dimensions.
    Reference: InvestoGuard's behavioral entropy analysis (Lakshmi et al. 2025)
    """

    def compute_trading_entropy(self, trades: list[dict]) -> dict:
        """
        Analyze entropy across multiple behavioral dimensions.
        Returns entropy scores and anomaly flags.
        """
        if len(trades) < 5:
            return {
                'overall_entropy': None,
                'insufficient_data': True,
                'anomaly_flag': False
            }

        results = {}

        # 1. Temporal entropy: when does this wallet trade?
        hours = [t['timestamp'].hour for t in trades]
        hour_dist = self._to_probability_dist(hours, bins=24)
        results['temporal_entropy'] = scipy_entropy(hour_dist, base=2)
        results['temporal_max'] = np.log2(24)  # Max possible

        # 2. Market diversity entropy: how many different markets?
        markets = [t['market_id'] for t in trades]
        market_dist = self._to_probability_dist_categorical(markets)
        results['market_entropy'] = scipy_entropy(market_dist, base=2)

        # 3. Position size entropy: are sizes consistent or erratic?
        sizes = [t['position_size_usd'] for t in trades]
        size_bins = np.histogram(sizes, bins=10)[0]
        size_dist = size_bins / size_bins.sum() if size_bins.sum() > 0 else size_bins
        results['size_entropy'] = scipy_entropy(size_dist + 1e-10, base=2)

        # 4. Direction entropy: buy/sell balance
        directions = [t.get('direction', 'buy') for t in trades]
        dir_dist = self._to_probability_dist_categorical(directions)
        results['direction_entropy'] = scipy_entropy(dir_dist, base=2)

        # 5. Inter-trade interval entropy
        if len(trades) >= 3:
            timestamps = sorted([t['timestamp'] for t in trades])
            intervals = [(timestamps[i+1] - timestamps[i]).total_seconds()
                        for i in range(len(timestamps) - 1)]
            interval_bins = np.histogram(intervals, bins=10)[0]
            interval_dist = interval_bins / interval_bins.sum() if interval_bins.sum() > 0 else interval_bins
            results['interval_entropy'] = scipy_entropy(
                interval_dist + 1e-10, base=2
            )

        # Composite entropy score
        entropy_values = [v for k, v in results.items()
                         if k.endswith('_entropy') and v is not None]
        results['composite_entropy'] = np.mean(entropy_values)

        # Anomaly detection: flag if entropy is in extreme tails
        results['anomaly_flag'] = self._is_entropy_anomalous(results)

        return results

    def _to_probability_dist(self, values: list, bins: int) -> np.ndarray:
        counts, _ = np.histogram(values, bins=bins,
                                  range=(0, bins))
        total = counts.sum()
        if total == 0:
            return np.ones(bins) / bins
        return counts / total

    def _to_probability_dist_categorical(self, values: list) -> np.ndarray:
        counts = Counter(values)
        total = sum(counts.values())
        if total == 0:
            return np.array([1.0])
        return np.array([c / total for c in counts.values()])

    def _is_entropy_anomalous(self, results: dict) -> bool:
        """
        Flag wallets with suspiciously LOW entropy (focused insider behavior)
        or pattern-breaking HIGH entropy (obfuscation attempt).

        Thresholds should be calibrated on Sentinel's data.
        """
        composite = results.get('composite_entropy', 0)

        # Suspiciously focused (single market, single direction, single time)
        if composite < 0.5:
            return True

        # Market diversity near zero (only trades one market)
        if results.get('market_entropy', 999) < 0.1:
            return True

        return False
```

### 3.3 Entropy-Based Feature for RF Classifier

Add entropy scores to the feature vector from Implementation Guide 1:

```python
# Additional features for ExtendedFeatureVector
composite_entropy: float        # Overall behavioral entropy
temporal_entropy: float         # Trading time pattern entropy
market_diversity_entropy: float # How many markets they trade
size_consistency_entropy: float # Position size regularity
entropy_anomaly_flag: bool      # Extreme entropy detected
```

---

## 4. Swarm Intelligence Pattern Mining (ACO)

### 4.1 Concept

From Sadiq et al.: Ant Colony Optimization discovers **frequent suspicious patterns** in trade sequences. Unlike DBSCAN (which clusters by spatial proximity), ACO finds temporal/behavioral patterns that recur across different insider trading events.

### 4.2 Implementation: Pattern Discovery

```python
import numpy as np
from collections import defaultdict

class ACOPatternMiner:
    """
    Ant Colony Optimization for discovering recurring suspicious
    trade patterns. Ants traverse trade sequences, depositing
    pheromone on pattern edges that lead to confirmed suspicious cases.

    Reference: Sadiq et al. 2025 - 99.7% detection accuracy,
    98.6% pattern discovery rate.

    NOTE: The paper reports 39% false alarm rate. We mitigate this
    by using ACO as a pattern DISCOVERY tool (not final classifier),
    feeding discovered patterns into the RF + Mistral pipeline.
    """

    def __init__(self, n_ants: int = 50, n_iterations: int = 100,
                 evaporation_rate: float = 0.3,
                 alpha: float = 1.0,  # Pheromone weight
                 beta: float = 2.0):  # Heuristic weight
        self.n_ants = n_ants
        self.n_iterations = n_iterations
        self.evaporation_rate = evaporation_rate
        self.alpha = alpha
        self.beta = beta
        self.pheromone = defaultdict(lambda: 1.0)
        self.discovered_patterns = []

    def encode_trade_sequence(self, trades: list[dict]) -> list[str]:
        """
        Encode a sequence of trades into discrete behavioral tokens.
        Each token represents a behavioral "state".
        """
        tokens = []
        for trade in sorted(trades, key=lambda t: t['timestamp']):
            # Discretize key features into categorical tokens
            size_cat = self._categorize_size(trade['position_size_usd'])
            timing_cat = self._categorize_timing(
                trade.get('hours_before_news', None)
            )
            wallet_cat = 'FRESH' if trade.get('is_fresh_wallet') else 'ESTAB'
            direction = trade.get('direction', 'BUY').upper()

            token = f"{wallet_cat}_{direction}_{size_cat}_{timing_cat}"
            tokens.append(token)
        return tokens

    def _categorize_size(self, size_usd: float) -> str:
        if size_usd > 50000: return 'WHALE'
        if size_usd > 10000: return 'LARGE'
        if size_usd > 1000: return 'MEDIUM'
        return 'SMALL'

    def _categorize_timing(self, hours: float) -> str:
        if hours is None: return 'UNKNOWN'
        if hours > 24: return 'FAR_BEFORE'
        if hours > 6: return 'BEFORE'
        if hours > 1: return 'JUST_BEFORE'
        if hours > 0: return 'MINUTES_BEFORE'
        return 'AFTER'

    def mine_patterns(self, trade_sequences: list[list[str]],
                      labels: list[bool]) -> list[dict]:
        """
        Run ACO to discover recurring token subsequences
        that correlate with suspicious (label=True) cases.

        Returns list of discovered patterns with support and confidence.
        """
        # Build transition graph from all sequences
        edges = set()
        for seq in trade_sequences:
            for i in range(len(seq) - 1):
                edges.add((seq[i], seq[i+1]))

        # Initialize pheromone
        for edge in edges:
            self.pheromone[edge] = 1.0

        # Heuristic: edges more common in suspicious cases get bonus
        suspicious_seqs = [s for s, l in zip(trade_sequences, labels) if l]
        legit_seqs = [s for s, l in zip(trade_sequences, labels) if not l]

        edge_suspicion = defaultdict(float)
        for seq in suspicious_seqs:
            for i in range(len(seq) - 1):
                edge_suspicion[(seq[i], seq[i+1])] += 1.0

        for seq in legit_seqs:
            for i in range(len(seq) - 1):
                edge_suspicion[(seq[i], seq[i+1])] -= 0.5

        # ACO iterations
        best_patterns = []
        for iteration in range(self.n_iterations):
            ant_paths = []

            for ant in range(self.n_ants):
                path = self._ant_walk(edges, edge_suspicion)
                score = self._evaluate_path(path, suspicious_seqs)
                ant_paths.append((path, score))

            # Update pheromone
            self._evaporate()
            for path, score in ant_paths:
                if score > 0:
                    self._deposit_pheromone(path, score)

            # Track best patterns
            ant_paths.sort(key=lambda x: -x[1])
            for path, score in ant_paths[:3]:
                if score > 0.5 and path not in [p['pattern'] for p in best_patterns]:
                    best_patterns.append({
                        'pattern': path,
                        'score': score,
                        'iteration': iteration
                    })

        # Calculate support and confidence for discovered patterns
        self.discovered_patterns = self._calculate_pattern_stats(
            best_patterns, trade_sequences, labels
        )
        return self.discovered_patterns

    def _ant_walk(self, edges, edge_suspicion, max_steps=5):
        """Single ant traverses the graph probabilistically."""
        all_nodes = set()
        for a, b in edges:
            all_nodes.add(a)
            all_nodes.add(b)

        if not all_nodes:
            return []

        current = np.random.choice(list(all_nodes))
        path = [current]

        for _ in range(max_steps):
            neighbors = [b for (a, b) in edges if a == current]
            if not neighbors:
                break

            # Probability proportional to pheromone^alpha * heuristic^beta
            probs = []
            for n in neighbors:
                pheromone = self.pheromone[(current, n)] ** self.alpha
                heuristic = max(0.1,
                    edge_suspicion.get((current, n), 0) + 1
                ) ** self.beta
                probs.append(pheromone * heuristic)

            total = sum(probs)
            if total == 0:
                break
            probs = [p / total for p in probs]

            current = np.random.choice(neighbors, p=probs)
            path.append(current)

        return tuple(path)

    def _evaluate_path(self, path, suspicious_seqs) -> float:
        """Score a path by how often it appears in suspicious sequences."""
        if len(path) < 2:
            return 0.0
        count = 0
        for seq in suspicious_seqs:
            seq_str = ' '.join(seq)
            path_str = ' '.join(path)
            if path_str in seq_str:
                count += 1
        return count / max(len(suspicious_seqs), 1)

    def _evaporate(self):
        for edge in self.pheromone:
            self.pheromone[edge] *= (1 - self.evaporation_rate)

    def _deposit_pheromone(self, path, score):
        for i in range(len(path) - 1):
            self.pheromone[(path[i], path[i+1])] += score

    def _calculate_pattern_stats(self, patterns, sequences, labels):
        """Calculate support and confidence for each pattern."""
        results = []
        n_suspicious = sum(labels)
        n_total = len(labels)

        for p in patterns:
            pattern_str = ' '.join(p['pattern'])
            matches_suspicious = 0
            matches_total = 0

            for seq, label in zip(sequences, labels):
                seq_str = ' '.join(seq)
                if pattern_str in seq_str:
                    matches_total += 1
                    if label:
                        matches_suspicious += 1

            support = matches_total / n_total if n_total > 0 else 0
            confidence = (matches_suspicious / matches_total
                         if matches_total > 0 else 0)

            results.append({
                'pattern': p['pattern'],
                'support': support,
                'confidence': confidence,
                'lift': (confidence / (n_suspicious / n_total)
                        if n_suspicious > 0 else 0),
            })

        return sorted(results, key=lambda x: -x['confidence'])

    def match_pattern(self, trade_sequence: list[str]) -> list[dict]:
        """
        Check if a new trade sequence matches any discovered patterns.
        Returns matching patterns with confidence scores.
        """
        seq_str = ' '.join(trade_sequence)
        matches = []
        for pattern in self.discovered_patterns:
            pattern_str = ' '.join(pattern['pattern'])
            if pattern_str in seq_str:
                matches.append(pattern)
        return matches
```

---

## 5. Graph Neural Network for Wallet Networks

### 5.1 Concept

From Al-khawaja et al.: model wallet interactions as a graph where nodes are wallets and edges are fund flows or correlated trading. GNN propagates information through the network to classify nodes.

### 5.2 Lightweight Implementation (No PyTorch Geometric Required)

For hackathon scope, implement the graph structure and feature propagation without a full GNN training loop:

```python
import networkx as nx
import numpy as np
from collections import defaultdict

class WalletGraphAnalyzer:
    """
    Graph-based wallet analysis.
    Reference: Al-khawaja et al. 2025 (Precision=0.91, AUC=0.94)

    For production: use PyTorch Geometric with GraphSAGE.
    For hackathon: use NetworkX with manual feature propagation.
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def build_graph(self, trades: list[dict],
                    funding_flows: list[dict]):
        """
        Construct wallet interaction graph.
        Nodes: wallet addresses
        Edges: fund transfers + correlated trading activity
        """
        # Add nodes with features
        wallet_features = defaultdict(lambda: {
            'trade_count': 0, 'total_volume': 0,
            'unique_markets': set(), 'risk_score': 0
        })

        for trade in trades:
            w = trade['wallet_address']
            wallet_features[w]['trade_count'] += 1
            wallet_features[w]['total_volume'] += trade.get(
                'position_size_usd', 0
            )
            wallet_features[w]['unique_markets'].add(
                trade.get('market_id', '')
            )

        for w, feats in wallet_features.items():
            self.graph.add_node(w,
                trade_count=feats['trade_count'],
                total_volume=feats['total_volume'],
                market_diversity=len(feats['unique_markets']),
            )

        # Add funding edges
        for flow in funding_flows:
            self.graph.add_edge(
                flow['from_address'],
                flow['to_address'],
                amount=flow.get('amount_usd', 0),
                edge_type='funding'
            )

        # Add correlated trading edges
        self._add_correlation_edges(trades)

    def _add_correlation_edges(self, trades: list[dict],
                                time_window_seconds: int = 300):
        """
        Connect wallets that trade the same market within a time window.
        Correlated entry = potential coordination.
        """
        from itertools import combinations

        # Group trades by market
        market_trades = defaultdict(list)
        for t in trades:
            market_trades[t.get('market_id', '')].append(t)

        for market_id, market_group in market_trades.items():
            market_group.sort(key=lambda x: x['timestamp'])

            for i, j in combinations(range(len(market_group)), 2):
                t1, t2 = market_group[i], market_group[j]
                time_diff = abs(
                    (t2['timestamp'] - t1['timestamp']).total_seconds()
                )

                if time_diff <= time_window_seconds:
                    w1 = t1['wallet_address']
                    w2 = t2['wallet_address']
                    if w1 != w2:
                        self.graph.add_edge(w1, w2,
                            time_diff=time_diff,
                            market=market_id,
                            edge_type='correlated_trade'
                        )

    def compute_network_features(self, wallet_address: str) -> dict:
        """
        Extract graph-based features for a specific wallet.
        These augment the RF feature vector.
        """
        if wallet_address not in self.graph:
            return self._default_features()

        features = {}

        # Centrality measures
        features['degree_centrality'] = nx.degree_centrality(
            self.graph
        ).get(wallet_address, 0)

        # Local clustering coefficient
        undirected = self.graph.to_undirected()
        features['clustering_coefficient'] = nx.clustering(
            undirected, wallet_address
        )

        # Connected component size
        components = list(nx.weakly_connected_components(self.graph))
        for comp in components:
            if wallet_address in comp:
                features['component_size'] = len(comp)
                break
        else:
            features['component_size'] = 1

        # Neighbor suspicion propagation (1-hop)
        neighbor_risk = []
        for neighbor in self.graph.neighbors(wallet_address):
            n_data = self.graph.nodes.get(neighbor, {})
            neighbor_risk.append(n_data.get('risk_score', 0))
        features['neighbor_avg_risk'] = (
            np.mean(neighbor_risk) if neighbor_risk else 0
        )
        features['neighbor_max_risk'] = (
            max(neighbor_risk) if neighbor_risk else 0
        )

        # Funding chain depth (from known exchanges)
        features['funding_depth'] = self._funding_chain_depth(
            wallet_address
        )

        # Correlated trading edges
        corr_edges = [
            (u, v, d) for u, v, d in self.graph.edges(
                wallet_address, data=True
            )
            if d.get('edge_type') == 'correlated_trade'
        ]
        features['correlated_wallets_count'] = len(corr_edges)

        return features

    def _funding_chain_depth(self, wallet: str, max_depth: int = 10) -> int:
        """BFS backward through funding edges to find depth from known source."""
        visited = set()
        queue = [(wallet, 0)]

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                return max_depth
            if current in visited:
                continue
            visited.add(current)

            # Check predecessors (who funded this wallet?)
            for pred in self.graph.predecessors(current):
                edge_data = self.graph.edges[pred, current]
                if edge_data.get('edge_type') == 'funding':
                    if self.graph.nodes[pred].get('is_known_exchange'):
                        return depth + 1
                    queue.append((pred, depth + 1))

        return max_depth  # Unknown origin

    def _default_features(self) -> dict:
        return {
            'degree_centrality': 0,
            'clustering_coefficient': 0,
            'component_size': 1,
            'neighbor_avg_risk': 0,
            'neighbor_max_risk': 0,
            'funding_depth': 10,
            'correlated_wallets_count': 0,
        }
```

---

## 6. Composite Game Theory Score

### 6.1 Bringing It All Together

Combine game-theoretic deviation, behavioral entropy, pattern matching, and network analysis into a single enriched signal:

```python
@dataclass
class GameTheoryAnalysis:
    """
    Combined game-theoretic analysis result.
    Fed into Stage 1 triage and Stage 2 deep analysis.
    """
    # Game theory
    behavioral_deviation_score: float    # 0-100, from Nash analysis
    player_type_fit: dict                # {PlayerType: fit_score}
    best_fit_type: PlayerType

    # Entropy
    composite_entropy: float
    entropy_anomaly: bool
    entropy_details: dict

    # Pattern matching
    matched_patterns: list[dict]         # From ACO miner
    pattern_confidence: float            # Best match confidence

    # Network
    network_features: dict               # From graph analysis

    # Composite
    game_theory_suspicion_score: float   # 0-100 final score

    def to_classifier_context(self) -> str:
        """Generate context string for Mistral classification prompts."""
        lines = []
        lines.append(f"Game Theory Analysis:")
        lines.append(f"  Best-fit player type: {self.best_fit_type.value}")
        lines.append(f"  Behavioral deviation: {self.behavioral_deviation_score:.1f}/100")
        lines.append(f"  Behavioral entropy: {self.composite_entropy:.3f} "
                     f"({'ANOMALOUS' if self.entropy_anomaly else 'normal'})")

        if self.matched_patterns:
            best = self.matched_patterns[0]
            lines.append(f"  Matched suspicious pattern: "
                        f"{' -> '.join(best['pattern'])} "
                        f"(confidence: {best['confidence']:.2f})")

        nf = self.network_features
        lines.append(f"  Network: {nf.get('correlated_wallets_count', 0)} "
                     f"correlated wallets, "
                     f"component size {nf.get('component_size', 1)}")

        return '\n'.join(lines)


def compute_game_theory_score(
    deviation_score: float,
    entropy_result: dict,
    pattern_matches: list[dict],
    network_features: dict
) -> float:
    """
    Weighted composite of all game-theory-informed signals.
    Weights calibrated to favor temporal and behavioral signals.
    """
    weights = {
        'deviation': 0.30,
        'entropy': 0.20,
        'pattern': 0.25,
        'network': 0.25,
    }

    # Normalize each component to 0-100
    deviation_component = deviation_score  # Already 0-100

    entropy_component = 0
    if entropy_result.get('anomaly_flag'):
        entropy_component = 80
    elif entropy_result.get('composite_entropy', 999) < 1.0:
        entropy_component = 50

    pattern_component = 0
    if pattern_matches:
        pattern_component = min(100,
            pattern_matches[0].get('confidence', 0) * 100
        )

    network_component = min(100,
        network_features.get('correlated_wallets_count', 0) * 20 +
        network_features.get('neighbor_max_risk', 0) * 50 +
        (30 if network_features.get('funding_depth', 10) > 5 else 0)
    )

    composite = (
        weights['deviation'] * deviation_component +
        weights['entropy'] * entropy_component +
        weights['pattern'] * pattern_component +
        weights['network'] * network_component
    )

    return round(min(100, max(0, composite)), 1)
```

---

## 7. Integration with Sentinel Pipeline

### 7.1 New File: `src/detection/game_theory.py`

Contains: `PlayerProfile`, `BehavioralEntropyAnalyzer`, `ACOPatternMiner`, `WalletGraphAnalyzer`, `GameTheoryAnalysis`, and the composite scoring function.

### 7.2 Pipeline Integration

```python
# In SentinelPipeline.process_anomaly():

# After feature extraction, before Stage 1:
entropy = self.entropy_analyzer.compute_trading_entropy(wallet_trades)
gt_deviation = compute_behavioral_deviation(trade, equilibrium, profiles)
pattern_matches = self.aco_miner.match_pattern(encoded_sequence)
network_feats = self.graph_analyzer.compute_network_features(wallet_addr)

gt_analysis = GameTheoryAnalysis(
    behavioral_deviation_score=gt_deviation,
    composite_entropy=entropy['composite_entropy'],
    entropy_anomaly=entropy['anomaly_flag'],
    matched_patterns=pattern_matches,
    network_features=network_feats,
    game_theory_suspicion_score=compute_game_theory_score(...)
)

# Enrich Stage 1 prompt with game theory context
stage1_context = gt_analysis.to_classifier_context()
```

### 7.3 Dashboard Integration

Add to the Case Detail page:
- Radar chart showing player type fit scores
- Entropy breakdown visualization
- Network graph of wallet cluster (using the graph data)
- Pattern match timeline

---

## 8. Key Caveats from the Literature

1. **39% false alarm rate** (Sadiq et al.) -- ACO should be a signal, not a classifier. Always feed into the RF + Mistral pipeline.
2. **Synthetic data limitation** -- most papers validated on synthetic data. Sentinel's Arena provides real human labels, which is a significant advantage.
3. **Adversarial adaptation** -- the report notes no study tests against insiders who adapt. The game-theoretic framework explicitly models this (Nash equilibrium assumes rational adversaries), making Sentinel's approach more robust in theory.
4. **Computational cost** -- the report questions whether 95-99% accuracy justifies complexity vs. 80-85% with simpler methods. For Sentinel, the game theory layer runs once per flagged anomaly (not on every trade), keeping costs manageable.
