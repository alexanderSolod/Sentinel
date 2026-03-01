"""Sentinel FastAPI backend."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import logging
import os
import sqlite3
import threading
import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from src.classification.evaluation import compute_evaluation_metrics
from src.data.database import (
    DEFAULT_DB_PATH,
    get_anomaly,
    get_case,
    get_connection,
    get_evidence_packet,
    get_osint_events_by_ids,
    get_osint_events_by_market,
    get_stats,
    init_schema,
    get_votes_for_case,
    insert_vote,
    list_evidence_packets,
)

logger = logging.getLogger(__name__)

# Simple API key auth for mutating endpoints.
# Set SENTINEL_API_KEY in .env; if unset, auth is disabled (open demo mode).
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_SENTINEL_API_KEY = os.getenv("SENTINEL_API_KEY")


async def _require_api_key(
    api_key: Optional[str] = Security(_api_key_header),
) -> None:
    """Reject requests to protected endpoints when an API key is configured."""
    if _SENTINEL_API_KEY is None:
        return  # auth disabled — open demo mode
    if api_key != _SENTINEL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


_schema_init_lock = threading.Lock()
_schema_initialized_path: Optional[str] = None


@asynccontextmanager
async def _lifespan(_: FastAPI):
    """Best-effort schema init so fresh deployments don't return 500s."""
    try:
        _ensure_schema()
    except HTTPException as exc:  # pragma: no cover - startup fallback
        logger.error("%s", exc.detail)
    yield


app = FastAPI(
    title="Sentinel API",
    description="Live evidence correlation and case intelligence API",
    version="0.2.0",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class VoteRequest(BaseModel):
    """Request payload for Arena vote submissions."""

    case_id: str = Field(min_length=1)
    vote: Literal["agree", "disagree", "uncertain"]
    voter_id: str = Field(default="anonymous", min_length=1, max_length=128)
    confidence: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)
    vote_id: Optional[str] = Field(default=None, min_length=1, max_length=64)


def _database_path() -> str:
    return os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)


def _ensure_schema() -> None:
    """Initialize schema once per active DB path."""
    global _schema_initialized_path

    db_path = _database_path()
    if _schema_initialized_path == db_path:
        return

    with _schema_init_lock:
        if _schema_initialized_path == db_path:
            return
        try:
            init_schema(db_path)
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(
                status_code=503,
                detail=f"Database initialization failed for {db_path}: {exc}",
            ) from exc
        _schema_initialized_path = db_path


def _connect() -> sqlite3.Connection:
    _ensure_schema()
    return get_connection(_database_path())


def _decode_json_field(payload: Dict[str, Any], field_name: str, target_name: str) -> Dict[str, Any]:
    data = dict(payload)
    raw_value = data.get(field_name)
    if isinstance(raw_value, str):
        try:
            data[target_name] = json.loads(raw_value)
        except json.JSONDecodeError:
            data[target_name] = None
    elif raw_value is not None:
        data[target_name] = raw_value
    return data


def _decode_anomaly(anomaly: Dict[str, Any]) -> Dict[str, Any]:
    return _decode_json_field(anomaly, "fraud_triangle_json", "fraud_triangle")


def _decode_case(case: Dict[str, Any]) -> Dict[str, Any]:
    return _decode_json_field(case, "evidence_json", "evidence")


def _decode_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    return _decode_json_field(packet, "evidence_json", "evidence")


def _resolve_osint_events(
    conn: "sqlite3.Connection",
    evidence: Optional[Dict[str, Any]],
    market_id: Optional[str],
) -> List[Dict[str, Any]]:
    """Resolve related OSINT events from evidence IDs or market matching."""
    # Try osint_event_ids from evidence JSON first
    if evidence:
        event_ids = evidence.get("osint_event_ids")
        if isinstance(event_ids, list) and event_ids:
            events = get_osint_events_by_ids(conn, event_ids)
            if events:
                return events

    # Fallback: search by market_id in related_market_ids
    if market_id:
        return get_osint_events_by_market(conn, market_id)

    return []


