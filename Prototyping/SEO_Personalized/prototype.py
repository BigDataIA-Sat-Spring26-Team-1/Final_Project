"""SEO Personalization prototype — end-to-end validation against real
Qdrant + Snowflake, across multiple dates per tenant.

Run:
    uv sync
    uv run python prototype.py

What this does:

1. Connects to Snowflake + Qdrant using the repo's backend/.env.

2. **Stage A — affinity extraction.** One structured LLM call per company
   maps its profile onto the production 10-category taxonomy.

3. **Stage B — real retrieval per (tenant, date).** Same code-path as
   production SearchService:
      a. Embed the company's free-text query.
      b. Qdrant → top-40 cluster candidates.
      c. Date-filter by joining against articles_raw.published_at within
         [edition_date - 1, edition_date] — only keep clusters that had
         at least one article published in that window.
      d. Trim to top-8.

4. **Stage C — brief generation** under OLD prompt (current production)
   vs NEW prompt (affinity vector injected as hard constraint, top
   dominant categories named, temperature 0.4). Runs for each
   (tenant, date) pair.

5. **Two divergence matrices.** Both use cosine similarity on embeddings
   of the generated brief text; lower = more distinct.
      - Cross-tenant same-date: does TechCorp's 2026-04-22 brief differ
        from Ledgerwise's 2026-04-22 brief?
      - Same-tenant cross-date: does TechCorp's 2026-04-18 brief differ
        from TechCorp's 2026-04-22 brief?

   Success criterion:
      - NEW cross-tenant mean cosine strictly < OLD cross-tenant mean.
      - Same-tenant cross-date cosine < 0.95 (i.e. each day's brief is
        at least a little different from every other day's brief).
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# -- env ----------------------------------------------------------------

_ROOT = Path(__file__).parent
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT.parents[1] / "backend" / ".env")

for required in ("OPENAI_API_KEY", "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER",
                 "SNOWFLAKE_PASSWORD", "SNOWFLAKE_DATABASE", "QDRANT_URL"):
    if not os.environ.get(required):
        print(f"! {required} not set (check backend/.env)", file=sys.stderr)
        sys.exit(2)

client = OpenAI()
EMBED_MODEL = "text-embedding-3-small"
GEN_MODEL = "gpt-4o-mini"


# -- Snowflake + Qdrant clients -----------------------------------------

def snowflake_conn():
    import snowflake.connector
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
        role=os.environ.get("SNOWFLAKE_ROLE"),
    )


def qdrant_client():
    from qdrant_client import QdrantClient
    if os.environ.get("QDRANT_API_KEY"):
        return QdrantClient(url=os.environ["QDRANT_URL"],
                            api_key=os.environ["QDRANT_API_KEY"])
    return QdrantClient(url=os.environ["QDRANT_URL"])


# -- taxonomy + affinity ------------------------------------------------

TAXONOMY: List[str] = [
    "llms", "ai_agents", "computer_vision", "security", "hardware",
    "software_engineering", "ai_policy", "general_ai", "data_engineering",
    "startups",
]


class CompanyContentAffinity(BaseModel):
    llms: float = Field(ge=0.0, le=1.0)
    ai_agents: float = Field(ge=0.0, le=1.0)
    computer_vision: float = Field(ge=0.0, le=1.0)
    security: float = Field(ge=0.0, le=1.0)
    hardware: float = Field(ge=0.0, le=1.0)
    software_engineering: float = Field(ge=0.0, le=1.0)
    ai_policy: float = Field(ge=0.0, le=1.0)
    general_ai: float = Field(ge=0.0, le=1.0)
    data_engineering: float = Field(ge=0.0, le=1.0)
    startups: float = Field(ge=0.0, le=1.0)

    def as_dict(self) -> Dict[str, float]:
        return self.model_dump()


# -- static company fixtures --------------------------------------------

@dataclass
class Company:
    name: str
    industry: str
    description: str
    target_audience: str
    key_products: str
    content_pillars: str
    competitors: str
    tone_of_voice: str


COMPANIES: List[Company] = [
    Company(
        name="TechCorp Inc.",
        industry="Developer Productivity & AI Tooling",
        description=(
            "TechCorp Inc. builds integrated developer-productivity tools "
            "that embed LLM copilots directly inside the IDE, CI/CD "
            "pipelines, and code review workflows. We help engineering "
            "teams ship faster with AI-assisted code generation, review, "
            "and test authoring."
        ),
        target_audience=(
            "VPs of Engineering and Platform leads at mid-market SaaS "
            "companies (50–500 engineers) modernising their AI-assisted "
            "delivery stack."
        ),
        key_products=(
            "AI Pair-Programming IDE extension, Pull-Request Copilot, "
            "Test-Generation Service, Agentic Refactor Assistant."
        ),
        content_pillars=(
            "AI-assisted coding, developer experience, agentic software "
            "engineering, CI/CD automation, LLM cost control."
        ),
        competitors="GitHub Copilot, Cursor, Sourcegraph Cody, Codeium, Tabnine.",
        tone_of_voice="TECHNICAL",
    ),
    Company(
        name="Ledgerwise AI",
        industry="AI-powered Fintech Risk & Compliance",
        description=(
            "Ledgerwise AI is a fintech platform that uses on-device "
            "machine learning and graph analytics to detect real-time "
            "payment fraud, enforce BSA/AML compliance, and automate "
            "suspicious-activity reporting for consumer digital-banking "
            "apps and mobile wallets."
        ),
        target_audience=(
            "Chief Risk Officers, Heads of Fraud, and BSA/AML compliance "
            "leads at neobanks, challenger banks, and payment processors."
        ),
        key_products=(
            "Ledgerwise Sentinel (real-time transaction scoring), "
            "Ledgerwise Casebook (SAR/CTR workflow + auto-narrative "
            "generation), Ledgerwise Graph (entity-resolution fraud-ring "
            "detection)."
        ),
        content_pillars=(
            "Real-time payment fraud, BSA/AML automation, regulatory "
            "compliance for fintech, graph ML for financial crime, "
            "privacy-preserving ML on transaction data."
        ),
        competitors="Alloy, Hawk AI, ComplyAdvantage, Feedzai, Sardine.",
        tone_of_voice="AUTHORITATIVE",
    ),
    Company(
        name="Meridian Capital Research",
        industry="AI-driven Institutional Investment Research",
        description=(
            "Meridian Capital Research is an AI-first investment research "
            "firm building an LLM-powered alpha platform that ingests SEC "
            "filings, earnings-call transcripts, insider-transaction data, "
            "and alternative data sources to produce quantitative trade "
            "theses for long/short equity funds."
        ),
        target_audience=(
            "Portfolio managers and equity analysts at multi-strategy "
            "hedge funds, family offices, and pension fund internal "
            "investment teams."
        ),
        key_products=(
            "Meridian Alpha Engine (LLM-native thesis generator), "
            "Meridian Filings Index (structured SEC Q&A), "
            "Meridian Transcript Signal (earnings-call sentiment)."
        ),
        content_pillars=(
            "LLM-driven equity research, alternative data for alpha, "
            "earnings-call NLP, SEC filings extraction, quantitative "
            "portfolio construction, institutional investment workflows."
        ),
        competitors="AlphaSense, Bloomberg Terminal, Kensho, FactSet, YipitData.",
        tone_of_voice="AUTHORITATIVE",
    ),
]


# -- extraction ----------------------------------------------------------

EXTRACTOR_SYSTEM = """\
You are the CurateAI company-affinity extractor. Read a corporate
profile and return a 10-dimensional weight vector describing how much
of the company's content gravity sits in each fixed taxonomy category.

