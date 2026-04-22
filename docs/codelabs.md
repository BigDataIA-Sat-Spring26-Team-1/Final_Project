---
id: curateai-codelab
summary: Build, deploy, and operate CurateAI — a multi-tenant AI news intelligence platform on GCP, Snowflake, Qdrant, Airflow, FastAPI, and Next.js.
categories: data-engineering,llm,production-ml
tags: langgraph,airflow,cloud-run,snowflake,qdrant,fastapi,nextjs,prometheus,mcp
status: draft
authors: Team 1 (Aakash Belide, Abhinav Piyush, Rahul Singh)
feedback link: https://github.com/BigDataIA-Sat-Spring26-Team-1/Final_Project/issues
---

# CurateAI: From Zero to a Multi-Tenant AI News Platform

## 1. What you'll build

Duration: 0:03:00

By the end of this codelab you'll have a running version of CurateAI —

- A FastAPI backend that serves a personalised news feed, runs LangGraph agents for newsletter + research-brief generation, and exposes an MCP tool surface.
- A Next.js frontend with admin console, persona editor, trend dashboards, and a live Prometheus panel.
- Seven Airflow DAGs orchestrating a 3 000-article/day ingestion → deduplication → ranking → personalization → delivery pipeline.
- A Snowflake warehouse + Qdrant Cloud vector index storing article clusters, personas, newsletters, and content briefs.
- GitHub Actions CI that lints, tests, and can deploy everything to Cloud Run via Cloud Build.

### Architecture you'll touch

```
Browser ─► Next.js (Cloud Run)
              │
              ▼
       FastAPI (Cloud Run) ──► Snowflake + Qdrant Cloud + OpenAI
              │
              │  triggers DAGs
              ▼
   Airflow on GCE VM ──► Snowflake + Qdrant + OpenAI
```

### Learning goals

- Designing LangGraph agents with shared state
- Orchestrating async pipelines on Airflow triggered from a stateless API
- URL + semantic deduplication with Qdrant
- Multi-tenant persona modelling with dynamic weight updates
- Exposing the same tools via REST and MCP
- Production observability with Prometheus + structured logging

### Prerequisites

