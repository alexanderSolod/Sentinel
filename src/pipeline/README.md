# Real-Time Pipeline

Connects to Polymarket's WebSocket, grabs every trade, and runs it through wallet profiling, cluster detection, OSINT correlation, and AI classification. This is what you run in production.

## Evidence correlator (`evidence_correlator.py`)

### EvidenceCorrelator

Processes trades as they come in:

```
WebSocket Trade ─→ Wallet Profiling ─→ Cluster Analysis ─→ OSINT Correlation
                                                                  │
                                                                  ▼
                                                        Feature Extraction
                                                                  │
                                                                  ▼
                                                    5-Gate FP Cascade (optional)
                                                                  │
                                                                  ▼
                                                      AI Classification (Stages 1-3)
                                                                  │
                                                                  ▼
                                                      Evidence Packet ─→ Database
```

Per trade, the pipeline runs through: wallet profiling (history, win rate, funding chain) → DBSCAN cluster check → OSINT correlation (temporal gap) → streaming z-score → autoencoder scoring → 5-gate false positive filter → AI classification (Stages 1-3) → persist evidence packet to database.

### Running live

```bash
# Start the API server first
python main.py api

# In another terminal:
python main.py monitor --live    # Ctrl+C to stop
```

Connects to Polymarket's WebSocket, processes each `TradeEvent`, and saves evidence packets. The dashboard auto-refreshes to show new cases.

### Mock data

```bash
python main.py monitor --mock        # 20 trades (default)
python main.py monitor --mock 50     # 50 trades
python main.py monitor --mock 200    # 200 trades, 0.25s delay each
```

Generates synthetic trades with a mix of insider/edge/reactor/speculator patterns. Still hits the Mistral API for classification — mock only applies to the trade data, not the AI.

### Correlation score

Each evidence packet includes a correlation score — a weighted composite of four signals:

| Signal | Weight | Source |
|--------|--------|--------|
| Wallet risk flags | 0.3 | Wallet profiler |
| Cluster confidence | 0.2 | DBSCAN sniper detector |
| Temporal gap score | 0.3 | OSINT correlator |
| Volume z-score | 0.2 | Streaming detector |

### Temporal gap scoring

`compute_temporal_gap_score()` converts the raw hours-before-news value into a 0-1 suspicion score:

| Gap | Score | Interpretation |
|-----|-------|---------------|
| > 6h before news | 0.95+ | Almost certainly insider |
| 2-6h before news | 0.70-0.95 | Highly suspicious |
| 0-2h before news | 0.40-0.70 | Suspicious but not conclusive |
| After news | 0.10-0.30 | Likely legitimate |
| No news correlation | 0.15 | Neutral |

## Demo stream (`demo_stream.py`)

Generates synthetic trade streams for demos and development. `main.py init` uses this to seed the database with pre-classified cases.

## Data flow

```
Polymarket WebSocket
        │
        ▼
TradeStreamHandler (src/data/websocket_handler.py)
        │
        ▼
EvidenceCorrelator.process_trade()
        │
        ├─→ WalletProfiler
        ├─→ SniperDetector (DBSCAN)
        ├─→ OSINTAggregator
        ├─→ StreamingAnomalyDetector
        ├─→ TradingAutoencoder
        ├─→ FalsePositiveGate
        └─→ SentinelPipeline (Stages 1-3)
                │
                ▼
        Evidence Packet ─→ SQLite (evidence_packets table)
                         ─→ Sentinel Index (sentinel_index table)
```

## Files

| File | Purpose |
|------|---------|
| `evidence_correlator.py` | Main real-time trade processing pipeline |
| `demo_stream.py` | Synthetic trade generation for demos |
