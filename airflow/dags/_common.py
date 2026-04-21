"""Shared helpers for CurateAI DAGs.

Kept deliberately tiny — we want DAG files to remain self-contained and
readable. Anything in here is code that every DAG otherwise had to repeat.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict

# The backend package is bind-mounted into the scheduler / worker images at
# /opt/airflow/backend (see infrastructure/docker-compose.vm.yml). Airflow's
# Python path doesn't include this by default — importing app.* will fail
# unless we prepend it, and we cannot do it at module load time because
# Airflow imports DAG files with a different CWD. Every task callable that
# needs backend imports should invoke ``ensure_backend_on_path()`` first.
BACKEND_MOUNT = os.environ.get("CURATEAI_BACKEND_PATH", "/opt/airflow/backend")


def ensure_backend_on_path() -> None:
    """Idempotently prepend the backend source dir to ``sys.path``."""
    if BACKEND_MOUNT not in sys.path:
        sys.path.insert(0, BACKEND_MOUNT)


def default_args(owner: str = "curateai") -> Dict[str, Any]:
    """Standard default_args so we don't redefine them in every DAG.

    ``start_date`` is pinned in the past so the scheduler picks the DAG up on
    first boot instead of waiting for a future run. ``catchup=False`` on the
    DAG itself prevents replaying missed runs at deploy time.
    """
    return {
        "owner": owner,
        "depends_on_past": False,
        "start_date": datetime(2026, 4, 1),
        "email_on_failure": False,
        "email_on_retry": False,
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=45),
    }
