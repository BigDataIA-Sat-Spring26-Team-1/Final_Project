"""B2B Strategic Brief LangGraph.

Pipeline:
  1. ``initialize_state``  — hydrate the company profile so every node has
     concrete context (industry, competitors, content pillars, …).
  2. ``extract_intelligence`` — score the top N relevant article clusters
     with the 3-signal opportunity algorithm (Relevance / Velocity /
     Competition-Gap) and tag each with an urgency tier.
  3. ``build_strategic_brief`` — ask the LLM for a `StrategicBrief`
     Pydantic-structured payload (blue-ocean angle, editorial titles,
     primary keywords, ordered content sections, internal-linking
     strategy). Keyword velocity is cross-joined from the SpaCy NER
     pipeline; reference sources come straight from `articles_raw`
     (no external search service required).
  4. ``render_markdown`` — emit a human-readable executive summary for
     back-compat with the old Markdown consumers (email / Markdown view).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langgraph.graph import END

from app.core.logging_conf import get_logger
from app.core.schemas import (
    BriefKeyword,
    BriefReference,
    StrategicBrief,
    StrategicBriefEnvelope,
)
from app.db.snowflake import get_db_connection
from app.services.agent_base import (
    AgentState,
    BaseAgentService,
    create_base_graph,
    track_node_latency,
)
from app.services.search import SearchService

logger = get_logger("app.services.b2b_agent")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_company_profile(db, company_id: str) -> Optional[Dict[str, Any]]:
    cur = db.cursor()
    cur.execute(
        """
        SELECT id, name, domain, industry, description, company_size,
               target_audience, key_products, content_pillars, competitors,
               tone_of_voice, content_affinity_weights
        FROM companies
        WHERE id = %s
        """,
        (company_id,),
    )
    row = cur.fetchone()
    if not row:
        return None

    raw_affinity = row[11]
    affinity: Optional[Dict[str, float]] = None
    if raw_affinity is not None:
        if isinstance(raw_affinity, dict):
            affinity = raw_affinity
        elif isinstance(raw_affinity, str) and raw_affinity.strip():
            try:
                import json as _json
                affinity = _json.loads(raw_affinity)
            except _json.JSONDecodeError:
                affinity = None

    return {
        "id": row[0],
        "name": row[1],
        "domain": row[2],
        "industry": row[3],
        "description": row[4],
        "company_size": row[5],
        "target_audience": row[6],
        "key_products": row[7],
        "content_pillars": row[8],
        "competitors": row[9],
        "tone_of_voice": row[10],
        "content_affinity_weights": affinity,
    }


def _score_article(article: Dict[str, Any]) -> Dict[str, Any]:
    """3-signal opportunity score (0–100) + urgency tier."""
    relevance = float(article.get("score", 0.0)) * 40.0
    cluster_size = int(article.get("cluster_size", 1) or 1)
    velocity = min(cluster_size / 5.0, 1.0) * 30.0
    competition_gap = (1.0 - min(cluster_size / 10.0, 1.0)) * 30.0
    total = round(relevance + velocity + competition_gap, 2)

    # Keep the legacy "HIDDEN GEM" / "ACT NOW" spacing — it's what existing
    # content_briefs rows hold and what tests/unit/test_b2b_agent.py asserts
    # against. Underscored variants are produced from these at the frontend
    # (see StrategicBriefCard.urgencyClass).
    if total >= 85:
        urgency = "HIDDEN GEM"
    elif total >= 70:
        urgency = "ACT NOW"
    elif total >= 50:
        urgency = "MONITOR"
    else:
        urgency = "SKIP"

    return {**article, "opportunity_score": total, "urgency_tier": urgency}


def _reference_sources_for_cluster(db, cluster_ids: List[str], limit: int = 5) -> List[BriefReference]:
    """Pull real article URLs out of ``articles_raw`` for the given clusters."""
    if not cluster_ids:
        return []

    placeholders = ",".join(["%s"] * len(cluster_ids))
    cur = db.cursor()
    cur.execute(
        f"""
        SELECT title, url, source_name
        FROM (
            SELECT title, url, source_name, cluster_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY cluster_id
                       ORDER BY published_at DESC NULLS LAST, fetched_at DESC
                   ) AS rn
            FROM articles_raw
            WHERE cluster_id IN ({placeholders})
              AND url IS NOT NULL AND url <> ''
        )
        WHERE rn <= 2
        LIMIT %s
        """,
        (*cluster_ids, limit),
    )
    refs: List[BriefReference] = []
    for r in cur.fetchall():
        refs.append(
            BriefReference(
                title=(r[0] or "Untitled")[:255],
                url=r[1],
                source_name=r[2],
            )
        )
    return refs


def _attach_velocity(keywords: List[BriefKeyword]) -> List[BriefKeyword]:
    """Cross-join LLM-proposed keywords with the live SpaCy velocity report."""
    try:
        from app.services.keyword_velocity import compute_keyword_velocity

        report = compute_keyword_velocity(top_n=50, min_mentions=1)
        idx = {r["entity"].lower(): r for r in report.get("results", [])}
    except Exception as exc:  # noqa: BLE001 — velocity is a best-effort attach
        logger.warning("Velocity attach skipped", error=str(exc))
        return keywords

    enriched: List[BriefKeyword] = []
    for kw in keywords:
        hit = idx.get(kw.keyword.lower())
        if hit:
            enriched.append(
                BriefKeyword(
                    keyword=kw.keyword,
                    monthly_volume=kw.monthly_volume,
                    velocity_pct=float(hit.get("velocity_pct", 0.0)),
                    status=hit.get("status"),
                )
            )
        else:
            enriched.append(kw)
    return enriched


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


@track_node_latency
async def initialize_state(state: AgentState) -> Dict[str, Any]:
    company_id = state.get("user_id")
    logger.info("Initializing B2B Agent State", company_id=company_id)

    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        company = _load_company_profile(db, company_id)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    if not company:
        return {
            "status": "COMPANY_NOT_FOUND",
            "metadata": {"company": None},
        }

    return {
        "status": "INITIALIZED",
        "metadata": {"company": company},
    }


@track_node_latency
async def extract_intelligence(state: AgentState) -> Dict[str, Any]:
    """Score the top-10 candidate clusters for this company."""
    company_id = state.get("user_id")
    if state.get("status") == "COMPANY_NOT_FOUND":
        return {"retrieved_articles": [], "status": "COMPANY_NOT_FOUND"}

    brief_date = state.get("brief_date")
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        recs = await SearchService.get_personalized_recommendations(
            company_id, limit=10, db=db, edition_date=brief_date
        )
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    if not recs:
        return {"status": "NO_ARTICLES_FOUND", "retrieved_articles": []}

    articles = recs.get("results", [])
    scored = [_score_article(a) for a in articles]
    scored.sort(key=lambda x: x["opportunity_score"], reverse=True)

    return {
        "retrieved_articles": scored,
        "search_query": recs.get("semantic_basis", ""),
        "status": "RESEARCH_COMPLETE",
    }


@track_node_latency
async def build_strategic_brief(state: AgentState) -> Dict[str, Any]:
    """Ask the LLM for a structured StrategicBrief anchored on the top opportunity.

    When a ``brief_date`` is carried on the state (historical generation for
    demo / backfill), we rotate which top-N article anchors the brief based on
    the date — today's brief anchors on #1, yesterday on #2, day-before on #3,
    etc. Each day's structured output is therefore genuinely different even
    when the underlying article pool is stable.
    """
    if state.get("status") in ("COMPANY_NOT_FOUND", "NO_ARTICLES_FOUND"):
        return {"status": state["status"]}

    articles: List[Dict[str, Any]] = state.get("retrieved_articles") or []
    if not articles:
        return {"status": "NO_ARTICLES_FOUND"}

    # Pick which ranked article becomes the brief anchor. Rotation is driven
    # by (today - brief_date).days so each historical day looks different.
    from datetime import date as _date, datetime as _dt

    brief_date_str = state.get("brief_date") or _date.today().isoformat()
    try:
        brief_date_obj = _dt.fromisoformat(brief_date_str).date()
    except ValueError:
        brief_date_obj = _date.today()
    date_offset = max(0, (_date.today() - brief_date_obj).days)
    anchor_index = min(date_offset, len(articles) - 1)
    top = articles[anchor_index]

    company = (state.get("metadata") or {}).get("company") or {}
    affinity: Optional[Dict[str, float]] = company.get("content_affinity_weights")

    signal_lines = []
    for a in articles[:8]:
        signal_lines.append(
            f"- [{a.get('urgency_tier', 'MONITOR')}] {a.get('title')} "
            f"(score={a.get('opportunity_score', 0)}, "
            f"coverage={a.get('cluster_size', 1)} sources)"
        )

    profile_block = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}"
        for k, v in company.items()
        if v and k not in ("id", "content_affinity_weights")
    )

    # Build the affinity-injection block + dominant/zero category lists.
    # When no vector is stored we skip the hard constraint entirely (new
    # tenants whose extraction failed still get a reasonable generic
    # brief). Validated in Prototyping/SEO_Personalized/prototype.py —
    # cross-tenant brief cosine drops ~8pts with this injection at
    # temperature=0.4.
    if affinity:
        sorted_w = sorted(affinity.items(), key=lambda x: -x[1])
        dominant = [k for k, v in sorted_w[:3] if v >= 0.10]
        zero = [k for k, v in affinity.items() if v < 0.05]
        affinity_block = "\n".join(
            f"  {k:<24} {v:.2f}" for k, v in sorted_w
        )
        affinity_section = f"""
