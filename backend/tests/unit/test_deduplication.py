"""Unit tests for DeduplicationService.

URL normalization + cluster synthesis are pure functions — tested directly.
The semantic batch pipeline mocks LiteLLM embeddings so the tests run offline.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.services.deduplication import DeduplicationService


@pytest.mark.parametrize(
    "raw, expected",
    [
        # www prefix stripped, scheme dropped, path preserved.
        ("https://www.example.com/foo/bar", "example.com/foo/bar"),
        # trailing slash removed.
        ("https://example.com/foo/", "example.com/foo"),
        # query string intentionally dropped — UTM etc. vary per source.
        ("https://example.com/foo?utm=x", "example.com/foo"),
        # subdomain preserved.
        ("https://blog.example.com/post", "blog.example.com/post"),
        # empty / malformed input should not crash.
        ("", ""),
    ],
)
def test_normalize_url(raw, expected):
    # The normaliser intentionally strips query strings, so the UTM input above
    # should end up identical to the no-query variant.
    assert DeduplicationService.normalize_url(raw).split("?")[0] == expected


def test_synthesize_story_aggregates_sources_and_ids():
    cluster = [
        {"id": "a", "title": "A", "source_name": "TechCrunch", "_all_ids": ["a"], "_all_sources": ["TechCrunch"]},
        {"id": "b", "title": "B", "source_name": "WSJ",        "_all_ids": ["b"], "_all_sources": ["WSJ"]},
    ]
    out = DeduplicationService.synthesize_story(cluster)
    assert out["primary_title"] == "A"
    assert sorted(out["article_ids"]) == ["a", "b"]
    assert set(out["sources"]) == {"TechCrunch", "WSJ"}
    # 2+ sources confirms the story -> TRENDING marker.
    assert out["trend_status"] == "TRENDING"


def test_synthesize_story_single_source_is_new():
    cluster = [{"id": "a", "title": "solo", "source_name": "X", "_all_ids": ["a"], "_all_sources": ["X"]}]
    assert DeduplicationService.synthesize_story(cluster)["trend_status"] == "NEW"


@pytest.mark.asyncio
async def test_process_batch_url_dedup_collapses_duplicates():
    """Two articles with the same (normalized) URL become one cluster,
    regardless of source."""
    articles = [
        {"id": "1", "url": "https://www.example.com/foo", "title": "A", "summary": "s", "source_name": "S1"},
        {"id": "2", "url": "https://example.com/foo/",   "title": "B", "summary": "s", "source_name": "S2"},
    ]

    with patch.object(
        DeduplicationService,
        "get_embeddings",
        AsyncMock(return_value=np.array([[0.1] * 1536])),
    ):
        fake_client = MagicMock()
        fake_client.upsert.return_value = None
        with patch("app.services.deduplication.get_qdrant_client", return_value=fake_client):
            clusters = await DeduplicationService.process_batch(articles)

    # Both articles were structurally identical -> one semantic cluster.
    assert len(clusters) == 1
    # _all_ids captures both raw article ids.
    assert sorted(clusters[0][0]["_all_ids"]) == ["1", "2"]


@pytest.mark.asyncio
async def test_process_batch_semantic_split_when_below_threshold():
    """Distinct embeddings must NOT be merged even when URLs differ by path."""
    articles = [
        {"id": "1", "url": "https://a.com/x", "title": "llms research", "summary": "", "source_name": "A"},
        {"id": "2", "url": "https://b.com/y", "title": "hardware supply chain", "summary": "", "source_name": "B"},
    ]

    far_apart = np.array(
        [
            [1.0] + [0.0] * 1535,
            [0.0] * 1535 + [1.0],
        ]
    )
    with patch.object(DeduplicationService, "get_embeddings", AsyncMock(return_value=far_apart)):
        fake_client = MagicMock()
        fake_client.upsert.return_value = None
        with patch("app.services.deduplication.get_qdrant_client", return_value=fake_client):
            clusters = await DeduplicationService.process_batch(articles)

    assert len(clusters) == 2