def _where_clause(filters: List[str]) -> str:
    if not filters:
        return ""
    return " WHERE " + " AND ".join(filters)


@app.get("/api/health")
def health() -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn = _connect()
        try:
            stats = get_stats(conn)
        finally:
            conn.close()
        return {
            "status": "ok",
            "timestamp": now,
            "database": {
                "status": "ok",
                "path": _database_path(),
            },
            "stats": stats,
        }
    except Exception as exc:  # pragma: no cover - defensive
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "timestamp": now,
                "database": {"status": "error", "path": _database_path()},
                "error": str(exc),
            },
        )


@app.get("/api/metrics")
def evaluation_metrics(
    min_votes: int = Query(default=5, ge=1),
    include_osint_edge: bool = Query(default=False),
) -> Dict[str, Any]:
    positive_classes = ["INSIDER", "OSINT_EDGE"] if include_osint_edge else ["INSIDER"]
    conn = _connect()
    try:
        metrics = compute_evaluation_metrics(
            conn,
            min_votes=min_votes,
            positive_classes=positive_classes,
        )
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "evaluation": metrics,
        }
    finally:
        conn.close()


@app.get("/api/anomalies")
def list_anomalies(
    classification: Optional[str] = Query(default=None),
    market_id: Optional[str] = Query(default=None),
    wallet_address: Optional[str] = Query(default=None),
    min_bss: Optional[int] = Query(default=None, ge=0, le=100),
    max_bss: Optional[int] = Query(default=None, ge=0, le=100),
    min_confidence: Optional[float] = Query(default=None, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    conn = _connect()
    try:
        filters: List[str] = []
        params: List[Any] = []

        if classification:
            filters.append("classification = ?")
            params.append(classification)
        if market_id:
            filters.append("market_id = ?")
            params.append(market_id)
        if wallet_address:
            filters.append("wallet_address = ?")
            params.append(wallet_address.lower())
        if min_bss is not None:
            filters.append("bss_score >= ?")
            params.append(min_bss)
        if max_bss is not None:
            filters.append("bss_score <= ?")
            params.append(max_bss)
        if min_confidence is not None:
            filters.append("confidence >= ?")
            params.append(min_confidence)

        where = _where_clause(filters)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM anomaly_events{where}", params)
        total = int(cursor.fetchone()[0])

        cursor.execute(
            f"""
            SELECT * FROM anomaly_events
            {where}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        )
        items = [_decode_anomaly(dict(row)) for row in cursor.fetchall()]

        return {
            "count": len(items),
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        }
    finally:
        conn.close()


@app.get("/api/cases/{case_id}")
def get_case_details(case_id: str) -> Dict[str, Any]:
    conn = _connect()
    try:
        case = get_case(conn, case_id)

        # Fallback: look up by anomaly_event_id (when navigating from anomaly feed)
        if case is None:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sentinel_index WHERE anomaly_event_id = ? LIMIT 1",
                (case_id,),
            )
            row = cursor.fetchone()
            if row:
                case = dict(row)

        # Last fallback: build a synthetic case from the anomaly itself
        if case is None:
            anomaly = get_anomaly(conn, case_id)
            if anomaly:
                osint_events = _resolve_osint_events(
                    conn, None, anomaly.get("market_id"),
                )
                return {
                    "case": {
                        "case_id": case_id,
                        "anomaly_event_id": case_id,
                        "market_id": anomaly.get("market_id"),
                        "market_name": anomaly.get("market_name"),
                        "classification": anomaly.get("classification"),
                        "bss_score": anomaly.get("bss_score"),
                        "pes_score": anomaly.get("pes_score"),
                        "temporal_gap_hours": None,
                        "consensus_score": None,
                        "vote_count": 0,
                        "votes_agree": 0,
                        "votes_disagree": 0,
                        "votes_uncertain": 0,
                        "status": "UNDER_REVIEW",
                        "sar_report": None,
                        "xai_summary": anomaly.get("xai_narrative"),
                        "evidence": None,
                        "created_at": anomaly.get("created_at"),
                        "updated_at": anomaly.get("updated_at"),
                    },
                    "anomaly": _decode_anomaly(anomaly),
                    "evidence_packet": _decode_packet(get_evidence_packet(conn, case_id)) if get_evidence_packet(conn, case_id) else None,
                    "osint_events": osint_events,
                    "votes": [],
                    "vote_count": 0,
                }

        if case is None:
            raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

        resolved_case_id = case.get("case_id", case_id)

        anomaly = None
        anomaly_event_id = case.get("anomaly_event_id")
        if anomaly_event_id:
            anomaly = get_anomaly(conn, anomaly_event_id)

        evidence_packet = get_evidence_packet(conn, resolved_case_id)
        votes = get_votes_for_case(conn, resolved_case_id)

        # Resolve related OSINT events
        decoded_case = _decode_case(case)
        evidence_data = decoded_case.get("evidence")
        osint_events = _resolve_osint_events(
            conn, evidence_data, case.get("market_id"),
        )

        return {
            "case": decoded_case,
            "anomaly": _decode_anomaly(anomaly) if anomaly else None,
            "evidence_packet": _decode_packet(evidence_packet) if evidence_packet else None,
            "osint_events": osint_events,
            "votes": votes,
            "vote_count": len(votes),
        }
    finally:
        conn.close()


@app.get("/api/index")
def query_index(
    classification: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Market name substring match"),
    min_bss: Optional[int] = Query(default=None, ge=0, le=100),
    min_consensus: Optional[float] = Query(default=None, ge=0.0, le=100.0),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    conn = _connect()
    try:
        filters: List[str] = []
        params: List[Any] = []

        if classification:
            filters.append("classification = ?")
            params.append(classification)
        if status:
            filters.append("status = ?")
            params.append(status)
        if search:
            filters.append("market_name LIKE ?")
            params.append(f"%{search}%")
        if min_bss is not None:
            filters.append("bss_score >= ?")
            params.append(min_bss)
        if min_consensus is not None:
            filters.append("consensus_score >= ?")
            params.append(min_consensus)

        where = _where_clause(filters)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM sentinel_index{where}", params)
        total = int(cursor.fetchone()[0])

        cursor.execute(
            f"""
            SELECT * FROM sentinel_index
            {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        )
        items = [_decode_case(dict(row)) for row in cursor.fetchall()]

        return {
            "count": len(items),
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        }
    finally:
        conn.close()


@app.post("/api/vote", dependencies=[Depends(_require_api_key)])
def submit_vote(payload: VoteRequest) -> Dict[str, Any]:
    conn = _connect()
    try:
        case = get_case(conn, payload.case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"Case not found: {payload.case_id}")

        vote_id = payload.vote_id or str(uuid.uuid4())[:8]
        insert_vote(
            conn,
            {
                "vote_id": vote_id,
                "case_id": payload.case_id,
                "voter_id": payload.voter_id,
                "vote": payload.vote,
                "confidence": payload.confidence,
                "comment": payload.comment,
            },
        )
        conn.commit()
        updated_case = get_case(conn, payload.case_id)

        return {
            "status": "recorded",
            "vote_id": vote_id,
            "case_id": payload.case_id,
            "vote": payload.vote,
            "updated_case": _decode_case(updated_case) if updated_case else None,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        conn.close()


@app.get("/api/evidence")
def list_evidence(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    conn = _connect()
    try:
        packets = list_evidence_packets(conn, limit=limit, offset=offset)
        return {
            "count": len(packets),
            "limit": limit,
            "offset": offset,
            "items": [_decode_packet(packet) for packet in packets],
        }
    finally:
        conn.close()


@app.get("/api/evidence/{case_id}")
def get_evidence(case_id: str) -> Dict[str, Any]:
    conn = _connect()
    try:
        packet = get_evidence_packet(conn, case_id)
        if packet is None:
            raise HTTPException(status_code=404, detail=f"No evidence packet found for case_id={case_id}")
        return _decode_packet(packet)
    finally:
        conn.close()
