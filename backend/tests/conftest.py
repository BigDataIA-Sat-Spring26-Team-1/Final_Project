"""Shared test fixtures for the backend suite.

Biggest job: make sure no unit test ever opens a real Snowflake session.
Locally, a populated .env masks the problem (tests that forget to mock
``get_db_connection`` silently connect to real Snowflake). In CI the
placeholder credentials 404 against ``test.snowflakecomputing.com`` and
the test run blows up.

The fixture below patches ``snowflake.connector.connect`` at the module
boundary so any service/agent that imports it gets a MagicMock that
answers common cursor calls without reaching the network.
"""
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _stub_snowflake_connection(monkeypatch):
    """Replace the network-reaching ``snowflake.connector.connect`` with a mock.

    Individual tests can still override the cursor return values via their
    own ``patch`` calls — MagicMock's recursive attribute access means the
    default stub tolerates any ``conn.cursor().execute(...)`` chain that
    older tests rely on.
    """
    fake_cursor = MagicMock()
    fake_cursor.description = [("col",)]
    fake_cursor.fetchone.return_value = None
    fake_cursor.fetchall.return_value = []

    fake_conn = MagicMock()
    fake_conn.cursor.return_value = fake_cursor
    fake_conn.database = "TEST_DB"
    fake_conn.schema = "PUBLIC"

    monkeypatch.setattr("snowflake.connector.connect", lambda *a, **kw: fake_conn)
    yield
