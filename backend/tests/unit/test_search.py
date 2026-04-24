"""Unit tests for the personalized retrieval service.

Covers two behaviours:
    * explicit × 0.8 + behavioral × 0.2 blend drives the semantic query
    * empty-persona fallback still returns a non-empty query so Qdrant
      doesn't blow up on an empty string
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.services.search import SearchService


def _fake_conn(explicit, behavioral):
    """Build a conn whose cursor returns the supplied persona weights."""
    cur = MagicMock()
    cur.fetchone.return_value = (
        json.dumps(explicit) if explicit is not None else None,
        json.dumps(behavioral) if behavioral is not None else None,
    )
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


@pytest.mark.asyncio
async def test_blended_query_uses_top_categories_from_weighted_sum():
    # explicit dominated by LLMs; behavioral dominated by security.
    # With an 80/20 blend LLMs still wins, but security survives the floor.
    explicit = {"llms": 0.9, "security": 0.1}
    behavioral = {"security": 1.0, "llms": 0.0}
    conn, _ = _fake_conn(explicit, behavioral)

    fake_response = MagicMock()
    fake_response.points = []

    with patch(
        "app.services.search.DeduplicationService.get_embeddings",
        AsyncMock(return_value=np.array([[0.0] * 1536])),
    ) as emb, patch("app.services.search.get_qdrant_client") as qd:
        qd.return_value.query_points.return_value = fake_response
        out = await SearchService.get_personalized_recommendations("u1", 5, conn)

    assert out["results"] == []
    # Blended weight: llms=0.72, security=0.28 -> query starts with "llms security"
    passed_query = emb.call_args.args[0][0]
    assert passed_query.split()[0] == "llms"
    assert "security" in passed_query


@pytest.mark.asyncio
async def test_empty_persona_falls_back_to_generic_query():
    """When both weight blobs are empty the query must still be non-empty so
    the downstream embedding call doesn't get a zero-length string."""
    conn, _ = _fake_conn({}, {})

    fake_response = MagicMock()
    fake_response.points = []

    with patch(
        "app.services.search.DeduplicationService.get_embeddings",
        AsyncMock(return_value=np.array([[0.0] * 1536])),
    ) as emb, patch("app.services.search.get_qdrant_client") as qd:
        qd.return_value.query_points.return_value = fake_response
        out = await SearchService.get_personalized_recommendations("u1", 5, conn)

    passed_query = emb.call_args.args[0][0]
    assert passed_query
    assert len(passed_query) > 5
    assert out["semantic_basis"] == passed_query


@pytest.mark.asyncio
async def test_returns_none_when_user_missing():
    cur = MagicMock()
    cur.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cur

    out = await SearchService.get_personalized_recommendations("ghost", 5, conn)
    assert out is None


@pytest.mark.asyncio
async def test_results_pass_through_qdrant_hits():
    conn, _ = _fake_conn({"llms": 1.0}, {})

    hit = MagicMock()
    hit.id = "cluster-1"
    hit.score = 0.81234
    hit.payload = {"title": "Headline", "sources": ["S1"], "cluster_size": 3}

    fake_response = MagicMock()
    fake_response.points = [hit]

    with patch(
        "app.services.search.DeduplicationService.get_embeddings",
        AsyncMock(return_value=np.array([[0.0] * 1536])),
    ), patch("app.services.search.get_qdrant_client") as qd:
        qd.return_value.query_points.return_value = fake_response
        out = await SearchService.get_personalized_recommendations("u1", 5, conn)

    # `source_name`, `trend_status`, and `categories` were added to the
    # Qdrant pass-through so like/dislike feedback has per-article taxonomy
    # weights to multiply against. Missing keys default to empty.
    assert out["results"][0] == {
        "cluster_id": "cluster-1",
        "score": 0.8123,
        "title": "Headline",
        "url": "",
        "summary": "",
        "sources": ["S1"],
        "source_name": "",
        "cluster_size": 3,
        "trend_status": None,
        "categories": {},
    }
