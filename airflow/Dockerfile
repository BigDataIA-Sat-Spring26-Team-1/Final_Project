# Airflow runtime image for CurateAI.
#
# We intentionally pin the base image so a scheduler restart on the VM doesn't
# silently pick up a breaking Airflow upgrade. ``apache-airflow`` is installed
# via the base image; requirements-airflow.txt lists only the extra packages
# the backend services need at runtime (LiteLLM, LangGraph, Snowflake driver).
FROM apache/airflow:2.9.1-python3.12

USER root
# curl powers the healthcheck in docker-compose; the base image lacks it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY --chown=airflow:root airflow/requirements-airflow.txt /tmp/requirements-airflow.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements-airflow.txt

# Backend source is bind-mounted at runtime (see docker-compose.vm.yml) so DAGs
# can ``from app.services.* import ...`` without a duplicate install.
