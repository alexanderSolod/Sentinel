"""
ChromaDB Vector Store for OSINT Events

Embeds OSINT events using Mistral Embed and stores them in ChromaDB
for similarity search / RAG context retrieval in the classification pipeline.

Usage:
    store = VectorStore()
    store.add_events(osint_events)
    results = store.search("tariff announcement", k=5)
"""
import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
COLLECTION_NAME = "osint_events"
EMBED_MODEL = "mistral-embed"
EMBED_BATCH_SIZE = 25  # Mistral embed batch limit


class VectorStore:
    """ChromaDB-backed vector store for OSINT events."""

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.persist_dir = persist_dir or CHROMA_PERSIST_DIR
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self._client = None
        self._collection = None
        self._mistral = None

    @property
    def client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=self.persist_dir)
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    @property
    def mistral(self):
        if self._mistral is None and self.api_key:
            try:
                from mistralai import Mistral
                self._mistral = Mistral(api_key=self.api_key)
            except ImportError:
                logger.warning("mistralai package not installed")
        return self._mistral

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed texts using Mistral Embed API, with fallback to simple hash."""
        if self.mistral:
            try:
                all_embeddings = []
                for i in range(0, len(texts), EMBED_BATCH_SIZE):
                    batch = texts[i : i + EMBED_BATCH_SIZE]
                    resp = self.mistral.embeddings.create(
                        model=EMBED_MODEL,
                        inputs=batch,
                    )
                    all_embeddings.extend([d.embedding for d in resp.data])
                return all_embeddings
            except Exception as e:
                logger.warning("Mistral Embed failed, using fallback: %s", e)

        # Fallback: let ChromaDB use its default embedding function
        return []

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def _event_to_text(self, event: Dict[str, Any]) -> str:
        """Convert an OSINT event dict to a searchable text string."""
        parts = []
        if event.get("title"):
            parts.append(event["title"])
        if event.get("description"):
            parts.append(event["description"])
        if event.get("source"):
            parts.append(f"Source: {event['source']}")
        if event.get("category"):
            parts.append(f"Category: {event['category']}")
        if event.get("country"):
            parts.append(f"Country: {event['country']}")
        if event.get("threat_level"):
            parts.append(f"Threat: {event['threat_level']}")
        return " | ".join(parts) if parts else "Unknown event"

    def _event_to_metadata(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for ChromaDB storage."""
        meta = {}
        for key in ["source", "category", "threat_level", "country", "url", "event_id"]:
            val = event.get(key)
            if val is not None:
                meta[key] = str(val)

        ts = event.get("timestamp")
        if ts is not None:
            if isinstance(ts, datetime):
                meta["timestamp"] = ts.isoformat()
            else:
                meta["timestamp"] = str(ts)

        if event.get("latitude") is not None:
            meta["latitude"] = float(event["latitude"])
        if event.get("longitude") is not None:
            meta["longitude"] = float(event["longitude"])

        return meta

    def add_events(self, events: List[Dict[str, Any]]) -> int:
        """
        Add OSINT events to the vector store.

        Args:
            events: List of OSINT event dicts (from OSINTAggregator or DB).

        Returns:
            Number of events successfully added.
        """
        if not events:
            return 0

        ids = []
        documents = []
        metadatas = []

        for event in events:
            eid = event.get("event_id", str(uuid.uuid4()))
            text = self._event_to_text(event)
            meta = self._event_to_metadata(event)
            ids.append(eid)
            documents.append(text)
            metadatas.append(meta)

        # Try Mistral embeddings first
        embeddings = self._embed_texts(documents)

        try:
            kwargs = dict(ids=ids, documents=documents, metadatas=metadatas)
            if embeddings:
                kwargs["embeddings"] = embeddings
            self.collection.upsert(**kwargs)
            logger.info("Added %d events to vector store", len(ids))
            return len(ids)
        except Exception as e:
            logger.error("Failed to add events to vector store: %s", e)
            return 0

    def add_osint_objects(self, osint_events) -> int:
        """
        Add OSINTEvent dataclass objects (from sources.py) to the store.

        Converts dataclass fields to dicts first.
        """
        dicts = []
        for ev in osint_events:
            d = {}
            if hasattr(ev, "__dataclass_fields__"):
                from dataclasses import asdict
                d = asdict(ev)
            elif isinstance(ev, dict):
                d = ev
            else:
                continue
            dicts.append(d)
        return self.add_events(dicts)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar OSINT events.

        Args:
            query: Search query text.
            k: Number of results to return.
            where: Optional ChromaDB where filter (e.g. {"source": "GDELT"}).

        Returns:
            List of dicts with keys: id, document, metadata, distance.
        """
        # Embed query
        query_embedding = None
        embeddings = self._embed_texts([query])
        if embeddings:
            query_embedding = embeddings[0]

        try:
            kwargs: Dict[str, Any] = {"n_results": min(k, self.collection.count() or k)}
            if query_embedding:
                kwargs["query_embeddings"] = [query_embedding]
            else:
                kwargs["query_texts"] = [query]
            if where:
                kwargs["where"] = where

            results = self.collection.query(**kwargs)
        except Exception as e:
            logger.error("Vector search failed: %s", e)
            return []

        # Flatten results
        output = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"][0]):
                entry = {
                    "id": doc_id,
                    "document": results["documents"][0][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                }
                output.append(entry)

        return output

    def search_by_market(
        self,
        market_name: str,
        market_keywords: Optional[List[str]] = None,
        k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for OSINT events relevant to a specific market.

        Args:
            market_name: The prediction market question/name.
            market_keywords: Additional keywords to include in search.
            k: Number of results.

        Returns:
            List of matching OSINT events.
        """
        query_parts = [market_name]
        if market_keywords:
            query_parts.extend(market_keywords)
        query = " ".join(query_parts)
        return self.search(query, k=k)

    def search_time_window(
        self,
        query: str,
        start_time: str,
        end_time: str,
        k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for events within a time window.

        Note: ChromaDB where filters work on metadata fields.
        Time filtering is done post-query since ChromaDB doesn't support
        range queries on string timestamps natively.
        """
        # Get more results and filter by time
        results = self.search(query, k=k * 3)

        filtered = []
        for r in results:
            ts = r["metadata"].get("timestamp", "")
            if ts and start_time <= ts <= end_time:
                filtered.append(r)

        return filtered[:k]

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def count(self) -> int:
        """Return total number of events in the store."""
        return self.collection.count()

    def clear(self):
        """Delete all events from the collection."""
        self.client.delete_collection(COLLECTION_NAME)
        self._collection = None
        logger.info("Vector store cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Return basic stats about the vector store."""
        count = self.count()
        return {
            "total_events": count,
            "persist_dir": self.persist_dir,
            "collection": COLLECTION_NAME,
            "has_mistral_embed": self.mistral is not None,
        }


if __name__ == "__main__":
    import sys

    print("Testing VectorStore...")

    store = VectorStore()

    # Add some test events
    test_events = [
        {
            "event_id": "test-1",
            "title": "US announces new tariffs on Chinese goods",
            "description": "The United States has announced sweeping tariffs on imports from China, escalating the trade war.",
            "source": "GDELT",
            "category": "ECONOMIC",
            "threat_level": "HIGH",
            "country": "United States",
            "timestamp": "2025-02-15T08:00:00Z",
        },
        {
            "event_id": "test-2",
            "title": "Iran nuclear deal talks collapse",
            "description": "Negotiations on the Iran nuclear agreement have broken down after disagreements on enrichment limits.",
            "source": "GDELT",
            "category": "DIPLOMATIC",
            "threat_level": "CRITICAL",
            "country": "Iran",
            "timestamp": "2025-02-14T14:30:00Z",
        },
        {
            "event_id": "test-3",
            "title": "Hurricane warning issued for Florida coast",
            "description": "National Hurricane Center issues warning as Category 4 storm approaches the Florida coastline.",
            "source": "GDACS",
            "category": "DISASTER",
            "threat_level": "CRITICAL",
            "country": "United States",
            "timestamp": "2025-02-16T06:00:00Z",
        },
        {
            "event_id": "test-4",
            "title": "Cryptocurrency exchange Axiom faces SEC investigation",
            "description": "The SEC has opened a formal investigation into Axiom exchange regarding alleged market manipulation.",
            "source": "RSS",
            "category": "ECONOMIC",
            "threat_level": "HIGH",
            "country": "United States",
            "timestamp": "2025-02-15T12:00:00Z",
        },
        {
            "event_id": "test-5",
            "title": "Russian military exercises near Ukraine border",
            "description": "Russia has begun large-scale military exercises near the Ukrainian border, raising tensions.",
            "source": "ACLED",
            "category": "MILITARY",
            "threat_level": "HIGH",
            "country": "Russia",
            "timestamp": "2025-02-13T20:00:00Z",
        },
    ]

    added = store.add_events(test_events)
    print(f"Added {added} events")
    print(f"Store count: {store.count()}")
    print(f"Stats: {store.get_stats()}")

    # Search
    print("\n--- Search: 'tariffs trade war' ---")
    results = store.search("tariffs trade war", k=3)
    for r in results:
        print(f"  [{r['distance']:.3f}] {r['document'][:80]}...")

    print("\n--- Search: 'hurricane florida' ---")
    results = store.search("hurricane florida", k=3)
    for r in results:
        print(f"  [{r['distance']:.3f}] {r['document'][:80]}...")

    print("\n--- Search by market: 'Will the US announce new tariffs?' ---")
    results = store.search_by_market("Will the US announce new tariffs?", k=3)
    for r in results:
        print(f"  [{r['distance']:.3f}] {r['document'][:80]}...")

    # Cleanup
    store.clear()
    print("\nStore cleared. Test complete.")
