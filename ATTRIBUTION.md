# Attribution

This project incorporates code and patterns from the following open source projects:

## polymarket-insider-tracker

- **Repository**: https://github.com/pselamy/polymarket-insider-tracker
- **License**: MIT
- **Used for**:
  - Rate limiting (token bucket) pattern
  - Exponential backoff retry logic
  - Fresh wallet detection algorithm with confidence scoring
  - Category keyword matching for market classification
  - Risk scoring with weighted signal aggregation

**Files adapted**:
- `src/data/polymarket_client.py` - Rate limiter and retry decorator
- `src/data/websocket_handler.py` - WebSocket trade streaming with reconnection
- `src/detection/anomaly_detector.py` - Fresh wallet detection, confidence scoring
- `src/detection/wallet_profiler.py` - Wallet profiling, funding chain tracing
- `src/detection/cluster_analysis.py` - DBSCAN sniper clustering, composite risk scoring

## worldmonitor

- **Repository**: https://github.com/koala73/worldmonitor
- **License**: See repository
- **Used for**:
  - OSINT data source integrations (ACLED, GDELT, GDACS, NASA FIRMS)
  - Threat classification keyword system
  - Cache TTL alignment patterns
  - RSS feed aggregation patterns
  - Intelligence topic queries

**Files adapted**:
- `src/osint/sources.py` - ACLED, GDELT, GDACS clients, threat classification
- `src/osint/rss_aggregator.py` - RSS aggregation patterns

## Data Sources

The following external data sources are used:

| Source | Provider | License |
|--------|----------|---------|
| ACLED | Armed Conflict Location & Event Data Project | Requires registration |
| GDELT | GDELT Project | Public API |
| GDACS | UN OCHA / European Commission | Public API |
| NASA FIRMS | NASA | Public API (key required) |
| Polymarket | Polymarket Inc. | Public CLOB API |
