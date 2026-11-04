"""Integration tests for the copilot API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from epitoperank.api.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_copilot_tools_lists_registry(client):
    response = client.get("/api/copilot/tools")
    assert response.status_code == 200
    payload = response.json()
    names = [tool["name"] for tool in payload["tools"]]
    assert "project_overview" in names
    assert "query_events" in names
    assert payload["limits"]["max_steps"] >= 1


def test_copilot_chat_requires_message(client):
    response = client.post("/api/copilot/chat", json={"message": "   "})
    assert response.status_code == 400


def test_copilot_chat_rejects_bad_history(client):
    response = client.post("/api/copilot/chat", json={"message": "hi", "history": "nope"})
    assert response.status_code == 422


def test_copilot_chat_offline_briefing(client):
    response = client.post("/api/copilot/chat", json={
        "message": "有哪些项目？",
        "force_offline": True,
        "max_steps": 2,
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "offline"
    assert "结论" in payload["answer"]
    assert isinstance(payload["tool_calls"], list)
    assert payload["grounding"]["severity"] == "ok"
    assert payload["strategy"] in {"react", "plan"}
    assert "cache" in payload


def test_copilot_status_exposes_strategies_and_network_tools(client):
    payload = client.get("/api/copilot/tools").json()
    assert payload["strategies"] == ["react", "plan", "auto"]
    assert "annotate_gene" in payload["network_tools"]
    assert payload["limits"]["max_model_calls"] >= 1


def test_copilot_tools_can_disable_network(client):
    payload = client.get("/api/copilot/tools", params={"allow_network": False}).json()
    names = [tool["name"] for tool in payload["tools"]]
    assert "annotate_gene" not in names
    assert "project_overview" in names


def test_copilot_chat_rejects_unknown_mode(client):
    response = client.post("/api/copilot/chat", json={"message": "hi", "mode": "turbo"})
    assert response.status_code == 422


def test_copilot_stream_emits_sse_events(client):
    with client.stream("POST", "/api/copilot/stream", json={
        "message": "有哪些项目？",
        "force_offline": True,
        "max_steps": 2,
    }) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join(response.iter_text())
    assert "event: offline" in body
    assert "event: done" in body
    assert '"mode": "offline"' in body


def test_copilot_chat_plan_mode_offline_exposes_orchestration(client):
    response = client.post("/api/copilot/chat", json={
        "message": "比较这个项目的显著性与数据质量，并给出下一步建议。",
        "mode": "plan",
        "force_offline": True,
        "max_steps": 2,
    })
    assert response.status_code == 200
    payload = response.json()
    for key in ("plan", "critique", "strategy", "cache"):
        assert key in payload, f"missing response key: {key}"
    assert payload["mode"] == "offline"
    assert payload["strategy"] in {"react", "plan"}
    assert isinstance(payload["plan"], dict)
    assert isinstance(payload["critique"], dict)
    assert isinstance(payload["cache"], dict)


def test_copilot_stream_plan_mode_offline_emits_sse(client):
    with client.stream("POST", "/api/copilot/stream", json={
        "message": "比较这个项目的显著性与数据质量，并给出下一步建议。",
        "mode": "plan",
        "force_offline": True,
        "max_steps": 2,
    }) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join(response.iter_text())
    assert "event: offline" in body
    assert "event: done" in body


def test_copilot_tools_without_network_exclude_fulltext_search(client):
    payload = client.get("/api/copilot/tools", params={"allow_network": False}).json()
    names = [tool["name"] for tool in payload["tools"]]
    assert "search_literature_passages" not in names
    assert "search_literature" not in names
    assert "project_overview" in names
    assert payload["allow_network"] is False
