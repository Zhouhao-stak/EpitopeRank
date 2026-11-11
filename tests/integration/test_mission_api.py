"""自主任务页依赖的证明接口：结构化状态、产物索引与报告链接。"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from epitoperank.api.app import _list_project_artifacts, create_app
from epitoperank.llm.trace import ModelTrace


@pytest.fixture
def env(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("EPITOPERANK_RUNTIME_ROOT", str(runtime))
    project = runtime / "projects" / "P1"
    project.mkdir(parents=True)
    (project / "report.html").write_text("<html>ok</html>", encoding="utf-8")
    (project / "report.pdf").write_bytes(b"%PDF-1.4 stub")
    figures = project / "figures"
    figures.mkdir()
    (figures / "volcano.png").write_bytes(b"png")
    state = {
        "steps": [{"index": 0, "action": "profile_dataset", "source": "rule"}],
        "facts": {"candidates": 0, "figures": 0},
        "model_calls": [], "tool_calls": [], "errors": [], "params": {},
        "meta": {
            "schema_version": 1, "integrity": None, "query": "找候选",
            "project_id": "P1", "input_dir": str(tmp_path),
            "stopped_reason": "error budget exhausted (3 failures)",
            "input_fingerprints": {}, "reports": {},
        },
    }
    state["meta"]["integrity"] = ModelTrace.checksum(state)
    (project / "agent_state.json").write_text(json.dumps(state), encoding="utf-8")
    return TestClient(create_app()), project


def test_proof_reports_failure_and_points_to_real_files(env) -> None:
    client, project = env
    response = client.get("/api/projects/P1/proof")
    assert response.status_code == 200
    proof = response.json()
    assert proof["run_status"] == "failed"
    assert "未产出" in proof["run_summary"]
    assert proof["failure"]["hint"]
    assert proof["output_dir"] == str(project)
    assert {item["name"] for item in proof["artifacts"]} >= {
        "report.html", "report.pdf", "agent_state.json", "volcano.png"}
    assert proof["report_urls"]["html"] == "/api/report/P1?format=html"
    assert proof["report_urls"]["pdf"] == "/api/report/P1?format=pdf"


def test_list_artifacts_only_returns_existing_files(env) -> None:
    _, project = env
    names = [item["name"] for item in _list_project_artifacts(project)]
    assert names.count("report.html") == 1
    assert "volcano.png" in names
    assert all(item["size"] > 0 for item in _list_project_artifacts(project))
