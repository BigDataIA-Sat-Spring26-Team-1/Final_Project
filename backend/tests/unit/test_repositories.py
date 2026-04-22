"""Repository-layer tests with a mocked Snowflake cursor.

The goal is to lock down the SQL contracts these helpers emit — if someone
renames a column or flips the MERGE ON clause the tests fail loudly.
"""
import json
from unittest.mock import MagicMock

from app.core.schemas import UserPersonaUpdate
from app.repository.article import ArticleRepository
from app.repository.persona import PersonaRepository


def _mock_conn():
    cur = MagicMock()
    cur.description = [("ID",)]
    cur.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


# ---- ArticleRepository ---------------------------------------------------

def test_upsert_raw_articles_empty_list_is_a_noop():
    conn, cur = _mock_conn()
    saved = ArticleRepository.upsert_raw_articles(conn, [])
    assert saved == 0
    cur.execute.assert_not_called()


def test_upsert_raw_articles_chunks_and_uses_merge_on_url():
    conn, cur = _mock_conn()

    # 75 articles -> one chunk of 50 + one of 25.
    articles = [
        {
            "source_name": "S",
            "source_url": "https://s.com",
            "title": f"t{i}",
            "url": f"https://s.com/{i}",
            "summary": "",
            "published_at": "2026-01-01T00:00:00+00:00",
            "author": "a",
            "tags": [],
        }
        for i in range(75)
    ]
    saved = ArticleRepository.upsert_raw_articles(conn, articles)
    assert saved == 75
    assert cur.execute.call_count == 2

    # MERGE statement must key on URL, not id — that's the dedup contract.
    first_sql = cur.execute.call_args_list[0].args[0]
    assert "MERGE INTO articles_raw" in first_sql
    assert "ON TARGET.url = SOURCE.url" in first_sql


def test_get_unclustered_articles_selects_null_cluster_ids():
    conn, cur = _mock_conn()
    cur.description = [("id",), ("title",), ("url",), ("summary",), ("source_name",), ("published_at",)]
    cur.fetchall.return_value = [("id-1", "t", "u", "s", "src", None)]

    out = ArticleRepository.get_unclustered_articles(conn, limit=5)
    assert out == [{
        "id": "id-1",
        "title": "t",
        "url": "u",
        "summary": "s",
        "source_name": "src",
        "published_at": None,
    }]
    sql = cur.execute.call_args.args[0]
    assert "cluster_id IS NULL" in sql


# ---- PersonaRepository ---------------------------------------------------

def test_upsert_persona_merges_on_user_id():
    conn, cur = _mock_conn()
    data = UserPersonaUpdate(
        user_id="u-1",
        linkedin_url=None,
        job_title="eng",
        seniority="mid",
        persona_archetype="DATA_STRATEGIST",
        bio_summary="bio",
        explicit_category_weights={"llms": 0.5},
    )
    PersonaRepository.upsert_persona(conn, data)
    sql = cur.execute.call_args.args[0]
    assert "MERGE INTO user_personas" in sql
    assert "ON target.user_id = source.user_id" in sql


def test_get_persona_parses_variant_json():
    conn, cur = _mock_conn()
    # Snowflake returns the VARIANT columns as JSON strings.
    cur.fetchone.return_value = (
        "eng",
        "mid",
        "DATA_STRATEGIST",
        "bio",
        json.dumps({"llms": 0.5}),
        json.dumps({"llms": 0.1}),
    )
    out = PersonaRepository.get_persona(conn, "u-1")
    assert out["persona_archetype"] == "DATA_STRATEGIST"
    assert out["explicit_category_weights"] == {"llms": 0.5}
    assert out["behavioral_category_weights"] == {"llms": 0.1}


def test_get_persona_returns_none_when_row_missing():
    conn, cur = _mock_conn()
    cur.fetchone.return_value = None
    assert PersonaRepository.get_persona(conn, "ghost") is None