Rules:
- Every weight ∈ [0, 1].
- Ten weights sum to approximately 1.0.
- Zero out categories with no realistic tie; do not spread evenly.
- Emphasize categories named in content_pillars, key_products, and
  target_audience; demote categories mentioned only incidentally.

Taxonomy:
- llms: LLMs, foundation models, prompting, RAG
- ai_agents: Agentic frameworks, autonomous workflows, tool use
- computer_vision: CV, vision-language, image / video models
- security: Cybersecurity, fraud, prompt injection, adversarial ML
- hardware: Chips, accelerators, inference silicon
- software_engineering: IDE tooling, CI/CD, code review, devex
- ai_policy: Governance, regulation, compliance, BSA/AML, responsible AI
- general_ai: Broad AI industry news
- data_engineering: ETL, data platforms, feature stores, graph, SEC data
- startups: Startup strategy, fundraising, fintech, finance industry
"""


def extract_affinity(c: Company) -> CompanyContentAffinity:
    profile = "\n".join(
        f"- {k}: {v}"
        for k, v in {
            "name": c.name, "industry": c.industry,
            "description": c.description,
            "target_audience": c.target_audience,
            "key_products": c.key_products,
            "content_pillars": c.content_pillars,
            "competitors": c.competitors,
            "tone_of_voice": c.tone_of_voice,
        }.items()
    )
    resp = client.beta.chat.completions.parse(
        model=GEN_MODEL, temperature=0.0,
        messages=[
            {"role": "system", "content": EXTRACTOR_SYSTEM},
            {"role": "user", "content": f"Company profile:\n{profile}"},
        ],
        response_format=CompanyContentAffinity,
    )
    return resp.choices[0].message.parsed  # type: ignore[return-value]


# -- retrieval (real Qdrant + Snowflake date filter) --------------------

def build_company_query(c: Company) -> str:
    parts = [c.name, c.industry, c.description, c.target_audience,
             c.key_products, c.content_pillars]
    return " ".join(p for p in parts if p).strip()


def embed(text: str) -> np.ndarray:
    r = client.embeddings.create(model=EMBED_MODEL, input=text)
    v = np.array(r.data[0].embedding, dtype=np.float32)
    return v / (np.linalg.norm(v) or 1.0)


def retrieve(
    qc, sf_cur, c: Company, edition_date: str, top_n: int = 8, overfetch: int = 40
) -> List[Dict[str, Any]]:
    """Top-N real clusters for the company on the given edition_date.

    Mirrors production SearchService: embed the free-text query, hit
    Qdrant, post-filter by articles_raw.published_at within
    [edition_date - 1, edition_date]. Returns ordered hits with real
    title/summary from the Qdrant payload (payloads are denormalized
    snapshots of article_clusters)."""
    qvec = embed(build_company_query(c)).tolist()
    qres = qc.query_points(collection_name="articles", query=qvec, limit=overfetch)
    if not qres.points:
        return []
    hits = [(str(h.id), h.score, h.payload or {}) for h in qres.points]

    ids = [h[0] for h in hits]
    placeholders = ",".join(["%s"] * len(ids))
    sf_cur.execute(
        f"""
        SELECT DISTINCT id, cluster_id
        FROM articles_raw
        WHERE (id IN ({placeholders}) OR cluster_id IN ({placeholders}))
          AND published_at IS NOT NULL
          AND CAST(published_at AS DATE)
              BETWEEN DATEADD(day, -1, %s::DATE) AND %s::DATE
        """,
        (*ids, *ids, edition_date, edition_date),
    )
    fresh = set()
    for aid, cid in sf_cur.fetchall():
        if aid: fresh.add(aid)
        if cid: fresh.add(cid)

    kept = [(hid, s, p) for hid, s, p in hits if hid in fresh][:top_n]
    # If the date window starved the result (rare, small day), fall back
    # to unscoped top-N so the brief has something to anchor on — we flag
    # it in the return shape.
    scoped_hit_count = len(kept)
    if len(kept) < 3:
        kept = hits[:top_n]
    return [
        {
            "cluster_id": hid, "score": round(s, 4),
            "title": (p.get("title") or "").strip(),
            "summary": (p.get("summary") or "").strip(),
            "source_name": p.get("source_name") or "",
            "_date_scoped": hid in fresh,
            "_scoped_in_window": scoped_hit_count,
        }
        for hid, s, p in kept
    ]


# -- brief generation ---------------------------------------------------

class BriefKeyword(BaseModel):
    keyword: str
    monthly_volume: int | None = None


class BriefSection(BaseModel):
    step: int
    title: str
    description: str


class StrategicBrief(BaseModel):
    headline: str
    blue_ocean_angle: str
    editorial_titles: List[str] = Field(min_length=3, max_length=5)
    primary_keywords: List[BriefKeyword] = Field(min_length=4, max_length=6)
    content_structure: List[BriefSection] = Field(min_length=3, max_length=6)
    internal_linking_strategy: str


OLD_SYSTEM = """\
You are the CurateAI Strategic SEO Analyst producing a single-topic
Strategic Brief for a corporate client. Output JSON matching the
StrategicBrief schema. Write a punchy headline, a 2-3 sentence
blue-ocean angle, 3-5 editorial titles, 4-6 primary keywords with
realistic monthly_volume, 4-6 ordered content_structure sections, and
a one-paragraph internal_linking_strategy. Tone: authoritative,
data-driven. Ground everything in the signals provided. Do not invent
facts.
"""


NEW_SYSTEM_TEMPLATE = """\
You are the CurateAI Strategic SEO Analyst producing a brief for
{tenant} — NOT a generic AI industry brief. Every line must read as if
it could only have been written for this specific tenant on this
specific date.

