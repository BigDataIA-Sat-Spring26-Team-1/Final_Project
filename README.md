# CurateAI

A multi-tenant AI news intelligence platform: ingests ~3 000 technical articles a day from RSS, ArXiv, and HackerNews; deduplicates them into story clusters; ranks them against the reader's persona; and publishes a daily newsletter for individuals plus a research brief for enterprise tenants. Built on FastAPI, Next.js, LangGraph, Airflow, Snowflake, and Qdrant.

## Table of contents

- [Live demo URLs](#live-demo-urls)
- [Architecture at a glance](#architecture-at-a-glance)
- [Folder layout](#folder-layout)
- [Quickstart (local dev)](#quickstart-local-dev)
- [Running the full stack on a VM](#running-the-full-stack-on-a-vm)
- [Production topology (Cloud Run + GCE)](#production-topology-cloud-run--gce)
- [Feature walk-through](#feature-walk-through)
- [Testing](#testing)
- [Observability](#observability)
- [MCP integration](#mcp-integration)
- [Architecture decisions](#architecture-decisions)
- [Known limitations](#known-limitations)
- [Access, permissions, secrets](#access-permissions-secrets)
- [Troubleshooting](#troubleshooting)
- [License + credits](#license--credits)

## Live demo URLs

| Service | URL | Auth |
|---|---|---|
| Frontend (Next.js) | https://curateai-frontend-sjhg7huf4q-uc.a.run.app | public |
| Backend (FastAPI) | https://curateai-backend-sjhg7huf4q-uc.a.run.app | public, rate-limited |
| Airflow UI | http://34.16.38.157:8080 | basic auth — demo credentials in Secret Manager (`AIRFLOW_PASSWORD`) |
| OpenAPI docs | https://curateai-backend-sjhg7huf4q-uc.a.run.app/docs | public |
| Prometheus metrics | https://curateai-backend-sjhg7huf4q-uc.a.run.app/metrics | public |

## Architecture at a glance

```
                             ┌──────────────┐
                             │  Browser     │
                             └──────┬───────┘
                                    │ https
                                    ▼
                       ┌────────────────────────┐
                       │  Next.js frontend      │
                       │  (Cloud Run)           │
                       └──────┬─────────────────┘
                              │ NEXT_PUBLIC_API_URL
                              ▼
                       ┌────────────────────────┐
                       │  FastAPI backend       │
                       │  (Cloud Run)           │
                       │                        │
                       │  REST + MCP (SSE)      │
                       │  + /metrics            │
                       └──┬──────────┬──────────┘
                          │          │
              OpenAI ◄────┘          │
                                     ▼
                   ┌──────────────────────────────┐
                   │  Airflow on GCE VM           │
                   │  scheduler + webserver +     │
                   │  Postgres meta-DB            │
                   │                              │
                   │  8 DAGs (ingestion, dedup,   │
                   │  trend, qdrant_sync, b2c,    │
                   │  personalization, b2b,        │
                   │  behavioral_rollup)           │
                   └─────┬────────┬────────┬──────┘
                         ▼        ▼        ▼
                  Snowflake   Qdrant    External
                  (warehouse) Cloud     (OpenAI, RSS,
                                        ArXiv, HN)
```

## Folder layout

| Path | Role |
|---|---|
| `backend/` | FastAPI API + LangGraph agents + Snowflake / Qdrant clients |
| `backend/app/api/` | Route modules — one per domain (personas, ingestion, trend, b2b, admin, …) |
| `backend/app/services/` | Business logic (ingestion crawlers, deduplication, search, agents) |
| `backend/app/repository/` | Snowflake persistence (user personas, articles) |
| `backend/app/core/` | Config, logging, metrics, MCP server, Airflow client |
| `backend/tests/` | Unit + integration suites (pytest) |
| `frontend/` | Next.js 16 app (Turbopack) |
| `frontend/src/app/` | File-router pages: `/user/*`, `/company/*`, `/admin/*`, `/trending` |
| `frontend/src/components/` | Reusable components (Navigation, MetricsPanel, AdminManagementPanel, …) |
| `frontend/tests/` | Vitest + RTL (59 tests) |
| `airflow/dags/` | 8 production DAGs |
| `airflow/Dockerfile` | Airflow image (adds curl + extra Python deps) |
| `airflow/README.md` | VM provisioning runbook |
| `infrastructure/` | Cloud Build configs + docker-compose for the VM |
| `.github/workflows/` | CI: lint, test, deploy |

## Quickstart (local dev)

Prereqs: Python 3.12, Node 22, Docker, [uv](https://docs.astral.sh/uv/), a `.env` at the repo root with Snowflake + OpenAI + Qdrant credentials.

The fastest path is the automated setup script at the repo root:

```bash
chmod +x setup_dev.sh
./setup_dev.sh   # starts Qdrant, installs Python deps, runs agent health checks
```

Or manually:

```bash
# 1. Install + start Qdrant (local, for dev only — prod uses Qdrant Cloud)
docker run -d --name curateai_qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant:v1.11.3

# 2. Backend
cd backend
uv sync --extra test
uv run uvicorn app.main:app --reload --port 8000
# -> http://localhost:8000/docs

# 3. Frontend (new terminal)
cd frontend
npm install
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local
npm run dev
# -> http://localhost:3000
```

To seed Snowflake with mock user personas for local development:

```bash
cd backend
uv run python scripts/seed_mock_users.py
```

With just these two services the app is fully usable for browsing, persona editing, and reading newsletters. Airflow is only needed when you want to actually fire the ingestion / dedup / ranking pipelines — otherwise the read endpoints happily return whatever is already in Snowflake.

### Required `.env` keys

```ini
# Application
SECRET_KEY=<32-byte random string>
APP_ENV=dev                       # dev | uat | prod

# Snowflake
SNOWFLAKE_ACCOUNT=<account>.<region>
SNOWFLAKE_USER=...
SNOWFLAKE_PASSWORD=...
SNOWFLAKE_DATABASE=CURATE_AI
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=...
SNOWFLAKE_ROLE=...

# OpenAI (embeddings + LLM gateway via LiteLLM)
OPENAI_API_KEY=sk-...

# Qdrant (local or Qdrant Cloud)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=                   # empty for local

# Airflow (only required if the backend should be able to trigger DAGs)
AIRFLOW_HOST=                     # e.g. http://34.16.38.157:8080, blank disables
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=admin

# Airflow-side only (on the VM)
AIRFLOW_FERNET_KEY=               # python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
AIRFLOW_ADMIN_USERNAME=admin
AIRFLOW_ADMIN_PASSWORD=<rotate before demo>
AIRFLOW_ADMIN_EMAIL=you@example.com

# MailerSend (newsletter delivery)
# API key is a Secret Manager secret in prod. Leave blank locally to
# short-circuit sends — the /newsletter/send endpoint will return
# status=MAILER_DISABLED without contacting the provider.
MAILERSEND_API_KEY=
MAILERSEND_FROM_EMAIL=info@test-q3enl6kez3742vwr.mlsender.net
MAILERSEND_FROM_NAME=CurateAI Newsletter
# Dev/staging safety rail: when set, every outgoing newsletter is
# redirected to this address regardless of the user's stored email.
# Required on MailerSend trial plans (they only deliver to the account
# owner). Leave EMPTY in production so real users get their own mail.
MAILERSEND_TEST_RECIPIENT=

# CORS — only read by the backend. Comma-separated list of browser origins
# allowed to hit the API. Must include every frontend URL (Cloud Run, local
# dev, preview builds). Defaults to localhost-only when unset.
CORS_ORIGINS=http://localhost:3000

# JWT / session token signing (falls back to SECRET_KEY if unset)
JWT_SECRET=                       # optional — uses SECRET_KEY by default
JWT_EXPIRES_IN=14400              # seconds; matches the frontend idle expiry

# LLM routing knobs (optional — sensible defaults ship in config.py)
EMBEDDING_MODEL=text-embedding-3-small
LLM_DEFAULT_MODEL=gpt-4o-mini
```

## Running the full stack on a VM

The VM runs Airflow + Qdrant + Postgres under one docker-compose file. Backend / frontend are not needed on the VM; they live on Cloud Run.

```bash
# on the VM
git clone https://github.com/BigDataIA-Sat-Spring26-Team-1/Final_Project.git
cd Final_Project
cp ~/.env .           # with all the keys above

docker compose -f infrastructure/docker-compose.vm.yml up -d airflow-init
docker compose -f infrastructure/docker-compose.vm.yml up -d qdrant postgres \
  airflow-webserver airflow-scheduler
```

Full runbook including GCE provisioning, firewall, budget alerting, and Cloud Run wiring: [`airflow/README.md`](airflow/README.md).

## Production topology (Cloud Run + GCE)

| Component | Host | Image / Service |
|---|---|---|
| Backend | Cloud Run `curateai-backend` (us-central1) | `us-central1-docker.pkg.dev/<project>/curateai/backend` |
| Frontend | Cloud Run `curateai-frontend` (us-central1) | `us-central1-docker.pkg.dev/<project>/curateai/frontend` |
| Airflow | `curateai-airflow` e2-standard-2 VM, us-central1-a | docker-compose |
| Snowflake | Snowflake Cloud | database `CURATE_AI`, schema `PUBLIC` |
| Qdrant | Qdrant Cloud | collection `articles`, 1536-dim cosine |
| OpenAI | managed | `text-embedding-3-small`, `gpt-4o-mini` |

Secrets are stored in GCP Secret Manager (`SECRET_KEY`, `SNOWFLAKE_PASSWORD`, `OPENAI_API_KEY`, `QDRANT_API_KEY`, `MAILERSEND_API_KEY`, `AIRFLOW_PASSWORD`) and bound to the Cloud Run service account at deploy time.

## Personalization — the MVP

Every tenant surface in CurateAI (consumer newsletter, enterprise Strategic Brief) reaches the same embedding store (Qdrant `articles`, 1,536-dim, cosine), but *which* articles each tenant sees and *how* those articles are turned into delivered content is driven by two parallel personalization stacks that share a single 10-dimensional content taxonomy:

```
llms · ai_agents · computer_vision · security · hardware ·
software_engineering · ai_policy · general_ai · data_engineering · startups
```

Every user persona and every company profile is mapped onto this same 10-slot probability distribution. That shared shape is what lets the retrieval layer stay untouched while the downstream generation layer knows exactly *which vocabulary* to pull from for a given tenant.

### B2C newsletter — user-persona driven

**Inputs maintained per user** (`user_personas` in Snowflake):
- `explicit_category_weights` — captured at onboarding from a LinkedIn PDF (LLM extractor) or a manual chip-picker. This is a hard distribution over the 10 categories.
- `behavioral_category_weights` — drifts with every like / dislike / skip the user fires on their feed. Starts at the explicit vector and diffuses from there.
- `job_title`, `seniority`, `persona_archetype`, `bio_summary` — free-text persona fields that the extractor fills in once.

**Blend applied before retrieval** (`SearchService.get_personalized_recommendations`):
```
weights[c] = explicit[c] × 0.80 + behavioral[c] × 0.20     # P4 blend
weights    = { c: w for c, w in weights if w >= 0.05 }     # noise prune
```
The blended weights are concatenated with the free-text persona fields to build a semantic query. That query is embedded with `text-embedding-3-small` and issued against Qdrant; results are then date-scoped by joining `articles_raw.published_at` within a 2-day window around the edition date.

**Why it differentiates:** a Security Engineer and a Data Engineer produce sharply orthogonal query vectors — one leans on `security + ai_policy + software_engineering` plus the phrase "Senior Security Engineer", the other leans on `data_engineering + llms + general_ai` plus "Staff Data Engineer". The Qdrant returns don't overlap much, and because the B2C agent *renders the retrieved article list directly* into the newsletter, those differences are visible to the reader without the LLM needing to interpret anything.

**Behavioral loop closes the drift:** every like on a `llms`-heavy article nudges `behavioral[llms]` up; the next day's blended query has slightly more mass on LLMs. Nothing prescriptive — the system just tracks where the user's attention goes.

### B2B Strategic Brief — company-affinity driven (the new one)

The symmetric problem: different company tenants (a dev-tools vendor, a fintech-fraud vendor, an investment-research firm) should get visibly different daily briefs. The original implementation dumped every profile free-text field into one long semantic query, and the downstream LLM collapsed the distinct retrieval into tenant-voice boilerplate — briefs read alike across tenants even though the retrieval ranked different articles.

**The fix: give companies the same 10-dim taxonomy vector that users have, and inject it into the generation prompt as a hard constraint.**

**Inputs maintained per tenant** (`companies` in Snowflake):
- Rich text profile — `name`, `industry`, `description`, `target_audience`, `key_products`, `content_pillars`, `competitors`, `tone_of_voice`. All ten fields are mandatory (422 on missing).
- **`content_affinity_weights VARIANT`** (new) — the 10-dim distribution over the same taxonomy used by personas, extracted by an LLM call every time the profile is created or updated. Populated by `app.services.company_affinity.extract_company_affinity`.

**How the vector shapes the brief** (`b2b_agent.build_strategic_brief`):

```
DOMINANT CATEGORIES = top-3 categories with weight ≥ 0.10
ZERO-WEIGHT CATEGORIES = all categories with weight < 0.05

Prompt hard constraints:
  1. Every editorial_title MUST reference at least one DOMINANT category
     using the tenant's own vocabulary (not the raw taxonomy token).
  2. ≥3 of primary_keywords MUST be phrases a practitioner in the DOMINANT
     category would actually search for.
  3. DO NOT reference ZERO-WEIGHT categories anywhere in the output.

Temperature bumped from 0.0 → 0.4 so day-to-day briefs don't collapse
into identical prose when the retrieved anchor changes.
```

The top retrieved article for that specific `brief_date` is marked as a mandatory **primary anchor** in the prompt — `headline` and `blue_ocean_angle` must be framed around that specific development. Supporting signals are explicitly labeled as *context only*. That's what keeps the same tenant's 2026-04-22 brief distinct from its 2026-04-18 brief.

**How the two stacks are orthogonal in practice:**

Take three very different tenants that all ingest from the same Qdrant pool:

| Tenant | Dominant 10-dim axes | What ends up in the brief |
|---|---|---|
| **TechCorp Inc.** (AI dev tooling) | `llms 0.40 · software_engineering 0.30 · ai_agents 0.20` | Headlines about IDE copilots, CI/CD agents, code-review automation |
| **Ledgerwise AI** (fintech fraud + BSA/AML) | `startups 0.70 · security 0.20 · ai_policy 0.10` | Headlines about Neobanks, payment fraud, BSA/AML compliance |
| **Meridian Capital Research** (hedge-fund alpha) | `llms 0.50 · data_engineering 0.20 · software_engineering 0.10 · general_ai 0.10 · startups 0.10` | Headlines about equity research, earnings-call NLP, portfolio construction |

TechCorp's vector has **zero** mass on `security` and `ai_policy` — the prompt forbids the LLM from mentioning either. Ledgerwise has **zero** mass on `software_engineering` and `hardware` — those stay out of its briefs entirely. The vectors are close to *orthogonal* in the category space; the forbidden-category list enforces it at generation time.

**Validation (prototype — `Prototyping/SEO_Personalized/prototype.py`):**

Pairwise cosine similarity of the *generated brief text* (headline + blue-ocean angle + editorial titles + keywords + content structure + linking strategy), across three cross-vertical tenants on 5 consecutive days of real Qdrant + Snowflake data:

|  | OLD prompt (pre-affinity) | NEW prompt (affinity injected, temp 0.4) | Δ |
|---|---|---|---|
| Cross-tenant same-date mean | **0.6034** | **0.5243** | **−0.0790** (sharper) |
| Same-tenant cross-date mean | 0.9690 | 0.9473 | −0.0218 |

Cross-tenant divergence improved on *every* tested date. Biggest gain was the hardest pair (fintech vs investment research, both finance-adjacent) where inter-tenant cosine dropped from 0.61 → 0.46.

**Where each piece lives:**
- Taxonomy definition — [`backend/app/core/schemas.py`](backend/app/core/schemas.py) (`CategoryWeights`, `CompanyContentAffinity`)
- User blend + query build — [`backend/app/services/search.py`](backend/app/services/search.py)
- Company affinity extractor — [`backend/app/services/company_affinity.py`](backend/app/services/company_affinity.py)
- Brief generator with affinity injection — [`backend/app/services/b2b_agent.py`](backend/app/services/b2b_agent.py) (`build_strategic_brief`)
- Extractor hook on profile save — [`backend/app/api/admin.py`](backend/app/api/admin.py) (`create_company`, `update_company`)
- Read-only UI chip row — [`frontend/src/app/company/profile/page.tsx`](frontend/src/app/company/profile/page.tsx) (`AffinityChips`)

## Feature walk-through

### B2C (individual readers)

1. **Onboarding** (`/user/onboarding`) — upload one or more PDFs (LinkedIn export, resume). An LLM extracts a structured persona with a 10-category weight vector and one of six archetypes.
2. **Persona inspector** (`/user/persona`) — see the explicit weights captured at onboarding alongside the behavioral weights that drift from feedback. Toggle "Update Interests" to edit bio + category picks in place.
3. **My Feed** (`/user`) — personalized article feed driven by `SearchService.get_personalized_recommendations`. Each row has like / dislike / skip buttons; the signal flows through `/personas/feedback` and updates the persona in-place. First paint renders a pulsing skeleton, not the empty-state copy.
4. **Newsletter** (`/newsletter`) — renders the actual email HTML the user would receive (via `GET /api/v1/newsletter/preview`) in a sandboxed iframe. For today's edition the HTML is generated on-the-fly from fresh Qdrant data; past dates serve the stored copy. The B2C LangGraph runs in two modes: `fast` (skeleton render, lower latency) and `polished` (full multi-node generation with an editor review step). The traversal path is recorded in `newsletters.execution_path_taken` for debugging divergence between modes. A date picker flips between today's preview and the archive of past editions. One explicit **Send to My Inbox** button dispatches via MailerSend; it's idempotent per `(user_id, edition_date)` and disables once `sent_at` is stamped. There is no auto-email on generate — delivery is always a manual user or admin action.
5. **Newsletter archive** (`/user/newsletters`) — paginated list of all past editions for the logged-in user with per-edition send status.

### B2B (corporate tenants)

1. **Strategic Drafts** (`/company/drafts`) — the B2B LangGraph (init → intel_extract → brief_build → render_markdown). The agent scores cross-cluster signals with the 3-signal urgency algorithm (relevance 40 % + velocity 30 % + competition gap 30 %), calls the LLM with a Pydantic-structured `StrategicBrief` response format, cross-joins SpaCy keyword velocity, and pulls reference sources from `articles_raw`. The frontend renders the structured payload (Blue Ocean angle, editorial titles, primary keyword velocity table, detailed content structure, internal linking strategy, reference sources) in the layout from `Temp/SEO_Prototype/UI/index.html`; the raw Markdown brief is kept in a collapsible `<details>`. A **Regenerate** button reruns the agent for today (`?force=true`) so stale briefs can be rebuilt without waiting on the scheduled DAG.
2. **Keyword Velocity** (`/company/trends`) — SpaCy-driven entity velocity table with SURGING / STABLE / DECLINING tags.
3. **Company Profile** (`/company/profile`) — edits the 10 tenant fields used by the Strategic Brief agent: name, domain, industry, description, company size, target audience, key products, content pillars, competitors, and tone of voice (enum). Toggle-edit pattern mirrors the user persona page; all fields are mandatory and validated by the backend (422 on missing).

### Admin

1. **Admin Console** (`/admin`) — system health, high-velocity clusters, user/company totals, live Prometheus metrics, and the Admin Management panel (create user, create company, trigger pipeline).
2. **Global Trends** (`/admin/trends`) — full ranked cluster table with data-reliability ratio.
3. **Distribution Archive** (`/admin/newsletters`) — cross-tenant newsletter archive with date filter (defaults to yesterday); supports batch **Send All** dispatch (concurrency capped at 5 to respect MailerSend quota).
4. **Editorial Review** (`/admin/newsletters/review`) — HITL approval UI for drafts.
5. **User Directory** (`/admin/users`) — list, create, and edit all B2C users; updates persona fields and category weights in-place.
6. **Company Directory** (`/admin/companies`) — list, create, and edit all B2B tenant profiles; saving a profile triggers affinity re-extraction automatically.

### Data pipelines (Airflow)

| DAG | Schedule | Does |
|---|---|---|
| `ingestion_dag` | 10:30 UTC daily | Parallel fan-out (RSS ∥ ArXiv ∥ HN) → MERGE into `articles_raw` → invalidate cache |
| `deduplication_dag` | @hourly | URL + semantic dedup → `article_clusters` + Qdrant upsert |
| `trend_dag` | 10:50 UTC daily | Bulk re-rank clusters with 4-tier status (BREAKING / TRENDING / VIRAL / COMMUNITY-PICK / REGULAR) |
| `qdrant_sync_dag` | 11:05 UTC daily | Re-embed every live cluster and bulk-upsert into Qdrant `articles`, so the vector store stays in sync with Snowflake after merges / backfills |
| `b2c_personalization_dag` | 11:20 UTC daily | Fan-out — top-10 personalised clusters per user → `daily_selections` |
| `b2c_newsletter_dag` | 11:50 UTC daily | Fan-out — one newsletter per user, persisted to `newsletters`. No auto-email; send is a manual user/admin action. |
| `b2b_seo_dag` | manual (+ `{"company_id": "…"}` conf) | Fan-out — one structured brief per company, persisted to `content_briefs.structured_brief` |
| `behavioral_refinement_dag` | @weekly (paused in demo) | P4 rollup — decay + merge 7d of feedback events into `behavioral_category_weights`; boosts liked categories, decays skipped ones |

All per-user / per-company DAGs accept `dag_run.conf={"user_id": "…"}` / `{"company_id": "…"}` for on-demand targeted runs.

## Testing

### Backend

```bash
cd backend
uv run pytest tests/unit -q    # 38 tests, offline (Snowflake + OpenAI mocked)
uv run pytest tests/           # full suite (includes MCP e2e)
```

### Frontend

```bash
cd frontend
npm test -- --run              # 59 Vitest tests (MSW for backend mocking)
npm run lint
npx tsc --noEmit
```

### DAGs

Ad-hoc trigger via the Airflow UI or REST API:

```bash
curl -u admin:$AIRFLOW_PASSWORD \
  -X POST -H 'Content-Type: application/json' -d '{}' \
  http://<vm-ip>:8080/api/v1/dags/ingestion_dag/dagRuns
```

Or through the backend (which just forwards):

```bash
curl -X POST https://curateai-backend-sjhg7huf4q-uc.a.run.app/api/v1/ingestion/fetch-rss
```

### CI

Every PR runs GitHub Actions:
- `lint.yml` — ruff (backend), tsc + eslint (frontend)
- `test.yml` — pytest (backend), vitest (frontend), DAG AST parse
- `deploy.yml` — manual workflow dispatch to trigger Cloud Build

## Observability

| Signal | Where |
|---|---|
| Structured JSON logs | Cloud Logging (backend) + `docker compose logs` (Airflow VM) |
| Prometheus metrics | `GET /metrics` (raw text) and `GET /api/v1/metrics/summary` (JSON snapshot) |
| Live admin panel | `/admin` — polls `/api/v1/metrics/summary` every 10 s |
| HTTP latency | `curateai_http_request_duration_seconds` histogram |
| LLM cost + tokens | `curateai_llm_cost_total`, `curateai_llm_tokens_total` |
| LangGraph node latency | `curateai_langgraph_node_latency_seconds` (B2B + B2C instrumented) |
| DAG triggers | `curateai_dag_triggers_total{status}` + `curateai_dag_trigger_latency_seconds` |
| Agent reliability | `curateai_newsletter_rejections_total` — editor rejecting drafts |
| B2C execution path | `newsletters.execution_path_taken` column — records which LangGraph nodes fired per edition (fast vs polished divergence) |

## MCP integration

The backend mounts a FastMCP server at `/api/v1/mcp` (SSE transport) so Claude Desktop or any MCP client can call:

| Tool | Purpose |
|---|---|
| `health_check_mcp` | heartbeat |
| `get_user_archetype(user_id)` | return the persona archetype |
| `filter_articles(user_id, category?, limit)` | personalised recommendations with optional category filter |
| `get_keyword_trends(limit, status?, date?)` | ranked cluster snapshot with optional date and status filter |
| `get_common_highlights(date?, limit)` | universal trending articles across all tenants for a given date |
| `generate_user_newsletter(user_id, mode)` | run the B2C graph and return rendered HTML (`fast` or `polished` mode) |
| `generate_b2b_brief(company_id, date?)` | run the B2B graph and return Markdown for a specific date |

Claude Desktop config:

```json
{
  "mcpServers": {
    "curateai": {
      "url": "https://curateai-backend-sjhg7huf4q-uc.a.run.app/api/v1/mcp/sse"
    }
  }
}
```

## Architecture decisions

### Why LangGraph for both verticals

Two distinct graphs (B2C writer/editor, B2B analyst) share the same `AgentState` shape and a common `BaseAgentService` for LLM calls. This keeps the retry / cost-tracking / prompt-caching wiring in one place while letting each vertical diverge in node topology. The shared `track_node_latency` decorator in `app/services/agent_base.py` feeds every node's duration into a single Prometheus histogram so a Grafana panel can compare `curate` against `intel_extract` side-by-side.

### Why Airflow on a VM instead of Composer

Composer's floor is ~$350/month for a workload that fits in 8 GB of RAM. An `e2-standard-2` VM costs ~$48/month at full utilisation; stopped between demo sessions it's ~$0.12/day. We run Postgres (metadata), the scheduler, the webserver, and local Qdrant (for fallback) all under one docker-compose file. The backend is env-configured (`AIRFLOW_HOST`) so a redeploy wires it up automatically.

### Why URL + semantic dedup, not just one or the other

URL dedup is O(n) and catches ~80 % of duplicates coming from syndicated feeds. Semantic dedup uses OpenAI `text-embedding-3-small` + cosine similarity at a 0.75 threshold and catches the rest (articles republished under different paths, wire stories rewritten per publisher). Doing semantic-only would be ~4× the embedding cost; URL-only would let through roughly 1 in 5 duplicates.

### Why Qdrant Cloud instead of a self-hosted instance

The deduplication service + search service need identical embeddings across backend and Airflow. Running Qdrant on the VM plus Qdrant on Cloud Run would drift. A managed, externally reachable Qdrant is one less thing to keep in sync. Qdrant's free tier covers our workload (~10 k points, single collection).

### Why Snowflake, not Postgres

Two reasons: (a) Snowflake's VARIANT columns let us store evolving category-weight JSON blobs without ALTER migrations every time we add a label; (b) the analytical reads (trend ranking, daily selections aggregation) benefit from a columnar engine. The team-provided credentials also made this a zero-cost choice.

### Why "paused by default" for some DAGs

The daily pipeline fires as a **staggered chain starting 10:30 UTC** (6:30 AM EDT): ingestion → trend → qdrant_sync → b2c_personalization → b2c_newsletter, with a ~15–30 minute gap between steps so each upstream DAG has time to settle before the next consumes its output. `deduplication_dag` runs **@hourly** continuously to keep clustering reactive to fresh articles. `behavioral_refinement_dag` is **@weekly**. `b2b_seo_dag` is manual-only (trigger from the UI or via `dag_run.conf = {"company_id": "..."}`) since brief generation is user-driven, not time-driven.

### Why a thin backend for pipelines, not inline execution

The backend's pipeline endpoints (`/ingestion/fetch-rss`, `/deduplication/process`, `/trend/rank`) used to run the full pipeline synchronously. Cloud Run's per-request timeout would kill ingestion in the middle of the 3 000-article MERGE. Moving those pipelines to Airflow gave us retries, idempotency, observability, and a real audit trail — the backend call is now a 100 ms trigger that returns a `dag_run_id`.

## Known limitations

- **Auth is stubbed out.** Admin CRUD endpoints are publicly reachable on Cloud Run. Before any real launch, wire a real auth layer (IAP / Clerk / Auth0) and gate `admin/*` behind it.
- **LangGraph dependency pin drift.** Backend is on langgraph `1.1.6`; Airflow's image ships with the same pin but the Airflow base image ships pydantic `2.7`, while the backend happily runs on pydantic `2.10+`. If the scheduler starts failing on import, rebuild the Airflow image.
- **No request-level authZ for MCP tools.** Any MCP client can invoke `generate_b2b_brief(company_id=…)` for any company id. Fine for a demo, not for production.
- **Qdrant collection has no schema validation.** Payloads are trusted. A misbehaving backfill script could poison the collection with malformed payloads and the recommender would silently return garbage.
- **Cost visibility is model-level, not prompt-level.** `curateai_llm_cost_total{model}` tracks spend per model but not per user / per archetype.
- **Rate limits are coarse and not per-user.** `/ingestion/fetch-rss` is capped at 2/min, `/personas/extract` at 5/min, `/personas/feedback` at 30/min, and `/b2b/report` at 10/min — all global, not scoped per user or API key. A determined tester can still flood the DAG queue.
- **Newsletter archive doesn't paginate beyond the initial 10.** The frontend calls `?limit=10` with no offset control.
- **No GitHub Actions-driven auto-deploy to prod.** Deploys are manual (`gcloud builds submit`) or workflow_dispatch-triggered — deliberate until we add staging environments.

## Access, permissions, secrets

| Secret | Where | Rotated via |
|---|---|---|
| `SECRET_KEY` (session signing) | GCP Secret Manager | `gcloud secrets versions add SECRET_KEY --data-file=-` |
| `SNOWFLAKE_PASSWORD` | Secret Manager | Snowflake UI + rotate Secret Manager version |
| `OPENAI_API_KEY` | Secret Manager | OpenAI dashboard |
| `QDRANT_API_KEY` | Secret Manager | Qdrant Cloud console |
| `AIRFLOW_PASSWORD` | Secret Manager | `airflow users create --password …` on the VM + new Secret Manager version |
| `AIRFLOW_FERNET_KEY` | VM `.env` | rotate = re-encrypt the Airflow metadata DB; do not rotate casually |

Service accounts:
- `curateai-backend-sa` — Cloud Run backend. Has `secretmanager.secretAccessor` on all of the above.
- `curateai-frontend-sa` — Cloud Run frontend. No secret access.
- Cloud Build default SA — used by CI, deploys through `cloudbuild.yaml`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Frontend stat cards show "Health probe failed" | Backend CORS doesn't include the frontend origin | `gcloud run services update curateai-backend --update-env-vars CORS_ORIGINS=…` |
| `/api/v1/ingestion/fetch-rss` returns 503 with `AIRFLOW_HOST is not configured` | The VM is stopped or `AIRFLOW_HOST` is blank | `gcloud compute instances start curateai-airflow` + verify the env var |
| Airflow 403 `PermissionDenied` on REST calls | Basic auth credentials don't match Secret Manager | `airflow users reset-password -u admin` on the VM, update `AIRFLOW_PASSWORD` secret |
| DAG succeeds but writes nothing | Qdrant collection empty or wrong URL | Check `curateai_airflow_scheduler` env for `QDRANT_URL`, then run the dedup DAG once |
| Persona archetype column missing | Fresh Snowflake schema without ALTER | `ALTER TABLE user_personas ADD COLUMN IF NOT EXISTS persona_archetype VARCHAR(100)` |
| Newsletter generation returns empty HTML | Search service returned no Qdrant hits | Run `deduplication_dag` to re-populate Qdrant |

## License + credits

Academic project — Northeastern University DAMG 7245 Spring 26 Team 1 (Aakash Belide, Abhinav KumarPiyush, Rahul Bothra). LLMs via LiteLLM / OpenAI. Framework credits: FastAPI, Next.js, LangGraph, Apache Airflow, Snowflake, Qdrant.