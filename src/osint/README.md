# OSINT Intelligence

Pulls open-source intelligence from 5 data sources, stores it in a vector DB for semantic search, and correlates signals to prediction market trades. The whole point: measure the **temporal gap** between a trade and the nearest public signal. That gap is what the [classification pipeline](../classification/README.md) uses to decide insider vs. legitimate.

## How it fits together

```
       RSS Feeds (12)          GDELT          GDACS         ACLED       NASA FIRMS
            │                   │               │              │             │
            └───────────────────┴───────────────┴──────────────┴─────────────┘
                                         │
                                         ▼
                               ┌──────────────────┐
                               │  OSINTAggregator  │  sources.py
                               │  Unified API      │
                               └────────┬─────────┘
                                        │
                            ┌───────────┴───────────┐
                            ▼                       ▼
                   ┌─────────────────┐    ┌──────────────────┐
                   │   VectorStore   │    │ MarketCorrelator │
                   │   ChromaDB +    │    │ Temporal gap      │
                   │   Mistral Embed │    │ calculation       │
                   └─────────────────┘    └──────────────────┘
```

## Data sources (`sources.py`)

### OSINTAggregator

Single interface for all 5 sources. Each returns `OSINTEvent` objects with `source`, `headline`, `timestamp`, `location`, `threat_level`, and `raw_data`.

| Source | Data | Auth | Cache TTL | Threat Levels |
|--------|------|------|-----------|---------------|
| **RSS** | Reuters, AP, BBC, Bloomberg, + 8 more | None | 5 min | Based on keyword analysis |
| **GDELT** | Global news tone analysis, event counts | None | 5 min | Tone score mapping |
| **GDACS** | UN disaster alerts (earthquakes, floods, cyclones) | None | 15 min | Alert level (Red/Orange/Green) |
| **ACLED** | Armed conflict events, political violence | `ACLED_ACCESS_TOKEN` | 15 min | Fatality-based |
| **NASA FIRMS** | Active fire/thermal anomaly detection | `NASA_FIRMS_API_KEY` | 30 min | Brightness/confidence |

### Threat classification

Keyword matching assigns threat levels:

| Level | Meaning | Example Keywords |
|-------|---------|-----------------|
| CRITICAL | Imminent, large-scale threat | nuclear, invasion, assassination |
| HIGH | Active conflict/disaster | airstrike, earthquake, sanctions |
| MEDIUM | Elevated tensions | protest, deployment, tariff |
| LOW | Developing situation | negotiation, warning, monitoring |
| INFO | Background intelligence | report, analysis, forecast |

## RSS aggregator (`rss_aggregator.py`)

Pulls from 12 feeds in parallel — Reuters (3 feeds), AP (2), BBC (2), Bloomberg, Al Jazeera, CNBC World, NPR, and The Guardian. Deduplicates by headline similarity and normalizes timestamps.

## Vector store (`vector_store.py`)

### VectorStore

ChromaDB-backed semantic search using **Mistral Embed**:

```python
store = VectorStore()
store.add_osint_objects(osint_events)

# Semantic search
results = store.search("Iranian military activity", k=5)

# Market-specific search
results = store.search_by_market("Will Iran strike Israel?", k=10)

# Time-windowed search
results = store.search_time_window(query, start_dt, end_dt)
```

Falls back to `sentence-transformers/all-MiniLM-L6-v2` for local embeddings if Mistral Embed is unavailable.

Stage 2 deep analysis uses the vector store for RAG context — it pulls relevant OSINT signals when building the Fraud Triangle analysis.

## Market-OSINT correlator (`correlator.py`)

### MarketCorrelator

Where the temporal gap math happens. Matches OSINT events to prediction markets and computes the time delta.

```python
correlator = MarketCorrelator(vector_store=store)
result = correlator.correlate("Will Iran strike?", trade_timestamp)

result.primary_gap_hours      # -8.0 (trade was 8h BEFORE news)
result.signal_count_before    # 0 (no public signals existed)
result.information_asymmetry_indicator  # "TRADE_BEFORE_INFO"
```

### CorrelationResult

| Field | Type | Description |
|-------|------|-------------|
| `primary_gap_hours` | float | Hours between trade and most relevant signal (negative = before) |
| `signal_count_before` | int | OSINT signals that existed before the trade |
| `signal_count_after` | int | OSINT signals that appeared after the trade |
| `information_asymmetry_indicator` | str | Pattern classification |
| `matched_events` | list | Matched OSINT events with relevance scores |

### Information asymmetry patterns

| Pattern | Meaning | Implication |
|---------|---------|-------------|
| `TRADE_WELL_BEFORE_INFO` | Trade > 6h before any signal | Highly suspicious |
| `TRADE_BEFORE_INFO` | Trade before signals, no pre-trade info | Suspicious |
| `TRADE_AFTER_INFO` | Signals existed before trade | Legitimate (OSINT_EDGE) |
| `NO_SIGNALS` | No matched OSINT events | Inconclusive |
| `MIXED_SIGNALS` | Some before, some after | Requires deeper analysis |

### Anomaly enrichment

`correlator.enrich_anomaly()` adds four fields to an anomaly dict before it enters the classification pipeline: `osint_signals_before_trade`, `hours_before_news`, `information_asymmetry`, and `matched_osint_events`.

## Text analyzer (`text_analyzer.py`)

### OSINTTextAnalyzer

Scores how relevant an OSINT event is to a given market question. Extracts keywords from market names, runs TF-IDF similarity, and matches entities (countries, organizations, event types). The correlator uses this to rank its matches.

## Files

| File | Purpose |
|------|---------|
| `sources.py` | GDELT, GDACS, ACLED, NASA FIRMS clients + OSINTAggregator |
| `rss_aggregator.py` | 12-feed RSS aggregation with deduplication |
| `vector_store.py` | ChromaDB + Mistral Embed semantic search |
| `correlator.py` | Market-OSINT temporal gap calculation |
| `text_analyzer.py` | NLP relevance scoring |