=== TENANT CONTENT-AFFINITY (10-dim taxonomy, weights sum to ~1.0) ===
{affinity_block}
DOMINANT CATEGORIES: {dominant}
ZERO-WEIGHT CATEGORIES (never mention): {zero}

=== HARD CONSTRAINTS ===
- Every editorial_title must reference at least one DOMINANT category
  using tenant-specific vocabulary, not the raw taxonomy token.
- At least 3 primary_keywords must be phrases a practitioner in the
  dominant category would actually type into a search bar.
- blue_ocean_angle must cite a product or audience named in the tenant
  profile below — no generic "the company's expertise" phrasing.
- monthly_volume must reflect the tenant's audience size (niche B2B
  500–5000; broader topics 10k–100k).
- Never reference ZERO-WEIGHT categories, even in passing.

Output the StrategicBrief JSON — no prose, no Markdown.
"""


def _affinity_block(w: Dict[str, float]) -> str:
    return "\n".join(
        f"  {k:<24} {v:.2f}"
        for k, v in sorted(w.items(), key=lambda x: -x[1])
    )


def _tenant_block(c: Company) -> str:
    return (
        f"name: {c.name}\nindustry: {c.industry}\n"
        f"description: {c.description}\ntarget_audience: {c.target_audience}\n"
        f"key_products: {c.key_products}\ncontent_pillars: {c.content_pillars}\n"
        f"tone_of_voice: {c.tone_of_voice}"
    )


def _signals_block(articles: List[Dict[str, Any]]) -> str:
    lines = []
    for a in articles:
        title = a.get("title") or "(untitled)"
        summary = (a.get("summary") or "")[:240]
        lines.append(f"- {title}" + (f" — {summary}" if summary else ""))
    return "\n".join(lines) or "(no articles retrieved)"


def gen_brief_old(c: Company, articles: List[Dict[str, Any]], edition_date: str) -> StrategicBrief:
    user = (f"Edition date: {edition_date}\n\n"
            f"=== TENANT PROFILE ===\n{_tenant_block(c)}\n\n"
            f"=== REAL SIGNALS (retrieved from Qdrant+Snowflake for this date) ===\n"
            f"{_signals_block(articles)}")
    resp = client.beta.chat.completions.parse(
        model=GEN_MODEL, temperature=0.0,
        messages=[{"role": "system", "content": OLD_SYSTEM},
                  {"role": "user", "content": user}],
        response_format=StrategicBrief,
    )
    return resp.choices[0].message.parsed  # type: ignore[return-value]


def gen_brief_new(c: Company, w: Dict[str, float],
                  articles: List[Dict[str, Any]], edition_date: str) -> StrategicBrief:
    dominant = [k for k, v in sorted(w.items(), key=lambda x: -x[1])[:3] if v >= 0.10]
    zero = [k for k, v in w.items() if v < 0.05]
    system = NEW_SYSTEM_TEMPLATE.format(
        tenant=c.name, affinity_block=_affinity_block(w),
        dominant=", ".join(dominant) or "(none)",
        zero=", ".join(zero) or "(none)",
    )
    user = (f"Edition date: {edition_date}\n\n"
            f"=== TENANT PROFILE ===\n{_tenant_block(c)}\n\n"
            f"=== REAL SIGNALS (retrieved from Qdrant+Snowflake for this date) ===\n"
            f"{_signals_block(articles)}")
    resp = client.beta.chat.completions.parse(
        model=GEN_MODEL, temperature=0.4,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        response_format=StrategicBrief,
    )
    return resp.choices[0].message.parsed  # type: ignore[return-value]


def brief_as_text(b: StrategicBrief) -> str:
    parts = [
        b.headline, b.blue_ocean_angle,
        " | ".join(b.editorial_titles),
        " | ".join(f"{k.keyword} ({k.monthly_volume or '?'})" for k in b.primary_keywords),
        " | ".join(f"{s.step:02d} {s.title}: {s.description}" for s in b.content_structure),
        b.internal_linking_strategy,
    ]
    return "\n".join(parts)


# -- matrix helpers -----------------------------------------------------

def pairwise_mean(vecs: List[np.ndarray]) -> float:
    out = []
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            out.append(float(np.dot(vecs[i], vecs[j])))
    return float(np.mean(out)) if out else 0.0


def fmt_weights(w: Dict[str, float]) -> str:
    items = [(k, v) for k, v in w.items() if v > 0.03]
    items.sort(key=lambda x: -x[1])
    return ", ".join(f"{k}={v:.2f}" for k, v in items) or "(empty)"


# -- main ---------------------------------------------------------------

def main() -> None:
    print("=" * 78)
    print("SEO Personalization Prototype v3 — REAL Qdrant + Snowflake retrieval,")
    print("per-tenant × per-date brief comparison (OLD vs NEW prompt).")
    print("=" * 78)

    # 5 recent dates that have ingestion coverage.
    dates = [(date(2026, 4, 22) - timedelta(days=d)).isoformat() for d in range(5)]
    print(f"\ndates tested: {dates}\n")

    qc = qdrant_client()
    sf = snowflake_conn()
    sf_cur = sf.cursor()

    try:
        # Stage A — affinities
        print("── Stage A — affinity extraction ────────────────────────────────")
        affinities: Dict[str, Dict[str, float]] = {}
        for c in COMPANIES:
            aff = extract_affinity(c)
            affinities[c.name] = aff.as_dict()
            print(f"  {c.name:<26}  {fmt_weights(aff.as_dict())}")

        # Stage B — real retrieval per (tenant, date)
        print("\n── Stage B — real retrieval (Qdrant → date-filter) ──────────────")
        retrieved: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for c in COMPANIES:
            for d in dates:
                arts = retrieve(qc, sf_cur, c, d, top_n=8)
                retrieved[(c.name, d)] = arts
                in_window = sum(1 for a in arts if a["_date_scoped"])
                print(f"  {c.name:<26} {d}  kept={len(arts):>2}  in_window={in_window:>2}  "
                      f"top='{(arts[0]['title'] if arts else '')[:60]}'")

        # Stage C — OLD vs NEW briefs
        print("\n── Stage C — brief generation: OLD vs NEW prompt ────────────────")
        old_briefs: Dict[Tuple[str, str], StrategicBrief] = {}
        new_briefs: Dict[Tuple[str, str], StrategicBrief] = {}
        for c in COMPANIES:
            for d in dates:
                arts = retrieved[(c.name, d)]
                if not arts:
                    print(f"  ! {c.name} {d}  no articles retrieved — skipping")
                    continue
                print(f"  · {c.name} {d} OLD …")
                old_briefs[(c.name, d)] = gen_brief_old(c, arts, d)
                print(f"  · {c.name} {d} NEW …")
                new_briefs[(c.name, d)] = gen_brief_new(c, affinities[c.name], arts, d)

        # Embed all briefs once
        emb_old = {k: embed(brief_as_text(b)) for k, b in old_briefs.items()}
        emb_new = {k: embed(brief_as_text(b)) for k, b in new_briefs.items()}

        # Matrix 1 — cross-tenant same-date
        print("\n── Matrix 1 — cross-tenant, same-date (lower = tenants differ) ──")
        print(f"  {'DATE':<12} {'OLD mean':>10}  {'NEW mean':>10}  {'Δ':>8}")
        cross_old_all, cross_new_all = [], []
        for d in dates:
            vecs_old = [emb_old[(c.name, d)] for c in COMPANIES if (c.name, d) in emb_old]
            vecs_new = [emb_new[(c.name, d)] for c in COMPANIES if (c.name, d) in emb_new]
            if len(vecs_old) < 2:
                print(f"  {d:<12}  (insufficient data)")
                continue
            mo = pairwise_mean(vecs_old); mn = pairwise_mean(vecs_new)
            cross_old_all.append(mo); cross_new_all.append(mn)
            print(f"  {d:<12} {mo:>10.4f}  {mn:>10.4f}  {mn - mo:>+8.4f}")
        if cross_old_all:
            print(f"  {'OVERALL':<12} {np.mean(cross_old_all):>10.4f}  "
                  f"{np.mean(cross_new_all):>10.4f}  "
                  f"{np.mean(cross_new_all) - np.mean(cross_old_all):>+8.4f}")

        # Matrix 2 — same-tenant cross-date
        print("\n── Matrix 2 — same-tenant, cross-date (lower = days differ) ─────")
        print(f"  {'TENANT':<26} {'OLD mean':>10}  {'NEW mean':>10}  {'Δ':>8}")
        intra_old_all, intra_new_all = [], []
        for c in COMPANIES:
            vecs_old = [emb_old[(c.name, d)] for d in dates if (c.name, d) in emb_old]
            vecs_new = [emb_new[(c.name, d)] for d in dates if (c.name, d) in emb_new]
            if len(vecs_old) < 2:
                print(f"  {c.name:<26}  (insufficient data)")
                continue
            mo = pairwise_mean(vecs_old); mn = pairwise_mean(vecs_new)
            intra_old_all.append(mo); intra_new_all.append(mn)
            print(f"  {c.name:<26} {mo:>10.4f}  {mn:>10.4f}  {mn - mo:>+8.4f}")
        if intra_old_all:
            print(f"  {'OVERALL':<26} {np.mean(intra_old_all):>10.4f}  "
                  f"{np.mean(intra_new_all):>10.4f}  "
                  f"{np.mean(intra_new_all) - np.mean(intra_old_all):>+8.4f}")

        # Qualitative samples — headlines only
        print("\n── sample: 2026-04-22 headlines side-by-side ────────────────────")
        focus = "2026-04-22"
        for c in COMPANIES:
            o = old_briefs.get((c.name, focus))
            n = new_briefs.get((c.name, focus))
            if not o or not n:
                continue
            print(f"\n  {c.name}")
            print(f"    OLD: {o.headline}")
            print(f"    NEW: {n.headline}")
            print(f"    OLD titles: {o.editorial_titles[:2]}")
            print(f"    NEW titles: {n.editorial_titles[:2]}")

        # Persist raw dump
        out_path = _ROOT / "last_run_v3.json"
        dump = {
            "dates": dates,
            "affinities": affinities,
            "retrieval_stats": {
                f"{c.name}|{d}": {
                    "kept": len(retrieved[(c.name, d)]),
                    "in_window": sum(1 for a in retrieved[(c.name, d)] if a["_date_scoped"]),
                    "top_titles": [a["title"] for a in retrieved[(c.name, d)][:3]],
                }
                for c in COMPANIES for d in dates
                if (c.name, d) in retrieved
            },
            "briefs": {
                f"{c.name}|{d}": {
                    "old": old_briefs[(c.name, d)].model_dump(),
                    "new": new_briefs[(c.name, d)].model_dump(),
                }
                for c in COMPANIES for d in dates
                if (c.name, d) in old_briefs
            },
        }
        out_path.write_text(json.dumps(dump, indent=2))
        print(f"\nwrote → {out_path}")
    finally:
        sf_cur.close(); sf.close()


if __name__ == "__main__":
    main()
