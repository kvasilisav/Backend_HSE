import os

import pytest
from fastapi.testclient import TestClient

import main

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://moderation_test:moderation_test@localhost:5432/moderation_test",
)


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def db_client(client):
    pool = getattr(main.app.state, "db_pool", None)
    if pool is None:
        pytest.skip("Database not available")
    return client, pool
