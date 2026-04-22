"""Unit tests for IngestionService.

The actual feed parsers talk to the network, so the tests here focus on
the date-window math + the payload shape the aggregator produces from
mocked HTTP responses.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.ingestion import IngestionService


def test_yesterday_range_is_26_hours_and_utc_aware():
    start, end = IngestionService._get_yesterday_range()
    assert start.tzinfo is not None
    assert end.tzinfo is not None
    # 26-hour window with a small tolerance for clock drift during the test.
    diff = end - start
    assert timedelta(hours=25, minutes=59) < diff < timedelta(hours=26, minutes=1)


@pytest.mark.asyncio
async def test_fetch_all_sources_combines_three_streams():
    """The aggregator concatenates RSS + ArXiv + HN results in that order."""
    with patch.object(IngestionService, "fetch_all_rss", AsyncMock(return_value=[{"title": "rss-1"}])), \
         patch.object(IngestionService, "fetch_arxiv_api", AsyncMock(return_value=[{"title": "arxiv-1"}])), \
         patch.object(IngestionService, "fetch_hn_api", AsyncMock(return_value=[{"title": "hn-1"}])):
        out = await IngestionService.fetch_all_sources()

    assert [a["title"] for a in out] == ["rss-1", "arxiv-1", "hn-1"]


@pytest.mark.asyncio
async def test_fetch_all_sources_survives_individual_crawler_failures():
    """If one crawler raises, the others still contribute their articles."""
    boom = AsyncMock(side_effect=RuntimeError("rss exploded"))
    with patch.object(IngestionService, "fetch_all_rss", boom), \
         patch.object(IngestionService, "fetch_arxiv_api", AsyncMock(return_value=[{"title": "arxiv-ok"}])), \
         patch.object(IngestionService, "fetch_hn_api", AsyncMock(return_value=[{"title": "hn-ok"}])):
        out = await IngestionService.fetch_all_sources()

    titles = [a["title"] for a in out]
    assert "arxiv-ok" in titles
    assert "hn-ok" in titles
    assert "rss-1" not in titles


@pytest.mark.asyncio
async def test_hn_item_shape_includes_required_fields():
    """Individual HN worker returns the canonical article shape for successful stories."""
    import httpx

    now = datetime.now(timezone.utc)

    class FakeResp:
        status_code = 200

        @staticmethod
        def json():
            return {
                "type": "story",
                "title": "Sample",
                "url": "https://example.com/x",
                "text": "body",
                "by": "aakash",
                "time": int(now.timestamp()),
            }

    class FakeClient:
        async def get(self, _url):
            return FakeResp()

    import asyncio
    sem = asyncio.Semaphore(1)
    start, end = IngestionService._get_yesterday_range()

    out = await IngestionService._fetch_hn_item(FakeClient(), 1, sem, start, end)
    # Required keys for downstream MERGE.
    assert set(out.keys()) >= {
        "source_name",
        "title",
        "url",
        "summary",
        "published_at",
    }
    assert out["source_name"] == "Hacker News"