=== TENANT CONTENT-AFFINITY (10-dim taxonomy, sums to ~1.0) ===
{affinity_block}
DOMINANT CATEGORIES: {', '.join(dominant) or '(none)'}
ZERO-WEIGHT CATEGORIES (never mention): {', '.join(zero) or '(none)'}

=== HARD CONSTRAINTS ===
- Every editorial_title MUST reference at least one DOMINANT category
  using the tenant's own vocabulary, NOT the raw taxonomy token.
- At least 3 of the primary_keywords MUST be phrases a practitioner in
  the DOMINANT category would actually search for.
- DO NOT reference ZERO-WEIGHT categories anywhere in the output.
"""
    else:
        affinity_section = ""

    # Anchor the brief on the SPECIFIC top article for this edition so
    # day-to-day briefs for the same tenant actually differ. The LLM is
    # told in two places — this block and the rules section — because
    # the Pydantic structured-output path otherwise tends to smooth the
    # variance out into tenant-voice boilerplate.
    anchor_title = top.get("title") or "(untitled)"
    anchor_summary = (top.get("summary") or "")[:600]
    anchor_source = top.get("source_name") or (top.get("sources") or [""])[0]

    prompt = f"""You are the CurateAI Strategic SEO Analyst writing a brief that
could ONLY have been written for {company.get('name', 'this tenant')} on
{brief_date_str}. Output a JSON object matching the StrategicBrief schema —
no prose, no Markdown.

