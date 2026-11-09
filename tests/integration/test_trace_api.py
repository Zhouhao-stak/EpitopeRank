"""Read-only decision-trace API and record/replay comparison endpoints."""
from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from epitoperank.api.app import create_app
from epitoperank.llm.trace import ModelTrace


@pytest.fixture
def env(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("EPITOPERANK_RUNTIME_ROOT", str(runtime))
    project = runtime / "projects" / "P1"
    project.mkdir(parents=True)
    report = project / "report.html"
    report.write_text("<html>deterministic report</html>", encoding="utf-8")
    report_hash = hashlib.sha256(report.read_bytes()).hexdigest()
    state = {
        "steps": [
            {"index": 0, "action": "profile_dataset", "source": "rule", "status": "ok"},
            {"index": 1, "action": "mcp__predict_mhc_binding", "source": "llm", "status": "ok"},
        ],
        "model_calls": [{"seq": 0, "stage": "model_plan", "model": "test",
                         "prompt_hash": "b" * 64, "raw_response": "{}", "parsed": {}}],
        "tool_calls": [{"seq": 0, "server": "epitoperank-builtin",
                        "tool": "predict_mhc_binding", "args": {},
                        "result": {"predictions": []}}],
        "params": {"fdr": 0.05}, "errors": [],
        "meta": {"schema_version": 1, "integrity": None, "decisions": [],
                 "llm_enabled": True, "model_name": "test", "query": "q",
                 "project_id": "P1", "reports": {"html": report_hash},
                 "ranked": [], "input_fingerprints": {"a.tsv": "hash"}},
    }
    state["meta"]["integrity"] = ModelTrace.checksum(state)
    state_path = project / "agent_state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return TestClient(create_app()), runtime, state_path


def test_trace_endpoint_exposes_decisions_and_integrity(env):
    client, _, _ = env
    response = client.get("/api/projects/P1/trace")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["total_steps"] == 2
    assert data["sources"] == {"rule": 1, "llm": 1}
    assert data["model_call_count"] == 1
    assert data["tool_call_count"] == 1
    assert data["integrity_ok"] is True
    assert data["model_calls"][0]["stage"] == "model_plan"


def test_trace_endpoint_rejects_missing_and_invalid_projects(env):
    client, _, _ = env
    assert client.get("/api/projects/UNKNOWN/trace").status_code == 404
    assert client.get("/api/projects/bad%20id/trace").status_code == 400


def test_compare_same_trace_is_identical(env):
    client, _, state_path = env
    response = client.post("/api/trace/compare",
                           json={"left": "P1", "right": str(state_path.parent)})
    assert response.status_code == 200
    assert response.json()["identical"] is True
    assert response.json()["differences"] == []


def test_compare_detects_modified_report(env):
    client, _, state_path = env
    (state_path.parent / "report.html").write_text("tampered", encoding="utf-8")
    response = client.post("/api/trace/compare",
                           json={"left": "P1", "right": str(state_path.parent)})
    assert response.status_code == 200
    assert response.json()["identical"] is False
    assert any("modified" in item for item in response.json()["differences"])


def test_compare_rejects_paths_outside_runtime_root(env):
    client, runtime, _ = env
    response = client.post("/api/trace/compare",
                           json={"left": "P1", "right": str(runtime.parent / "outside")})
    assert response.status_code == 400
    assert client.post("/api/trace/compare", json={"left": "P1"}).status_code == 400
