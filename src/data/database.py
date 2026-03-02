"""
Sentinel Database Module
SQLite database with WAL mode for anomaly detection and case management.
"""
import sqlite3
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from pathlib import Path

# Default database path
DEFAULT_DB_PATH = os.getenv("DATABASE_PATH", "./data/sentinel.db")
VALID_VOTES = {"agree", "disagree", "uncertain"}
VOTE_COLUMN_MAP = {
    "agree": "votes_agree",
    "disagree": "votes_disagree",
    "uncertain": "votes_uncertain",
}
logger = logging.getLogger(__name__)


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Get a database connection with WAL mode enabled."""
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db(db_path: str = DEFAULT_DB_PATH):
    """Context manager for database connections."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(db_path: str = DEFAULT_DB_PATH):
    """Initialize the database schema with all required tables."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # Table 1: anomaly_events
        # Raw trade anomalies detected from Polymarket
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anomaly_events (
                event_id TEXT PRIMARY KEY,
                market_id TEXT NOT NULL,
                market_name TEXT,
                timestamp TEXT NOT NULL,
                trade_timestamp TEXT,
                wallet_address TEXT,
                trade_size REAL,
                position_side TEXT,  -- 'YES' or 'NO'
                price_before REAL,
                price_after REAL,
                price_change REAL,
                volume_24h REAL,
                volume_spike_ratio REAL,
                z_score REAL,
                classification TEXT,  -- INSIDER, OSINT_EDGE, FAST_REACTOR, SPECULATOR
                bss_score INTEGER,  -- Behavioral Suspicion Score 0-100
                pes_score INTEGER,  -- Public Explainability Score 0-100
                confidence REAL,
                xai_narrative TEXT,
                fraud_triangle_json TEXT,  -- JSON with pressure, opportunity, rationalization
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table 2: osint_events
        # OSINT signals from RSS, GDELT, etc.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS osint_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,  -- 'rss', 'gdelt', 'acled', 'adsb'
                source_url TEXT,
                headline TEXT NOT NULL,
                content TEXT,
                category TEXT,  -- 'politics', 'sports', 'crypto', 'business'
                geolocation TEXT,  -- JSON with lat/lng
                relevance_score REAL,
                embedding_id TEXT,  -- Reference to ChromaDB embedding
                related_market_ids TEXT,  -- JSON array of market IDs
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table 3: wallet_profiles
        # Wallet history and behavioral patterns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallet_profiles (
                address TEXT PRIMARY KEY,
                first_seen TEXT,
                last_seen TEXT,
                trade_count INTEGER DEFAULT 0,
                win_count INTEGER DEFAULT 0,
                loss_count INTEGER DEFAULT 0,
                win_rate REAL,
                total_volume REAL DEFAULT 0,
                avg_position_size REAL,
                is_fresh_wallet INTEGER DEFAULT 0,  -- 1 if age < 7 days, trades < 5
                cluster_id TEXT,
                funding_chain TEXT,  -- JSON array of funding sources
                suspicious_flags TEXT,  -- JSON array of flags
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table 4: sentinel_index
        # Curated case database - the main "product"
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentinel_index (
                case_id TEXT PRIMARY KEY,
                anomaly_event_id TEXT,
                market_id TEXT NOT NULL,
                market_name TEXT,
                classification TEXT NOT NULL,
                bss_score INTEGER,
                pes_score INTEGER,
                temporal_gap_hours REAL,  -- Hours between trade and first public signal
                consensus_score REAL,  -- Arena voting consensus (0-100)
                vote_count INTEGER DEFAULT 0,
                votes_agree INTEGER DEFAULT 0,
                votes_disagree INTEGER DEFAULT 0,
                votes_uncertain INTEGER DEFAULT 0,
                status TEXT DEFAULT 'UNDER_REVIEW',  -- CONFIRMED, DISPUTED, UNDER_REVIEW
                sar_report TEXT,  -- Suspicious Activity Report (markdown)
                xai_summary TEXT,
                evidence_json TEXT,  -- JSON with all evidence
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (anomaly_event_id) REFERENCES anomaly_events(event_id)
            )
        """)

        # Table 5: arena_votes
        # Human-in-the-loop voting records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS arena_votes (
                vote_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                voter_id TEXT,
                vote TEXT NOT NULL,  -- 'agree', 'disagree', 'uncertain'
                confidence INTEGER,  -- Voter's confidence 1-5
                comment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES sentinel_index(case_id)
            )
        """)

        # Table 6: evidence_packets
        # Normalized real-time evidence packet per correlated case
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence_packets (
                packet_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                event_id TEXT,
                market_id TEXT NOT NULL,
                market_name TEXT,
                market_slug TEXT,
                wallet_address TEXT NOT NULL,
                trade_timestamp TEXT NOT NULL,
                side TEXT,
                outcome TEXT,
                trade_size REAL,
                trade_price REAL,
                wallet_age_hours REAL,
                wallet_trade_count INTEGER,
                wallet_win_rate REAL,
                wallet_risk_score REAL,
                is_fresh_wallet INTEGER DEFAULT 0,
                cluster_id TEXT,
                cluster_size INTEGER DEFAULT 0,
                cluster_confidence REAL,
                osint_event_id TEXT,
                osint_source TEXT,
                osint_title TEXT,
                osint_timestamp TEXT,
                temporal_gap_minutes REAL,
                temporal_gap_score REAL,
                correlation_score REAL,
                evidence_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES sentinel_index(case_id),
                FOREIGN KEY (event_id) REFERENCES anomaly_events(event_id)
            )
        """)

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_market ON anomaly_events(market_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_timestamp ON anomaly_events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_classification ON anomaly_events(classification)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_osint_timestamp ON osint_events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_osint_source ON osint_events(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentinel_status ON sentinel_index(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentinel_classification ON sentinel_index(classification)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence_packets(case_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_trade_ts ON evidence_packets(trade_timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_market ON evidence_packets(market_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_wallet ON evidence_packets(wallet_address)")

        conn.commit()
        logger.info("Database schema initialized successfully")


# ============================================================
# CRUD Operations for anomaly_events
# ============================================================

def insert_anomaly(conn: sqlite3.Connection, anomaly: Dict[str, Any]) -> str:
    """Insert or update an anomaly event keyed by ``event_id``."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO anomaly_events (
            event_id, market_id, market_name, timestamp, trade_timestamp,
            wallet_address, trade_size, position_side, price_before, price_after,
            price_change, volume_24h, volume_spike_ratio, z_score,
            classification, bss_score, pes_score, confidence, xai_narrative, fraud_triangle_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_id) DO UPDATE SET
            market_id = excluded.market_id,
            market_name = excluded.market_name,
            timestamp = excluded.timestamp,
            trade_timestamp = excluded.trade_timestamp,
            wallet_address = excluded.wallet_address,
            trade_size = excluded.trade_size,
            position_side = excluded.position_side,
            price_before = excluded.price_before,
            price_after = excluded.price_after,
            price_change = excluded.price_change,
            volume_24h = excluded.volume_24h,
            volume_spike_ratio = excluded.volume_spike_ratio,
            z_score = excluded.z_score,
            classification = excluded.classification,
            bss_score = excluded.bss_score,
            pes_score = excluded.pes_score,
            confidence = excluded.confidence,
            xai_narrative = excluded.xai_narrative,
            fraud_triangle_json = excluded.fraud_triangle_json,
            updated_at = CURRENT_TIMESTAMP
    """, (
        anomaly.get('event_id'),
        anomaly.get('market_id'),
        anomaly.get('market_name'),
        anomaly.get('timestamp'),
        anomaly.get('trade_timestamp'),
        anomaly.get('wallet_address'),
        anomaly.get('trade_size'),
        anomaly.get('position_side'),
        anomaly.get('price_before'),
        anomaly.get('price_after'),
        anomaly.get('price_change'),
        anomaly.get('volume_24h'),
        anomaly.get('volume_spike_ratio'),
        anomaly.get('z_score'),
        anomaly.get('classification'),
        anomaly.get('bss_score'),
        anomaly.get('pes_score'),
        anomaly.get('confidence'),
        anomaly.get('xai_narrative'),
        anomaly.get('fraud_triangle_json'),
    ))
    return anomaly.get('event_id')


def get_anomaly(conn: sqlite3.Connection, event_id: str) -> Optional[Dict]:
    """Get an anomaly event by ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM anomaly_events WHERE event_id = ?", (event_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def list_anomalies(
    conn: sqlite3.Connection,
    classification: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """List anomaly events with optional filtering."""
    cursor = conn.cursor()
    query = "SELECT * FROM anomaly_events"
    params = []

    if classification:
        query += " WHERE classification = ?"
        params.append(classification)

    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


# ============================================================
# CRUD Operations for osint_events
# ============================================================

def insert_osint_event(conn: sqlite3.Connection, event: Dict[str, Any]) -> str:
    """Insert a new OSINT event."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO osint_events (
            event_id, timestamp, source, source_url, headline, content,
            category, geolocation, relevance_score, embedding_id, related_market_ids
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event.get('event_id'),
        event.get('timestamp'),
        event.get('source'),
        event.get('source_url'),
        event.get('headline'),
        event.get('content'),
        event.get('category'),
        event.get('geolocation'),
        event.get('relevance_score'),
        event.get('embedding_id'),
        event.get('related_market_ids'),
    ))
    return event.get('event_id')


def get_osint_events_in_range(
    conn: sqlite3.Connection,
    start_time: str,
    end_time: str,
    limit: int = 100
) -> List[Dict]:
    """Get OSINT events within a time range."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM osint_events
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
        LIMIT ?
    """, (start_time, end_time, limit))
    return [dict(row) for row in cursor.fetchall()]


def get_osint_events_by_ids(
    conn: sqlite3.Connection,
    event_ids: List[str],
) -> List[Dict]:
    """Get OSINT events by a list of event IDs."""
    if not event_ids:
        return []
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in event_ids)
    cursor.execute(
        f"SELECT * FROM osint_events WHERE event_id IN ({placeholders}) ORDER BY timestamp ASC",
        event_ids,
    )
    return [dict(row) for row in cursor.fetchall()]


def get_osint_events_by_market(
    conn: sqlite3.Connection,
    market_id: str,
    limit: int = 50,
) -> List[Dict]:
    """Get OSINT events related to a market (via related_market_ids JSON)."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM osint_events
        WHERE related_market_ids LIKE ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (f"%{market_id}%", limit),
    )
    return [dict(row) for row in cursor.fetchall()]


def list_osint_events(
    conn: sqlite3.Connection,
    source: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple:
    """List OSINT events with optional filtering. Returns (items, total)."""
    cursor = conn.cursor()
    filters: List[str] = []
    params: List[Any] = []

    if source:
        filters.append("source = ?")
        params.append(source)
    if category:
        filters.append("category = ?")
        params.append(category)

    where = (" WHERE " + " AND ".join(filters)) if filters else ""

    cursor.execute(f"SELECT COUNT(*) FROM osint_events{where}", params)
    total = int(cursor.fetchone()[0])

    cursor.execute(
        f"SELECT * FROM osint_events{where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    )
    items = [dict(row) for row in cursor.fetchall()]
    return items, total


# ============================================================
# CRUD Operations for wallet_profiles
# ============================================================

def upsert_wallet(conn: sqlite3.Connection, wallet: Dict[str, Any]) -> str:
    """Insert or update a wallet profile."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO wallet_profiles (
            address, first_seen, last_seen, trade_count, win_count, loss_count,
            win_rate, total_volume, avg_position_size, is_fresh_wallet,
            cluster_id, funding_chain, suspicious_flags
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(address) DO UPDATE SET
            last_seen = excluded.last_seen,
            trade_count = excluded.trade_count,
            win_count = excluded.win_count,
            loss_count = excluded.loss_count,
            win_rate = excluded.win_rate,
            total_volume = excluded.total_volume,
            avg_position_size = excluded.avg_position_size,
            is_fresh_wallet = excluded.is_fresh_wallet,
            cluster_id = excluded.cluster_id,
            funding_chain = excluded.funding_chain,
            suspicious_flags = excluded.suspicious_flags,
            updated_at = CURRENT_TIMESTAMP
    """, (
        wallet.get('address'),
        wallet.get('first_seen'),
        wallet.get('last_seen'),
        wallet.get('trade_count', 0),
        wallet.get('win_count', 0),
        wallet.get('loss_count', 0),
        wallet.get('win_rate'),
        wallet.get('total_volume', 0),
        wallet.get('avg_position_size'),
        wallet.get('is_fresh_wallet', 0),
        wallet.get('cluster_id'),
        wallet.get('funding_chain'),
        wallet.get('suspicious_flags'),
    ))
    return wallet.get('address')


def get_wallet(conn: sqlite3.Connection, address: str) -> Optional[Dict]:
    """Get a wallet profile by address."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM wallet_profiles WHERE address = ?", (address,))
    row = cursor.fetchone()
    return dict(row) if row else None