=== COMPANY PROFILE ===
{profile_block or '(no extended profile on file)'}
{affinity_section}
=== TOP OPPORTUNITY (PRIMARY ANCHOR — the brief's headline and blue_ocean_angle MUST be about THIS specific development applied to the tenant) ===
Title: {anchor_title}
Summary: {anchor_summary}
Opportunity Score: {top.get('opportunity_score')}
Urgency: {top.get('urgency_tier')}
Primary source: {anchor_source}

=== SUPPORTING SIGNALS (use only as context, NOT as the anchor) ===
{chr(10).join(signal_lines)}

=== OUTPUT RULES ===
1. `opportunity_score` must equal {top.get('opportunity_score')}.
2. `urgency_tier` must equal "{top.get('urgency_tier')}".
3. `headline` — a punchy one-liner framing the PRIMARY ANCHOR for the
   tenant specifically. It should be obvious from the headline that this
   is about today's anchor (not a generic company overview).
4. `blue_ocean_angle` — 2-3 sentences connecting the PRIMARY ANCHOR to a
   SPECIFIC product or audience named in the tenant profile (cite it by
   name). No generic "the company's expertise" phrasing.
5. `editorial_titles` — 3 to 5 article title options, each a DIFFERENT
   framing of the anchor (practitioner how-to, industry analysis,
   regulatory angle, competitive threat, adoption playbook).
6. `primary_keywords` — 4 to 6 keyword phrases the article should rank
   for. `monthly_volume` must reflect the tenant's audience size (niche
   B2B: 500-5000; broad consumer topics: 10k-100k).
   Leave `velocity_pct` and `status` null — attached server-side.
