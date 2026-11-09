"""Removed development endpoints stay gone; encoded traversal is rejected."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from epitoperank.api.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.mark.parametrize("path", [
    "/api/understand",
    "/api/skills/list",
    "/api/skills/execute",
    "/api/neoantigen/audit",
])
def test_removed_legacy_endpoints_return_404(client, path):
    assert client.post(path, json={}).status_code == 404


@pytest.mark.parametrize("path", [
    "/api/report/..%2F..%2Fetc",
    "/api/projects/..%2Fetc/events",
    "/api/figure/..%2Fsecret/volcano.png",
    "/api/status/..%2F..%2Fwindows",
])
def test_encoded_parent_segments_are_rejected(client, path):
    assert client.get(path).status_code == 400


def test_live_endpoints_still_work(client):
    assert client.get("/api/health").status_code == 200
    assert client.post("/api/plan/preview", json={"query": "Analyze splicing"}).status_code == 200
