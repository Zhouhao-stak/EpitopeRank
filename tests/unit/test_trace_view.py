"""Decision-trace summary: source statistics and integrity verification."""
from __future__ import annotations

import json

import pytest

from epitoperank.agent.trace_view import load_state, summarize
from epitoperank.llm.trace import ModelTrace


def _state():
    data = {
        "steps": [
            {"index": 0, "action": "profile_dataset", "source": "rule", "status": "ok"},
            {"index": 1, "action": "web_fetch", "source": "llm", "status": "ok"},
            {"index": 2, "action": "filter_significant_events", "source": "reflection", "status": "ok"},
            {"index": 3, "action": "adapt_thresholds", "source": "episodic", "status": "ok"},
            {"index": 4, "action": "generate_report", "source": "replay", "status": "ok"},
        ],
        "model_calls": [{"seq": 0, "stage": "model_plan", "model": "test",
                         "prompt_hash": "a" * 64, "raw_response": "{}", "parsed": {}}],
        "tool_calls": [{"seq": 0, "server": "s", "tool": "predict_mhc_binding",
                        "args": {}, "result": {"predictions": []}}],
        "params": {"fdr": 0.05}, "errors": [],
        "meta": {"schema_version": 1, "integrity": None, "decisions": [{"begin": 0, "end": 1}],
                 "llm_enabled": True, "model_name": "test", "query": "q",
                 "project_id": "P1", "reports": {}, "input_fingerprints": {"a.tsv": "x"}},
    }
    data["meta"]["integrity"] = ModelTrace.checksum(data)
    return data


def test_summary_counts_decision_sources_and_calls():
    view = summarize(_state())
    assert view["total_steps"] == 5
    assert view["sources"] == {"rule": 1, "llm": 1, "reflection": 1,
                               "episodic": 1, "replay": 1}
    assert view["llm_steps"] == 1 and view["llm_ratio"] == 0.2
    assert view["reflection_steps"] == 1 and view["episodic_steps"] == 1
    assert view["model_call_count"] == 1 and view["tool_call_count"] == 1
    assert view["integrity_ok"] is True
    assert view["steps"][1]["source"] == "llm"
    assert view["model_calls"][0]["stage"] == "model_plan"


def test_tampered_state_fails_integrity_check():
    data = _state()
    data["steps"][1]["action"] = "something_else"
    assert summarize(data)["integrity_ok"] is False


def test_old_state_without_new_fields_is_still_readable():
    data = {"steps": [{"index": 0, "action": "profile_dataset", "status": "ok"}],
            "params": {}, "meta": {}}
    view = summarize(data)
    assert view["total_steps"] == 1
    assert view["sources"] == {"rule": 1}
    assert view["model_call_count"] == 0 and view["tool_call_count"] == 0
    assert view["integrity_ok"] is False


def test_load_state_accepts_file_or_directory(tmp_path):
    project = tmp_path / "P1"
    project.mkdir()
    (project / "agent_state.json").write_text(json.dumps(_state()), encoding="utf-8")
    assert load_state(project)["meta"]["project_id"] == "P1"
    assert load_state(project / "agent_state.json")["meta"]["project_id"] == "P1"
    with pytest.raises(FileNotFoundError):
        load_state(tmp_path / "missing")
