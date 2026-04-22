"""Unit tests for POST /personas/feedback behavioral delta logic.

The route is simple data plumbing, so the tests focus on the invariants that
the spec calls out explicitly:

    like     -> +0.15 * article_weight
    dislike  -> -0.15 * article_weight
    skip     -> -0.05 * article_weight

All weights are clamped to [0, 1] and anything below 0.05 is pruned.
"""
import json
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from app.api.personas import record_article_feedback
from app.core.limiter import limiter
from app.core.schemas import ArticleFeedbackRequest, FeedbackType


@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    """slowapi demands a real Request in args[0]; unit tests don't need the
    rate-limit check so flipping the global switch off is cleaner than
    building a fake starlette scope."""
    limiter.enabled = False
    yield
    limiter.enabled = True


def _fake_request() -> Request:
    """Minimal Request object just sufficient to satisfy type checks."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/personas/feedback",
        "headers": [],
    }
    return Request(scope)


class _FakeCursor:
    """Minimal stand-in that lets the endpoint call cursor.execute + fetchone."""

    def __init__(self, initial_weights):
        self._initial = initial_weights
        self.executed = []

    def execute(self, sql, params=()):
        self.executed.append((sql.strip().split()[0].upper(), sql, params))

    def fetchone(self):
        return (json.dumps(self._initial),) if self._initial is not None else None


class _FakeConn:
    def __init__(self, initial_weights):
        self._cur = _FakeCursor(initial_weights)

    def cursor(self):
        return self._cur

    def commit(self):
        self._cur.executed.append(("COMMIT", "", ()))


@pytest.mark.asyncio
async def test_like_increases_weights_proportionally():
    conn = _FakeConn({"llms": 0.5})
    payload = ArticleFeedbackRequest(
        user_id="u1",
        article_categories={"llms": 1.0, "security": 0.4},
        feedback=FeedbackType.like,
    )

    out = await record_article_feedback(_fake_request(), payload, conn)

    # 0.5 + 0.15 * 1.0 = 0.65; 0 + 0.15 * 0.4 = 0.06 (passes the 0.05 floor)
    assert out.updated_categories["llms"] == pytest.approx(0.65)
    assert out.updated_categories["security"] == pytest.approx(0.06)


@pytest.mark.asyncio
async def test_dislike_can_prune_categories_below_noise_floor():
    conn = _FakeConn({"llms": 0.08})
    payload = ArticleFeedbackRequest(
        user_id="u1",
        article_categories={"llms": 1.0},
        feedback=FeedbackType.dislike,
    )

    out = await record_article_feedback(_fake_request(), payload, conn)

    # 0.08 + (-0.15 * 1.0) = -0.07 -> clamp to 0 -> prune because < 0.05
    assert "llms" not in out.updated_categories


@pytest.mark.asyncio
async def test_skip_applies_smaller_penalty_than_dislike():
    conn = _FakeConn({"llms": 0.6})
    payload = ArticleFeedbackRequest(
        user_id="u1",
        article_categories={"llms": 1.0},
        feedback=FeedbackType.skip,
    )

    out = await record_article_feedback(_fake_request(), payload, conn)

    # 0.6 + (-0.05 * 1.0) = 0.55
    assert out.updated_categories["llms"] == pytest.approx(0.55)


@pytest.mark.asyncio
async def test_404_when_persona_missing():
    from fastapi import HTTPException

    conn = _FakeConn(None)
    payload = ArticleFeedbackRequest(
        user_id="nobody",
        article_categories={"llms": 0.5},
        feedback=FeedbackType.like,
    )

    with pytest.raises(HTTPException) as exc:
        await record_article_feedback(_fake_request(), payload, conn)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_weights_clamp_to_one():
    conn = _FakeConn({"llms": 0.95})
    payload = ArticleFeedbackRequest(
        user_id="u1",
        article_categories={"llms": 1.0},
        feedback=FeedbackType.like,
    )

    out = await record_article_feedback(_fake_request(), payload, conn)

    # 0.95 + 0.15 = 1.10 -> clamp to 1.0
    assert out.updated_categories["llms"] == 1.0
