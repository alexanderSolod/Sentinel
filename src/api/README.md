# REST API

FastAPI backend. Serves data to the React dashboard and exposes endpoints for external use.

## Running

```bash
python main.py api
# Starts on http://localhost:8000
```

The React dashboard (`ui/`) proxies API calls to this server via Vite's dev proxy.

## Authentication

Set `SENTINEL_API_KEY` in `.env` to protect mutating endpoints. If unset, the API runs in **open demo mode** (no auth required).

Protected endpoints require the `X-API-Key` header:

```bash
curl -X POST http://localhost:8000/api/vote \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"case_id": "CASE-abc", "vote": "agree", "confidence": 0.9}'
```

## Endpoints

### Health & Metrics

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | System health check with database stats |
| `GET` | `/api/metrics` | Evaluation metrics (FPR, FNR, confusion matrix) |

### Anomalies

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/anomalies` | List/filter anomaly events |

**Query parameters:**
- `classification` — filter by class (INSIDER, OSINT_EDGE, etc.)
- `market_id` — filter by market
- `wallet_address` — filter by wallet
- `min_bss`, `max_bss` — BSS score range
- `min_confidence` — minimum confidence threshold
- `limit`, `offset` — pagination

### Cases

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/cases/{case_id}` | Full case details with anomaly, evidence, and votes |

Returns everything about a case: anomaly data, evidence packet (wallet profile, OSINT signals, temporal gap), arena votes, classification details (BSS, PES, reasoning), and SAR report if one was generated.

### Sentinel Index

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/index` | Query the curated case database |

**Query parameters:**
- `classification` — filter by class
- `status` — filter by status (UNDER_REVIEW, CONFIRMED, DISMISSED)
- `search` — full-text search on market name
- `min_bss`, `min_consensus` — score thresholds
- `limit`, `offset` — pagination

### Evidence

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/evidence` | List evidence packets with pagination |
| `GET` | `/api/evidence/{case_id}` | Get evidence packet for a specific case |

### Voting (Arena)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/api/vote` | Submit an arena vote | Requires `X-API-Key` if configured |

**Request body:**

```json
{
  "case_id": "CASE-abc12345",
  "vote": "agree",
  "confidence": 0.85,
  "reviewer_id": "optional-reviewer-name"
}
```

Vote values: `agree`, `disagree`, `uncertain`

### OSINT

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/osint` | List OSINT events |

## CORS

CORS is configured to allow requests from `localhost:5173` (Vite dev server) and `localhost:4173` (Vite preview).

## Database

The SQLite schema is created on startup if it doesn't exist. Path defaults to `./data/sentinel.db` (override with `DATABASE_PATH` env var).

## Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app with all route definitions |
