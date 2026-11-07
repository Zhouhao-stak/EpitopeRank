"""Small model boundary/integrity tests; every call is stubbed."""
import dataclasses
import hashlib
import json
from types import SimpleNamespace

import pytest

from epitoperank.agent.session import load_state, save_state
from epitoperank.agent.state import AgentState, Goal
from epitoperank.config import load_settings, LLMSettings
from epitoperank.llm.client import effective_temperature
from epitoperank.llm.enrich import LLMEnhancer
from epitoperank.llm.trace import ACTIVE, ModelTrace, ReplayError


@pytest.fixture
def settings():
    return dataclasses.replace(load_settings(), llm=LLMSettings(
        base_url="https://api.deepseek.com", api_key="test-secret", model="deepseek-chat", temperature=0.7))


def write_trace(tmp_path, trace):
    data = {"meta": dict(trace.meta, schema_version=1, decisions=trace.decisions), "model_calls": trace.calls}
    data["meta"]["integrity"] = trace.checksum(data)
    path = tmp_path / "trace.json"
    path.write_text(json.dumps(data), encoding="utf8")
    return path


def test_injected_recorder_and_effective_sampling(settings, monkeypatch):
    trace = ModelTrace(settings)
    enhancer = LLMEnhancer(settings, recorder=trace)
    monkeypatch.setattr(LLMEnhancer, "complete", lambda *a, **kw: '{"action":"rank_candidates"}')
    enhancer.request(system="system", user="user", stage="model_plan", temperature=0.01, max_tokens=40, json_output=True)
    record = trace.calls[0]
    assert record["prompt_hash"] == hashlib.sha256(b"system\nuser").hexdigest()
    assert record["temperature_effective"] == effective_temperature(settings, tools_expected=True)
    assert record["temperature_effective"] != 0.01
    assert record["parsed"] == {"action": "rank_candidates"}
    assert record["max_tokens"] == 40
    assert "reasoning_effort" not in record


def test_secrets_scrubbed(settings, monkeypatch):
    trace = ModelTrace(settings)
    monkeypatch.setattr(LLMEnhancer, "complete", lambda *a, **kw: "Authorization: Bearer test-secret token=another-secret")
    LLMEnhancer(settings, recorder=trace).request(system="api_key=test-secret", user="token=unknown")
    text = json.dumps(trace.clean({"llm": dataclasses.asdict(settings.llm), "calls": trace.calls}))
    for secret in ("test-secret", "another-secret", "unknown"):
        assert secret not in text
    assert '"api_key"' not in text


@pytest.mark.parametrize("mismatch", ["prompt", "stage", "missing", "remaining"])
def test_replay_boundary_rejects_mismatch(settings, tmp_path, monkeypatch, mismatch):
    trace = ModelTrace(settings)
    monkeypatch.setattr(LLMEnhancer, "complete", lambda *a, **kw: "{}")
    enhancer = LLMEnhancer(settings, recorder=trace)
    enhancer.request(system="s", user="u", stage="insight")
    replay = ModelTrace(settings, write_trace(tmp_path, trace))
    enhancer.recorder = replay
    monkeypatch.setattr(LLMEnhancer, "complete", lambda *a, **kw: pytest.fail("LLM request"))
    with pytest.raises(ReplayError):
        if mismatch == "remaining":
            replay.finish()
        else:
            if mismatch == "missing":
                replay.cursor = 1
            enhancer.request(system="different" if mismatch == "prompt" else "s", user="u",
                             stage="wrong" if mismatch == "stage" else "insight")
    assert replay.errors


def test_direct_complete_guard(settings):
    trace = ModelTrace(settings)
    trace.replay = True
    token = ACTIVE.set(trace)
    try:
        with pytest.raises(ReplayError, match="complete called"):
            LLMEnhancer(settings).complete(system="s", user="u")
    finally:
        ACTIVE.reset(token)


def test_old_state_compatible(tmp_path):
    (tmp_path / "agent_state.json").write_text('{"params":{"fdr":0.05}}', encoding="utf8")
    state = load_state(tmp_path, SimpleNamespace())
    assert state.model_calls == [] and state.meta == {}
    state.model_calls = [{"prompt_hash": "hash", "raw_response": "raw"}]
    state.meta = {"schema_version": 1}
    save_state(state, tmp_path)
    restored = load_state(tmp_path, SimpleNamespace())
    assert restored.model_calls == state.model_calls and restored.meta == state.meta


def test_retry_cache_telemetry_replayed(settings, tmp_path, monkeypatch):
    trace = ModelTrace(settings)
    notes = []
    enhancer = LLMEnhancer(settings, recorder=trace, logger=lambda *a: notes.append(a))
    attempts = []
    async def create(*a, **kw):
        attempts.append(kw)
        if len(attempts) == 1:
            raise ConnectionError("transient")
        return '{"ok":true}'
    monkeypatch.setattr(enhancer, "_create", create)
    kwargs = dict(system="s", user="u", json_output=True, stage="insight")
    assert enhancer.request(**kwargs) == '{"ok":true}'
    assert enhancer.request(**kwargs) == '{"ok":true}'
    assert trace.calls[0]["retries"] == 1
    assert trace.calls[1]["retries"] == 0
    assert trace.calls[1]["calls_added"] == []
    replay = ModelTrace(settings, write_trace(tmp_path, trace))
    replay_notes = []
    other = LLMEnhancer(settings, recorder=replay, logger=lambda *a: replay_notes.append(a))
    monkeypatch.setattr(LLMEnhancer, "complete", lambda *a, **k: pytest.fail("complete"))
    other.request(**kwargs)
    other.request(**kwargs)
    replay.finish()
    assert other.calls == enhancer.calls
    assert other.errors == enhancer.errors
    assert replay_notes == notes


def test_injected_replay_complete_guard(settings):
    trace = ModelTrace(settings)
    trace.replay = True
    with pytest.raises(ReplayError, match="complete called"):
        LLMEnhancer(settings, recorder=trace).complete(system="s", user="u")


def test_compare_detects_modified_report(tmp_path):
    from epitoperank.llm.trace import compare, file_hash
    report = tmp_path / "report.html"
    report.write_text("original", encoding="utf8")
    state = tmp_path / "agent_state.json"
    state.write_text(json.dumps({"steps": [], "params": {}, "meta": {
        "reports": {"html": file_hash(report)}}}), encoding="utf8")
    assert compare(state, state) == []
    report.write_text("changed", encoding="utf8")
    assert any("modified" in d for d in compare(state, state))