- Python 3.12
- Node 22
- Docker Desktop
- [uv](https://docs.astral.sh/uv/)
- GCP project with billing enabled (for the prod-deploy section only)
- Snowflake trial account (or the provided team credentials)
- OpenAI API key

## 2. Clone and bootstrap

Duration: 0:05:00

```bash
git clone https://github.com/BigDataIA-Sat-Spring26-Team-1/Final_Project.git
cd Final_Project
cp .env.example .env    # fill in the blanks — see README for the key list
```

Install deps:

```bash
# Backend
cd backend
uv sync --extra test

# Frontend
cd ../frontend
npm install
```

Positive
: `uv sync --extra test` reads `uv.lock`, so everyone on the team gets the exact same dependency tree. Don't use `pip install`.

## 3. Run the backend

Duration: 0:05:00

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` — you should see the OpenAPI doc with routers for Personas, Ingestion, Deduplication, Trend Engine, Search, B2B, Newsletter, Admin, and System.

Smoke test the health endpoint:

```bash
curl http://localhost:8000/api/v1/health
# {"status":"healthy","app_name":"Curate AI",...}
```

If you see a 503 here, Snowflake auth failed — double-check `.env`.

## 4. Inspect the persona agent

Duration: 0:05:00

Open [`backend/app/services/b2c_agent.py`](backend/app/services/b2c_agent.py). Note five things:

1. Every node is decorated with `@track_node_latency` — Prometheus histogram per node name.
2. The state is a plain `TypedDict` shared with the B2B graph.
3. The editor node can *reject* a draft and route back to `write_content` (a conditional edge in LangGraph).
4. The writer LLM call goes through `BaseAgentService.call_llm`, which in turn uses `litellm` so we never hard-code a model name.
5. `execution_mode == "fast"` skips the editor node entirely for demos.

Run an in-process graph execution:

```python
from app.services.b2c_agent import get_b2c_newsletter_graph
import asyncio

graph = get_b2c_newsletter_graph()
out = asyncio.run(graph.ainvoke({"user_id": "<some-real-user-id>", "execution_mode": "fast"}))
print(out["generated_content"][:500])
```

## 5. Start the frontend

Duration: 0:04:00

```bash
cd frontend
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local
npm run dev
```

Open `http://localhost:3000`. Navigate to **Admin Console** → **Live Prometheus Metrics** should show your single health-check request in the "HTTP endpoint latency" chart.

## 6. Wire up Airflow (optional for local dev)

Duration: 0:12:00

If you want the full ingestion → delivery pipeline locally:

```bash
docker compose -f infrastructure/docker-compose.vm.yml up -d airflow-init
docker compose -f infrastructure/docker-compose.vm.yml up -d \
  qdrant postgres airflow-webserver airflow-scheduler
```

Wait ~60 seconds for the webserver healthcheck, then open `http://localhost:8080` (admin / the password from your `.env`'s `AIRFLOW_ADMIN_PASSWORD`).

Point the backend at local Airflow:

```bash
# .env
AIRFLOW_HOST=http://localhost:8080
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=<your AIRFLOW_ADMIN_PASSWORD>
```

Restart the backend and hit `POST /api/v1/ingestion/fetch-rss` — you should get a 202 with a `dag_run_id`, and the Airflow UI should show the run go from queued → running → success.

## 7. Tour the DAGs

Duration: 0:07:00

Open [`airflow/dags/ingestion_dag.py`](airflow/dags/ingestion_dag.py). Observe:

- The three crawlers run **in parallel** (`[t_rss, t_arxiv, t_hn] >> t_persist`). This is the cheapest 3× throughput win.
- `persist_articles` pulls each crawler's XCom payload and unions them before the Snowflake MERGE.
- `invalidate_caches` is the only downstream task — it clears the archetype cache so personalization sees fresh data on the next request.

Per-user / per-company DAGs (`b2c_newsletter_dag`, `b2b_seo_dag`, `b2c_personalization_dag`) accept `dag_run.conf = {"user_id": "..."}` so the backend can target specific tenants on demand.

Positive
: Design idea worth stealing: every DAG runs in two modes. Scheduled (fan-out over every user) or on-demand (conf targets one user). Same task graph, same code — just different entry-point behaviour.

## 8. Add a new MCP tool

Duration: 0:05:00

The MCP server is at [`backend/app/core/mcp_server.py`](backend/app/core/mcp_server.py). Tools are just decorated async functions. Add one:

```python
@mcp_server.tool()
async def count_clusters_by_status() -> dict[str, int]:
    """Return a histogram of trend_status values across all ranked clusters."""
    db_gen = get_db_connection()
    db = next(db_gen)
    try:
        cur = db.cursor()
        cur.execute(
            "SELECT UPPER(trend_status), COUNT(*) FROM article_clusters GROUP BY 1"
        )
        return {row[0] or "NULL": int(row[1]) for row in cur.fetchall()}
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
```

Restart the backend. The tool shows up in any MCP client connected to `http://localhost:8000/api/v1/mcp/sse`.

## 9. Ship to Cloud Run

Duration: 0:10:00

The project ships two Cloud Build configs:

- [`infrastructure/backend.cloudbuild.yaml`](infrastructure/backend.cloudbuild.yaml) — builds the backend image, pushes to Artifact Registry, deploys to Cloud Run with the right secrets bound.
- [`infrastructure/frontend.cloudbuild.yaml`](infrastructure/frontend.cloudbuild.yaml) — builds the frontend image with `NEXT_PUBLIC_API_URL` baked in, deploys to Cloud Run.

Manual deploy:

```bash
gcloud builds submit \
  --config=infrastructure/backend.cloudbuild.yaml .

gcloud builds submit \
  --config=infrastructure/frontend.cloudbuild.yaml \
  --substitutions=_BACKEND_URL=<backend Cloud Run URL> .
```

CI-driven deploy (from GitHub):

1. Actions → **deploy** → Run workflow → pick `backend`, `frontend`, or `both`.
2. Provide secrets via GitHub repo secrets: `GCP_PROJECT_ID`, `GCP_SA_KEY` (JSON key of a service account with `roles/cloudbuild.builds.editor`), `BACKEND_URL`.

## 10. Stand up Airflow on a GCE VM

Duration: 0:15:00

```bash
gcloud compute instances create curateai-airflow \
  --zone=us-central1-a \
  --machine-type=e2-standard-2 \
  --image-family=debian-12 --image-project=debian-cloud \
  --boot-disk-size=30GB --boot-disk-type=pd-balanced \
  --tags=curateai-airflow

gcloud compute firewall-rules create curateai-airflow-ui \
  --allow=tcp:8080 --target-tags=curateai-airflow \
  --source-ranges=0.0.0.0/0
```

SSH in, install Docker, clone, drop `.env`, `docker compose up -d`. Full details live in [`airflow/README.md`](airflow/README.md).

Wire Cloud Run backend to the VM:

```bash
VM_IP=$(gcloud compute instances describe curateai-airflow \
  --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

gcloud run services update curateai-backend \
  --region=us-central1 \
  --update-env-vars="AIRFLOW_HOST=http://${VM_IP}:8080,AIRFLOW_USERNAME=admin" \
  --update-secrets="AIRFLOW_PASSWORD=AIRFLOW_PASSWORD:latest"
```

## 11. Run the test suites

Duration: 0:04:00

```bash
# Backend
cd backend && uv run pytest tests/unit -q         # 38 tests

# Frontend
cd frontend && npm test -- --run                 # 59 tests

# DAG syntax (no airflow install needed)
python -c "
import ast, pathlib
for p in pathlib.Path('airflow/dags').glob('*.py'):
    ast.parse(p.read_text())
    print('OK', p.name)
"
```

All three suites gate the GitHub Actions `test` workflow.

## 12. Observability

Duration: 0:03:00

- `GET /metrics` — raw Prometheus text.
- `GET /api/v1/metrics/summary` — pre-aggregated JSON used by the frontend panel.
- Admin Console → Live Prometheus Metrics — auto-refreshes every 10 s.

Useful labels to filter on when you wire this into Grafana:

| Metric | Label set |
|---|---|
| `curateai_http_request_duration_seconds` | `method`, `endpoint` |
| `curateai_llm_cost_total` | `model` |
| `curateai_langgraph_node_latency_seconds` | `node_name` |
| `curateai_dag_triggers_total` | `dag_id`, `status` (accepted / rejected) |

## 13. Known gotchas

Duration: 0:02:00

- `docker compose` YAML interpolates `${VAR}` against the **shell** env, not `env_file`. Escape with `$$VAR` when you want the container to resolve it at runtime.
- Snowflake's `ALTER COLUMN ... DEFAULT CURRENT_TIMESTAMP()` is rejected — set the column without a default, then backfill.
- Airflow's `airflow.api.auth.backend.session` requires CSRF tokens; add `basic_auth` to `AIRFLOW__API__AUTH_BACKENDS` for REST automation.
- `airflow dags unpause <id>` only works once the scheduler has parsed the DAG — wait ~30 s after `git pull`ing new DAG code.

## 14. Where to go next

Duration: 0:01:00

- Add an auth layer: drop IAP in front of Cloud Run and scope the admin routes.
- Wire Prometheus scraping to Grafana Cloud and replicate the metrics panel at a dashboard level.
- Replace the weekly `behavioral_refinement_dag` manual tuning with a bandit algorithm per user.
- Add a B2B MCP tool for `compare_companies(ids: list[str])` that emits a side-by-side intelligence diff.
- Move OpenAI key to per-tenant via LiteLLM's virtual-key routing.

## 15. Cleanup

Duration: 0:02:00

```bash
# Stop the VM to cut cost to ~$0.12/day
gcloud compute instances stop curateai-airflow --zone=us-central1-a

# Or nuke the demo entirely
gcloud compute instances delete curateai-airflow --zone=us-central1-a
gcloud compute firewall-rules delete curateai-airflow-ui
gcloud secrets delete AIRFLOW_PASSWORD
gcloud run services delete curateai-backend --region=us-central1
gcloud run services delete curateai-frontend --region=us-central1
```

That's it. For architecture rationale, known limitations, and secret rotation policy, see [`README.md`](../README.md).
