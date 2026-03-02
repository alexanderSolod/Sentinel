# OSINT Intelligence

Pulls open-source intelligence from 5 data sources, stores it in a vector DB for semantic search, and correlates signals to prediction market trades. The whole point: measure the **temporal gap** between a trade and the nearest public signal. That gap is what the [classification pipeline](../classification/README.md) uses to decide insider vs. legitimate.

## Module Overview

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

## Data Sources (`sources.py`)

### OSINTAggregator

Single interface for all 5 intelligence sources. Each source returns `OSINTEvent` objects with:
- `source`, `headline`, `timestamp`, `location`, `threat_level`, `raw_data`

| Source | Data | Auth | Cache TTL | Threat Levels |
|--------|------|------|-----------|---------------|
| **RSS** | Reuters, AP, BBC, Bloomberg, + 8 more | None | 5 min | Based on keyword analysis |
| **GDELT** | Global news tone analysis, event counts | None | 5 min | Tone score mapping |
| **GDACS** | UN disaster alerts (earthquakes, floods, cyclones) | None | 15 min | Alert level (Red/Orange/Green) |
| **ACLED** | Armed conflict events, political violence | `ACLED_ACCESS_TOKEN` | 15 min | Fatality-based |
| **NASA FIRMS** | Active fire/thermal anomaly detection | `NASA_FIRMS_API_KEY` | 30 min | Brightness/confidence |

### Threat Classification

Keyword matching assigns threat levels to each event:

| Level | Meaning | Example Keywords |
|-------|---------|-----------------|
| CRITICAL | Imminent, large-scale threat | nuclear, invasion, assassination |
| HIGH | Active conflict/disaster | airstrike, earthquake, sanctions |
| MEDIUM | Elevated tensions | protest, deployment, tariff |
| LOW | Developing situation | negotiation, warning, monitoring |
| INFO | Background intelligence | report, analysis, forecast |

## RSS Aggregator (`rss_aggregator.py`)

Aggregates 12 RSS feeds in parallel:

- Reuters (Top News, World, Business)
- AP News (Top, World)
- BBC News (Top, World)
- Bloomberg
- Al Jazeera
- CNBC World
- NPR News
- The Guardian World

Deduplicates by headline similarity and normalizes timestamps.

## Vector Store (`vector_store.py`)

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

**Embedding fallback:** If Mistral Embed is unavailable, falls back to `sentence-transformers/all-MiniLM-L6-v2` for local embeddings.

Stage 2 deep analysis uses this for RAG context -- it pulls relevant OSINT signals when building the Fraud Triangle analysis.

## Market-OSINT Correlator (`correlator.py`)

### MarketCorrelator

This is where the temporal gap math happens. Matches OSINT events to prediction markets and computes the time delta.

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

### Information Asymmetry Patterns

| Pattern | Meaning | Implication |
|---------|---------|-------------|
| `TRADE_WELL_BEFORE_INFO` | Trade > 6h before any signal | Highly suspicious |
| `TRADE_BEFORE_INFO` | Trade before signals, no pre-trade info | Suspicious |
| `TRADE_AFTER_INFO` | Signals existed before trade | Legitimate (OSINT_EDGE) |
| `NO_SIGNALS` | No matched OSINT events | Inconclusive |
| `MIXED_SIGNALS` | Some before, some after | Requires deeper analysis |

### Anomaly Enrichment

`correlator.enrich_anomaly()` adds fields to an anomaly dict before it enters the classification pipeline:
- `osint_signals_before_trade`
- `hours_before_news`
- `information_asymmetry`
- `matched_osint_events`

## Text Analyzer (`text_analyzer.py`)

### OSINTTextAnalyzer

NLP-based relevance scoring between OSINT events and market questions:
- Keyword extraction from market names
- TF-IDF similarity scoring
- Entity matching (countries, organizations, events)
- Used by the correlator to rank matched OSINT events by relevance

## Files

| File | Purpose |
|------|---------|
| `sources.py` | GDELT, GDACS, ACLED, NASA FIRMS clients + OSINTAggregator |
| `rss_aggregator.py` | 12-feed RSS aggregation with deduplication |
| `vector_store.py` | ChromaDB + Mistral Embed semantic search |
| `correlator.py` | Market-OSINT temporal gap calculation |
| `text_analyzer.py` | NLP relevance scoring |