# ============================================================
# CRUD Operations for sentinel_index
# ============================================================

def insert_case(conn: sqlite3.Connection, case: Dict[str, Any]) -> str:
    """Insert a new case into the Sentinel Index."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sentinel_index (
            case_id, anomaly_event_id, market_id, market_name, classification,
            bss_score, pes_score, temporal_gap_hours, consensus_score,
            status, sar_report, xai_summary, evidence_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        case.get('case_id'),
        case.get('anomaly_event_id'),
        case.get('market_id'),
        case.get('market_name'),
        case.get('classification'),
        case.get('bss_score'),
        case.get('pes_score'),
        case.get('temporal_gap_hours'),
        case.get('consensus_score'),
        case.get('status', 'UNDER_REVIEW'),
        case.get('sar_report'),
        case.get('xai_summary'),
        case.get('evidence_json'),
    ))
    return case.get('case_id')


def get_case(conn: sqlite3.Connection, case_id: str) -> Optional[Dict]:
    """Get a case from the Sentinel Index."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sentinel_index WHERE case_id = ?", (case_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def list_cases(
    conn: sqlite3.Connection,
    classification: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """List cases from the Sentinel Index."""
    cursor = conn.cursor()
    query = "SELECT * FROM sentinel_index WHERE 1=1"
    params = []

    if classification:
        query += " AND classification = ?"
        params.append(classification)

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def update_case_consensus(conn: sqlite3.Connection, case_id: str, vote: str):
    """Update case consensus after a vote."""
    cursor = conn.cursor()
    if vote not in VALID_VOTES:
        raise ValueError(
            f"Invalid vote '{vote}'. Expected one of: {sorted(VALID_VOTES)}"
        )

    # Increment the appropriate vote counter
    vote_column = VOTE_COLUMN_MAP[vote]
    cursor.execute(f"""
        UPDATE sentinel_index
        SET
            vote_count = vote_count + 1,
            {vote_column} = {vote_column} + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE case_id = ?
    """, (case_id,))

    # Recalculate consensus score
    cursor.execute("""
        UPDATE sentinel_index
        SET consensus_score = CASE
            WHEN vote_count > 0 THEN (votes_agree * 100.0) / vote_count
            ELSE 0
        END,
        status = CASE
            WHEN vote_count >= 5 AND (votes_agree * 100.0 / vote_count) >= 70 THEN 'CONFIRMED'
            WHEN vote_count >= 5 AND (votes_disagree * 100.0 / vote_count) >= 70 THEN 'DISPUTED'
            ELSE 'UNDER_REVIEW'
        END
        WHERE case_id = ?
    """, (case_id,))


# ============================================================
# CRUD Operations for arena_votes
# ============================================================

def insert_vote(conn: sqlite3.Connection, vote: Dict[str, Any]) -> str:
    """Insert a new arena vote."""
    vote_value = vote.get('vote')
    if vote_value not in VALID_VOTES:
        raise ValueError(
            f"Invalid vote '{vote_value}'. Expected one of: {sorted(VALID_VOTES)}"
        )

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO arena_votes (vote_id, case_id, voter_id, vote, confidence, comment)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        vote.get('vote_id'),
        vote.get('case_id'),
        vote.get('voter_id'),
        vote_value,
        vote.get('confidence'),
        vote.get('comment'),
    ))

    # Update case consensus
    update_case_consensus(conn, vote.get('case_id'), vote_value)

    return vote.get('vote_id')


