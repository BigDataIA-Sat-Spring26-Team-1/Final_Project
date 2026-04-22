# Airflow on a GCP Compute Engine VM

The CurateAI backend (Cloud Run) delegates every long-running pipeline — ingestion, deduplication, ranking, newsletter / brief generation, behavioral rollup — to Airflow DAGs that live on a dedicated GCP VM. This directory holds the DAG files, the Airflow image, and the Compose stack that runs them.

## Architecture

```
 Browser ─► Next.js (Cloud Run)
                │
                ▼
           FastAPI (Cloud Run)  ──► Snowflake + Qdrant Cloud
                │
                │   POST /api/v1/dags/{id}/dagRuns
                ▼
         Airflow on GCP VM
           ├─ webserver  (:8080, REST API + UI)
           ├─ scheduler  (LocalExecutor)
           └─ postgres   (metadata DB)
```

Snowflake and Qdrant are **external** to the VM — Airflow tasks connect to them over the public network using the same credentials the backend uses.

## One-time VM setup

```bash
# 1. Pick or create the VM. e2-standard-2 is plenty for this workload.
gcloud compute instances create curateai-airflow \
  --zone=us-central1-a \
  --machine-type=e2-standard-2 \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=50GB \
  --tags=http-server,https-server

# 2. Allow the backend's egress IP (or the whole Cloud Run range) to reach :8080.
#    Narrow this down in production — default allows any source.
gcloud compute firewall-rules create curateai-airflow-ui \
  --allow=tcp:8080 \
  --target-tags=http-server \
  --source-ranges=0.0.0.0/0

# 3. SSH in and install Docker + Compose.
gcloud compute ssh curateai-airflow --zone=us-central1-a
#   on the VM:
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER && exec su -l $USER
```

## Deploying the stack

From the VM, clone the repo and drop a `.env` at the root:

```bash
git clone https://github.com/BigDataIA-Sat-Spring26-Team-1/Final_Project.git
cd Final_Project

# .env — same shape as the backend uses. Required keys:
#   SECRET_KEY, SNOWFLAKE_* , OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY
#   AIRFLOW_FERNET_KEY          (python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
#   AIRFLOW_ADMIN_USERNAME      (defaults to "admin")
#   AIRFLOW_ADMIN_PASSWORD      (rotate from the default before going live)
#   AIRFLOW_ADMIN_EMAIL
nano .env

docker compose -f infrastructure/docker-compose.vm.yml up -d airflow-init
docker compose -f infrastructure/docker-compose.vm.yml up -d qdrant postgres airflow-webserver airflow-scheduler
docker compose -f infrastructure/docker-compose.vm.yml ps
```

The `all-in-one` profile also includes a local FastAPI backend container — skip it on the VM, that lives on Cloud Run.

## Wiring Cloud Run → VM

Once Airflow is up, point the backend at it and redeploy:

```bash
VM_IP=$(gcloud compute instances describe curateai-airflow \
  --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

gcloud run services update curateai-backend \
  --region=us-central1 \
  --update-env-vars="AIRFLOW_HOST=http://${VM_IP}:8080,AIRFLOW_USERNAME=admin" \
  --update-secrets="AIRFLOW_PASSWORD=AIRFLOW_PASSWORD:latest"
```

Store the admin password in Secret Manager first:

```bash
echo -n 'the-real-password' | gcloud secrets create AIRFLOW_PASSWORD --data-file=-
gcloud secrets add-iam-policy-binding AIRFLOW_PASSWORD \
  --member=serviceAccount:curateai-backend-sa@gen-lang-client-0720834968.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

## Smoke test

From any machine with the backend URL:

```bash
curl -i -X POST https://curateai-backend-sjhg7huf4q-uc.a.run.app/api/v1/ingestion/fetch-rss
```

Expected: `202 Accepted` with a body like

```json
{
  "status": "ACCEPTED",
  "dag_id": "ingestion_dag",
  "dag_run_id": "manual__2026-04-21T17:42:11+00:00",
  "state": "queued"
}
```

Follow the run in the Airflow UI at `http://<vm-ip>:8080` (`admin` / the password you set).

## Day-2 ops

| Action | Command |
|---|---|
| Tail scheduler logs | `docker compose -f infrastructure/docker-compose.vm.yml logs -f airflow-scheduler` |
| Restart webserver | `docker compose -f infrastructure/docker-compose.vm.yml restart airflow-webserver` |
| Update DAG code | `git pull` in `~/Final_Project`; the scheduler picks up changes automatically (dags volume is bind-mounted) |
| Rotate admin pw | `docker exec -it curateai_airflow_webserver airflow users reset-password -u admin` |

## Troubleshooting

* **`503` from the backend**: `AIRFLOW_HOST` is blank or unreachable. `curl http://<vm-ip>:8080/health` from a shell with the same network path.
* **DAG import errors**: the scheduler mounts `backend/` read-only at `/opt/airflow/backend`. If a DAG raises `ModuleNotFoundError: app.services`, make sure `CURATEAI_BACKEND_PATH` matches the mount (the default is already correct).
* **Snowflake connection refused**: the VM needs an egress IP on Snowflake's allowlist; check `SNOWFLAKE_ACCOUNT` in `.env`.
