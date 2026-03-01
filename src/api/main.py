"""Sentinel FastAPI backend."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import sqlite3
import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.classification.evaluation import compute_evaluation_metrics
from src.data.database import (
    DEFAULT_DB_PATH,
    get_anomaly,
    get_case,
    get_connection,
    get_evidence_packet,
    get_stats,
    get_votes_for_case,
    insert_vote,
    list_evidence_packets,
)

app = FastAPI(
    title="Sentinel API",
    description="Live evidence correlation and case intelligence API",
    version="0.2.0",
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


def _connect() -> sqlite3.Connection:
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
        if case is None:
            raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

        anomaly = None
        anomaly_event_id = case.get("anomaly_event_id")
        if anomaly_event_id:
            anomaly = get_anomaly(conn, anomaly_event_id)

        evidence_packet = get_evidence_packet(conn, case_id)
        votes = get_votes_for_case(conn, case_id)

        return {
            "case": _decode_case(case),
            "anomaly": _decode_anomaly(anomaly) if anomaly else None,
            "evidence_packet": _decode_packet(evidence_packet) if evidence_packet else None,
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


@app.post("/api/vote")
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
