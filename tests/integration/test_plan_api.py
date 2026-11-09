"""Goal-driven plan, proof and verification endpoints."""
from __future__ import annotations

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
    state = {
        "steps": [{"index": 0, "action": "profile_dataset", "source": "rule", "status": "ok"}],
        "model_calls": [], "tool_calls": [], "params": {}, "errors": [],
        "meta": {"schema_version": 1, "integrity": None, "query": "Analyze splicing",
                 "project_id": "P1", "input_dir": str(tmp_path / "no-such-input"),
                 "input_fingerprints": {"a.tsv": "hash"}, "reports": {},
                 "analysis_plan": {"goal": "g", "intent": "differential_AS",
                                   "thresholds": {"fdr": 0.05},
                                   "expected_tools": ["profile_dataset"]}},
    }
    state["meta"]["integrity"] = ModelTrace.checksum(state)
    (project / "agent_state.json").write_text(json.dumps(state), encoding="utf-8")
    return TestClient(create_app()), tmp_path


def test_plan_preview_is_editable_and_uses_real_tools(env):
    client, _ = env
    response = client.post("/api/plan/preview",
                           json={"query": "Find MHC-I neoantigen candidates"})
    assert response.status_code == 200
    body = response.json()
    assert body["registry_size"] == 33
    plan = body["plan"]
    assert plan["intent"] == "neoantigen"
    assert "mcp__predict_mhc_binding" in plan["expected_tools"]
    assert 0 < plan["thresholds"]["fdr"] < 1


def test_plan_run_rejects_missing_input_or_invalid_plan(env):
    client, tmp_path = env
    plan = client.post("/api/plan/preview", json={"query": "Analyze splicing"}).json()["plan"]
    assert client.post("/api/plan/run", json={"query": "q", "input_dir": "missing",
                                              "plan": plan}).status_code == 422
    plan["expected_tools"] = ["invented_action"]
    assert client.post("/api/plan/run", json={"query": "q",
                                              "input_dir": str(tmp_path),
                                              "plan": plan}).status_code == 422
    assert client.post("/api/plan/run", json={"query": "q", "input_dir": str(tmp_path),
                                              "plan": {}}).status_code == 422


def test_proof_endpoint_returns_a_self_contained_bundle(env):
    client, _ = env
    response = client.get("/api/projects/P1/proof")
    assert response.status_code == 200
    proof = response.json()
    assert proof["integrity_ok"] is True
    assert proof["input_fingerprints"] == {"a.tsv": "hash"}
    assert proof["plan"]["intent"] == "differential_AS"
    assert "run.py replay" in proof["replay_command"]
    assert proof["deviations"]["available"] is True
    assert proof["state_path"].endswith("agent_state.json")


def test_verify_rejects_unavailable_input_without_starting_a_job(env):
    client, _ = env
    response = client.post("/api/projects/P1/verify", json={})
    assert response.status_code == 422
    assert "input_dir" in response.json()["detail"]


def test_job_lookup_validates_id(env):
    client, _ = env
    assert client.get("/api/jobs/unknown-job").status_code == 404
    assert client.get("/api/jobs/bad%20id").status_code == 400
