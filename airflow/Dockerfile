FROM apache/airflow:2.9.1-python3.12

USER airflow

COPY --chown=airflow:root airflow/requirements-airflow.txt /tmp/requirements-airflow.txt
RUN pip install --no-cache-dir -r /tmp/requirements-airflow.txt