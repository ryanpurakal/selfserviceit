"""Semantic search and confidence scoring helpers."""

from __future__ import annotations

import logging
import math
from typing import Any

from embeddings import get_backend

logger = logging.getLogger(__name__)


def _distance_to_relevance(distance: float) -> float:
    """Convert a Chroma distance into a 0-1 relevance score.

    Chroma's default metric is squared L2 on normalized vectors, which is
    bounded in [0, 4]. We map that to a similarity in [0, 1] so it reads
    naturally in the UI as "relevance".
    """

    if distance is None or math.isnan(distance):
        return 0.0
    similarity = max(0.0, 1.0 - (distance / 2.0))
    return min(1.0, similarity)


def semantic_search(query: str, collection, top_k: int = 5) -> list[dict[str, Any]]:
    """Run a semantic search and return enriched chunk dicts."""

    if collection.count() == 0:
        return []

    backend = get_backend()
    [vector] = backend.embed([query])

    raw = collection.query(
        query_embeddings=[vector],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    docs = raw.get("documents", [[]])[0]
    metas = raw.get("metadatas", [[]])[0]
    dists = raw.get("distances", [[]])[0]

    results: list[dict[str, Any]] = []
    for text, meta, dist in zip(docs, metas, dists):
        results.append(
            {
                "text": text,
                "source": meta.get("source", "unknown"),
                "title": meta.get("title", meta.get("source", "")),
                "chunk_id": meta.get("chunk_id", ""),
                "score": _distance_to_relevance(dist),
                "distance": dist,
            }
        )
    return results


def calculate_confidence(results: list[dict[str, Any]]) -> float:
    """Combine top relevance scores into an overall answer confidence.

    Heuristic: weight the top hit heavily, but reward consistent agreement
    across the next two results. Returned value is in [0, 1].
    """

    if not results:
        return 0.0

    top = results[0]["score"]
    runner_up = results[1]["score"] if len(results) > 1 else top * 0.7
    third = results[2]["score"] if len(results) > 2 else runner_up * 0.7

    confidence = (top * 0.6) + (runner_up * 0.25) + (third * 0.15)
    return round(min(1.0, max(0.0, confidence)), 3)


def get_related_topics(
    query: str,
    collection,
    *,
    exclude_sources: set[str] | None = None,
    limit: int = 4,
) -> list[str]:
    """Return human-readable related topic titles based on the query.

    Pulls a wider semantic search and dedupes by source title so we surface
    different documents (not five chunks from the same VPN guide).
    """

    if collection.count() == 0:
        return []

    excluded = exclude_sources or set()
    results = semantic_search(query, collection, top_k=10)

    seen: set[str] = set()
    topics: list[str] = []
    for r in results:
        title = r.get("title") or r.get("source")
        if not title or title in seen:
            continue
        if r.get("source") in excluded and len(excluded) < collection.count():
            # Skip the source we already cited unless it's the only one.
            continue
        seen.add(title)
        topics.append(title)
        if len(topics) >= limit:
            break

    return topics
