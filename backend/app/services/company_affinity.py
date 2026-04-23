"""Company content-affinity extractor.

Mirrors the user-persona CategoryWeights taxonomy. Given a company
profile we ask the LLM to distribute 1.0 of probability mass over the
ten production categories, emphasising those named in content_pillars /
key_products / target_audience.

The resulting 10-dim vector is persisted in ``companies.content_affinity_weights``
and consumed by the B2B agent's Strategic Brief prompt as a hard
constraint — dominant categories drive headline / keyword vocabulary;
zero-weight categories are forbidden from appearing.

Validated under ``Prototyping/SEO_Personalized/prototype.py`` — cross-tenant
brief-text cosine dropped from 0.60 → 0.52 (~8 pts) when the affinity
vector was injected as a prompt constraint at temperature=0.4.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.logging_conf import get_logger
from app.core.schemas import CompanyContentAffinity
from app.services.llm_base import BaseLLMService

logger = get_logger("app.services.company_affinity")


EXTRACTOR_SYSTEM = """\
You are the CurateAI company-affinity extractor. You read a corporate
profile and return a 10-dimensional weight vector describing how much
of the company's content gravity sits in each fixed taxonomy category.

Rules:
- Every weight is a float in [0, 1].
- The ten weights MUST sum to approximately 1.0 (treat this as a
  normalized probability distribution).
- Zero out categories that have no realistic tie to the profile — do
  NOT spread mass evenly when the profile is narrow.
- Emphasize categories explicitly named in content_pillars, key_products,
  and target_audience; demote categories that appear only incidentally.

Taxonomy:
- llms: Large Language Models, foundation models, prompting, RAG
- ai_agents: Agentic frameworks, autonomous workflows, tool-using agents
- computer_vision: CV, vision-language, image / video models
- security: Cybersecurity, fraud, prompt injection, adversarial ML, zero-trust
- hardware: Chips, accelerators, inference silicon, rack infra
- software_engineering: IDE tooling, CI/CD, code review, developer experience
- ai_policy: Governance, regulation, compliance, BSA/AML, responsible AI
- general_ai: Broad-interest AI industry news
- data_engineering: ETL, data platforms, feature stores, graph, SEC data
- startups: Startup strategy, fundraising, product-market fit, fintech, finance
"""


def _profile_block(company: Dict[str, Any]) -> str:
    keep_fields = (
        "name", "industry", "description", "target_audience",
        "key_products", "content_pillars", "competitors", "tone_of_voice",
    )
    return "\n".join(
        f"- {k}: {company[k]}"
        for k in keep_fields
        if company.get(k)
    )


async def extract_company_affinity(
    company: Dict[str, Any],
) -> Optional[Dict[str, float]]:
    """One structured LLM call → 10-dim category weight vector.

    Returns ``None`` on extraction failure (don't block the profile save).
    """
    profile_text = _profile_block(company)
    if not profile_text.strip():
        logger.warning("Affinity skipped — empty company profile")
        return None

    try:
        result: CompanyContentAffinity = await BaseLLMService.get_structured_completion(
            response_model=CompanyContentAffinity,
            messages=[
                {"role": "system", "content": EXTRACTOR_SYSTEM},
                {"role": "user", "content": f"Company profile:\n{profile_text}"},
            ],
            model="gpt-4o-mini",
            temperature=0.0,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Affinity extraction failed — proceeding without weights",
            company_name=company.get("name"),
            error=str(exc),
        )
        return None

    weights = result.model_dump()
    total = sum(weights.values()) or 1.0
    # Renormalise so downstream consumers can rely on sum≈1.0 even when
    # the LLM drifts (it occasionally returns 0.9 or 1.1 despite the
    # "must sum to 1.0" instruction).
    normalised = {k: round(v / total, 4) for k, v in weights.items()}
    logger.info(
        "Affinity extracted",
        company_name=company.get("name"),
        dominant=[k for k, v in sorted(normalised.items(), key=lambda x: -x[1])[:3]],
    )
    return normalised
