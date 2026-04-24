from __future__ import annotations
from collections import Counter
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional
from app.core.logging_conf import get_logger
from app.db.snowflake import get_db_connection

logger = get_logger("app.services.keyword_velocity")

_WHITELIST = {"AI", "ML", "RAG", "LLM", "LLMs", "Claude", "OpenAI", "NVIDIA", "GPT", "Google"}

_ENTITY_LABELS = {"ORG", "PRODUCT", "WORK_OF_ART", "PERSON"}

@lru_cache(maxsize=1)
def _load_nlp():

    import spacy  

    try:
        return spacy.load("en_core_web_sm")
    except OSError as exc:
        raise RuntimeError(
            "spaCy model 'en_core_web_sm' not installed. Run: "
            "python -m spacy download en_core_web_sm"
        ) from exc


def _extract_entities(titles: List[str]) -> List[str]:
    nlp = _load_nlp()
    counts: Counter = Counter()
    for doc in nlp.pipe(titles, batch_size=50):
        seen_in_doc: set = set()
        for ent in doc.ents:
            if ent.label_ not in _ENTITY_LABELS:
                continue
            text = ent.text.strip()
            if text.lower().startswith("the "):
                text = text[4:]
            if len(text) < 2:
                continue
            seen_in_doc.add(text)
        counts.update(seen_in_doc)

    return [e for e, n in counts.items() if n >= 3]

def _count_entities(titles: List[str], entities: List[str]) -> Counter:
    counts: Counter = Counter()
    for title in titles:
        for ent in entities:
            if ent in title:
                counts[ent] += 1
    return counts

def _fetch_titles(
    target_date: Optional[str], window_hours: int = 24
) -> tuple[List[str], List[str]]:
    target = date.fromisoformat(target_date) if target_date else date.today()
    prev_date = target - timedelta(days=1)

    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        cur = db.cursor()
        cur.execute(
            "SELECT title FROM articles_raw WHERE CAST(fetched_at AS DATE) = %s",
            (target.isoformat(),),
        )
        current = [r[0] for r in cur.fetchall() if r[0]]

        cur.execute(
            "SELECT title FROM articles_raw WHERE CAST(fetched_at AS DATE) = %s",
            (prev_date.isoformat(),),
        )
        previous = [r[0] for r in cur.fetchall() if r[0]]
        logger.info(
            "keyword_velocity titles loaded",
            target=target.isoformat(),
            previous=prev_date.isoformat(),
            current_count=len(current),
            previous_count=len(previous),
        )
        return current, previous
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

def _status_for(velocity_pct: float) -> str:
    if velocity_pct > 50:
        return "SURGING"
    if velocity_pct > -20:
        return "STABLE"
    return "DECLINING"

def compute_keyword_velocity(
    target_date: Optional[str] = None, top_n: int = 30, min_mentions: int = 3
) -> Dict[str, Any]:
    """Return the velocity report for B2B SEO dashboards.

    Response shape::

        {
          "target_date": "2026-04-22",
          "previous_date": "2026-04-21",
          "total": 27,
          "results": [
            {"entity": "OpenAI", "current": 9, "previous": 4,
             "total_mentions": 13, "velocity_pct": 125.0, "status": "SURGING"},
            ...
          ]
        }
    """
    current_titles, previous_titles = _fetch_titles(target_date)
    entities = _extract_entities(current_titles + previous_titles)
    entities = list({*entities, *_WHITELIST})
    current_counts = _count_entities(current_titles, entities)
    previous_counts = _count_entities(previous_titles, entities)

    report: List[Dict[str, Any]] = []
    for ent in entities:
        curr = current_counts.get(ent, 0)
        prev = previous_counts.get(ent, 0)
        total = curr + prev
        if total < min_mentions:
            continue
        base = prev if prev > 0 else 1
        velocity = ((curr - prev) / base) * 100.0
        report.append(
            {
                "entity": ent,
                "current": curr,
                "previous": prev,
                "total_mentions": total,
                "velocity_pct": round(velocity, 1),
                "status": _status_for(velocity),
            }
        )

    report.sort(key=lambda r: (r["total_mentions"], r["current"]), reverse=True)
    top = report[:top_n]
    target = (
        date.fromisoformat(target_date) if target_date else date.today()
    )
    return {
        "target_date": target.isoformat(),
        "previous_date": (target - timedelta(days=1)).isoformat(),
        "total": len(top),
        "results": top,
    }