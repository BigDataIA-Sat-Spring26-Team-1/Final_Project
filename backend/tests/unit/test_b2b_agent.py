"""Unit tests for the B2B research agent.

Focused on the two pieces of pure logic:
    * opportunity scoring boundaries (HIDDEN GEM / ACT NOW / MONITOR / SKIP)
    * report generation renders a non-empty Markdown brief with a mocked LLM
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.services.b2b_agent import extract_intelligence, generate_report


@pytest.mark.asyncio
async def test_opportunity_scoring_tiers_boundaries():
    """The four urgency bands land on the expected inputs.

    Crafted article records stay on the side of each boundary with deliberate
    cluster sizes so regressions in the scoring math are obvious.
    """
    # Weight recap (see extract_intelligence):
    #   relevance        = score × 40                     (caps at 40)
    #   velocity         = min(cluster_size/5, 1) × 30    (caps at 30)
    #   competition_gap  = (1 - min(cluster_size/10, 1)) × 30
    #
    # HIDDEN GEM >= 85: size=5, score=1.0  -> 40 + 30 + 15 = 85
    # ACT NOW    >= 70: size=10, score=1.0 -> 40 + 30 +  0 = 70
    # MONITOR    >= 50: size=10, score=0.8 -> 32 + 30 +  0 = 62
    # SKIP       < 50:  size=10, score=0.2 -> 8  + 30 +  0 = 38
    fake_recs = {
        "semantic_basis": "llms ai_agents",
        "results": [
            {"title": "breakout", "score": 1.0, "cluster_size": 5},
            {"title": "hot",      "score": 1.0, "cluster_size": 10},
            {"title": "watch",    "score": 0.8, "cluster_size": 10},
            {"title": "skip",     "score": 0.2, "cluster_size": 10},
        ],
    }

    # The service drives the db generator to completion — yield once with a
    # dummy connection, then StopIteration on the cleanup pass.
    def _fake_conn_gen():
        yield object()

    with patch("app.services.b2b_agent.get_db_connection", _fake_conn_gen):
        with patch(
            "app.services.b2b_agent.SearchService.get_personalized_recommendations",
            AsyncMock(return_value=fake_recs),
        ):
            state = await extract_intelligence({"user_id": "tenant-1"})

    titles_to_tier = {a["title"]: a["urgency_tier"] for a in state["retrieved_articles"]}
    assert titles_to_tier == {
        "breakout": "HIDDEN GEM",
        "hot": "ACT NOW",
        "watch": "MONITOR",
        "skip": "SKIP",
    }
    # And they come back ordered by opportunity_score desc.
    scores = [a["opportunity_score"] for a in state["retrieved_articles"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_generate_report_empty_when_no_articles():
    """The agent must still return a valid Markdown stub when retrieval is empty,
    otherwise downstream persistence crashes with NOT NULL on brief_content."""
    out = await generate_report({"user_id": "tenant-1", "retrieved_articles": []})
    assert out["status"] == "EMPTY_RESULT"
    assert out["generated_content"].startswith("# ")


@pytest.mark.asyncio
async def test_generate_report_calls_llm_with_scored_intel():
    """The LLM prompt must include the scored intel lines so the agent can't
    hallucinate a report on unrelated data."""
    articles = [
        {"title": "LangGraph gains traction", "opportunity_score": 92.5, "urgency_tier": "HIDDEN GEM", "cluster_size": 2},
        {"title": "New auth framework",        "opportunity_score": 55.0, "urgency_tier": "MONITOR",    "cluster_size": 4},
    ]
    with patch(
        "app.services.b2b_agent.BaseAgentService.call_llm",
        AsyncMock(return_value="# Executive Intelligence Briefing\n\n..."),
    ) as llm:
        result = await generate_report({"user_id": "tenant-1", "retrieved_articles": articles})

    assert result["status"] == "SUCCESS"
    assert "Executive Intelligence Briefing" in result["generated_content"]
    prompt = llm.call_args.kwargs["messages"][0]["content"]
    assert "LangGraph gains traction" in prompt
    assert "HIDDEN GEM" in prompt