def get_votes_for_case(conn: sqlite3.Connection, case_id: str) -> List[Dict]:
    """Get all votes for a case."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM arena_votes WHERE case_id = ? ORDER BY created_at DESC
    """, (case_id,))
    return [dict(row) for row in cursor.fetchall()]


# ============================================================
# CRUD Operations for evidence_packets
# ============================================================

def insert_evidence_packet(conn: sqlite3.Connection, packet: Dict[str, Any]) -> str:
    """Insert or replace a normalized evidence packet."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO evidence_packets (
            packet_id, case_id, event_id, market_id, market_name, market_slug,
            wallet_address, trade_timestamp, side, outcome, trade_size, trade_price,
            wallet_age_hours, wallet_trade_count, wallet_win_rate, wallet_risk_score,
            is_fresh_wallet, cluster_id, cluster_size, cluster_confidence,
            osint_event_id, osint_source, osint_title, osint_timestamp,
            temporal_gap_minutes, temporal_gap_score, correlation_score,
            evidence_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        packet.get("packet_id"),
        packet.get("case_id"),
        packet.get("event_id"),
        packet.get("market_id"),
        packet.get("market_name"),
        packet.get("market_slug"),
        packet.get("wallet_address"),
        packet.get("trade_timestamp"),
        packet.get("side"),
        packet.get("outcome"),
        packet.get("trade_size"),
        packet.get("trade_price"),
        packet.get("wallet_age_hours"),
        packet.get("wallet_trade_count"),
        packet.get("wallet_win_rate"),
        packet.get("wallet_risk_score"),
        packet.get("is_fresh_wallet", 0),
        packet.get("cluster_id"),
        packet.get("cluster_size", 0),
        packet.get("cluster_confidence"),
        packet.get("osint_event_id"),
        packet.get("osint_source"),
        packet.get("osint_title"),
        packet.get("osint_timestamp"),
        packet.get("temporal_gap_minutes"),
        packet.get("temporal_gap_score"),
        packet.get("correlation_score"),
        packet.get("evidence_json"),
    ))
    return packet.get("packet_id")


def get_evidence_packet(conn: sqlite3.Connection, case_id: str) -> Optional[Dict[str, Any]]:
    """Get an evidence packet by case ID."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM evidence_packets
            WHERE case_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (case_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.OperationalError:
        return None


def list_evidence_packets(
    conn: sqlite3.Connection,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List recent evidence packets."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM evidence_packets
            ORDER BY trade_timestamp DESC, created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []


# ============================================================
# Utility Functions
# ============================================================

def get_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Get database statistics."""
    cursor = conn.cursor()

    stats = {}

    cursor.execute("SELECT COUNT(*) FROM anomaly_events")
    stats['total_anomalies'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM osint_events")
    stats['total_osint_events'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM wallet_profiles")
    stats['total_wallets'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM sentinel_index")
    stats['total_cases'] = cursor.fetchone()[0]

    try:
        cursor.execute("SELECT COUNT(*) FROM evidence_packets")
        stats['total_evidence_packets'] = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        stats['total_evidence_packets'] = 0

    cursor.execute("""
        SELECT classification, COUNT(*) as count
        FROM sentinel_index
        GROUP BY classification
    """)
    stats['cases_by_classification'] = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM sentinel_index
        GROUP BY status
    """)
    stats['cases_by_status'] = {row[0]: row[1] for row in cursor.fetchall()}

    return stats


if __name__ == "__main__":
    # Initialize schema when run directly
    init_schema()
    print("\nDatabase initialized at:", DEFAULT_DB_PATH)

    # Print stats
    with get_db() as conn:
        stats = get_stats(conn)
        print("\nDatabase stats:", stats)