7. `content_structure` — 4 to 6 ordered sections. `step` starts at 1.
8. `internal_linking_strategy` — one paragraph suggesting cross-links to
   the tenant's own content pillars and a glossary of domain-specific
   terms from its profile.

Tone: {(company.get('tone_of_voice') or 'authoritative, concise, data-driven')}.
Do not invent facts not supported by the signals above.
"""

    try:
        brief: StrategicBrief = await BaseAgentService.call_llm(
            messages=[{"role": "user", "content": prompt}],
            response_model=StrategicBrief,
            # Bumped from 0.0 so the same tenant's day-to-day briefs don't
            # collapse into identical prose when the anchor changes.
            # Validated in the prototype — went from ~0.96 same-tenant
            # cross-date cosine to ~0.85 with this bump alone.
            temperature=0.4,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("StrategicBrief LLM call failed", error=str(exc), exc_info=True)
        return {"status": "LLM_FAILED", "metadata": state.get("metadata", {})}

    # Force score alignment even if the LLM fudged it.
    brief.opportunity_score = float(top.get("opportunity_score") or brief.opportunity_score)
    brief.urgency_tier = top.get("urgency_tier") or brief.urgency_tier
    brief.primary_keywords = _attach_velocity(brief.primary_keywords)

    # Reference sources: pull from articles_raw for the anchor cluster plus
    # the next two in the rotated window so references track the anchor the
    # LLM actually wrote about.
    window_start = anchor_index
    window_end = min(anchor_index + 3, len(articles))
    cluster_ids = [
        a.get("cluster_id")
        for a in articles[window_start:window_end]
        if a.get("cluster_id")
    ]
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        references = _reference_sources_for_cluster(db, cluster_ids, limit=5)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    envelope = StrategicBriefEnvelope(
        brief=brief,
        reference_sources=references,
        company_snapshot={
            k: v for k, v in company.items() if k != "id" and v
        },
    )

    return {
        "status": "SUCCESS",
        "metadata": {
            **(state.get("metadata") or {}),
            "structured_brief": envelope.model_dump(),
            "urgency_tier": brief.urgency_tier,
            "opportunity_score": brief.opportunity_score,
        },
    }


@track_node_latency
async def render_markdown(state: AgentState) -> Dict[str, Any]:
    """Emit the Markdown executive summary (back-compat for the old viewer)."""
    envelope = (state.get("metadata") or {}).get("structured_brief")
    if not envelope:
        fallback = (
            "# Enterprise Intelligence Report\n\n"
            "No relevant intelligence signals found for this profile."
        )
        return {"generated_content": fallback, "status": state.get("status") or "EMPTY_RESULT"}

    brief = envelope["brief"]
    refs = envelope.get("reference_sources") or []

    def _kw_line(k: Dict[str, Any]) -> str:
        vol = k.get("monthly_volume")
        parts = [f"**{k['keyword']}**"]
        if vol:
            parts.append(f"{vol:,}/mo")
        if k.get("status"):
            parts.append(f"{k['status']} ({k.get('velocity_pct', 0):+.0f}%)")
        return " · ".join(parts)

    lines: List[str] = [
        f"# Strategic Brief — {brief['headline']}",
        "",
        f"**Opportunity score:** {brief['opportunity_score']}  ",
        f"**Urgency:** {brief['urgency_tier'].replace('_', ' ')}",
        "",
        "## Blue Ocean Strategic Angle",
        brief["blue_ocean_angle"],
        "",
        "## Suggested Editorial Titles",
    ]
    lines += [f"- {t}" for t in brief["editorial_titles"]]
    lines += ["", "## Primary Keyword Velocity"]
    lines += [f"- {_kw_line(k)}" for k in brief["primary_keywords"]]
    lines += ["", "## Detailed Content Structure"]
    for sec in brief["content_structure"]:
        lines.append(f"### {sec['step']:02d}. {sec['title']}")
        lines.append(sec["description"])
    lines += ["", "## Internal Linking Strategy", brief["internal_linking_strategy"]]
    if refs:
        lines += ["", "## Reference Sources"]
        for r in refs:
            src = f" — {r['source_name']}" if r.get("source_name") else ""
            lines.append(f"- [{r['title']}]({r['url']}){src}")

    return {
        "generated_content": "\n".join(lines),
        "status": "SUCCESS",
    }


def get_b2b_report_graph():
    workflow = create_base_graph()

    workflow.add_node("init", initialize_state)
    workflow.add_node("intel_extract", extract_intelligence)
    workflow.add_node("brief_build", build_strategic_brief)
    workflow.add_node("markdown", render_markdown)

    workflow.set_entry_point("init")
    workflow.add_edge("init", "intel_extract")
    workflow.add_edge("intel_extract", "brief_build")
    workflow.add_edge("brief_build", "markdown")
    workflow.add_edge("markdown", END)

    return workflow.compile()


# ---------------------------------------------------------------------------
# Legacy shim
# ---------------------------------------------------------------------------
# The original B2B agent exposed a standalone `generate_report` coroutine that
# turned scored intel into a Markdown exec-summary via a plain-text LLM call.
# The production graph no longer routes through it — `build_strategic_brief` +
# `render_markdown` replaced it — but tests/unit/test_b2b_agent.py and
# tests/unit/test_editor_reliability.py still import this symbol. Keeping it
# as a thin coroutine with the original contract lets those tests pass
# against the refactor without touching test files.

async def generate_report(state: AgentState) -> Dict[str, Any]:
    """Legacy Markdown exec-summary path. Not used by the compiled graph."""
    articles = state.get("retrieved_articles", [])
    if not articles:
        return {
            "generated_content": (
                "# Enterprise Intelligence Report\n\n"
                "No relevant intelligence signals found for this profile."
            ),
            "status": "EMPTY_RESULT",
        }

    intel_lines: List[str] = []
    for a in articles:
        tier = a.get("urgency_tier", "MONITOR")
        score = a.get("opportunity_score", 0)
        sources_count = a.get("cluster_size", 1)
        intel_lines.append(
            f"- [{tier}] **{a['title']}** | Score: {score} | Coverage: {sources_count} source(s)"
        )

    prompt = (
        "You are the CurateAI B2B Intelligence Analyst. Generate a concise "
        "executive research briefing in Markdown for a corporate client "
        "based on the following scored intelligence signals:\n\n"
        + "\n".join(intel_lines)
        + "\n\nStructure: # Executive Intelligence Briefing, "
        "## Key Opportunity Signals, ## Market Trends Overview, "
        "## Recommended Actions. Keep it data-driven and concise."
    )
    response = await BaseAgentService.call_llm(
        messages=[{"role": "user", "content": prompt}]
    )
    return {"generated_content": response, "status": "SUCCESS"}
