"""Offline end-to-end model recording and replay contract."""
import dataclasses
import json
from pathlib import Path

import pytest

from epitoperank.config import load_settings, PathSettings, LLMSettings
from epitoperank.llm.enrich import LLMEnhancer
from epitoperank.llm.trace import ReplayError, compare
from epitoperank.pipeline import run_analysis


@pytest.fixture
def recorded(tmp_path, monkeypatch):
    monkeypatch.setenv("EPITOPERANK_ENABLE_PUBMED", "false")
    settings = load_settings()
    settings = dataclasses.replace(settings,
        paths=PathSettings(tmp_path / "runtime", tmp_path / "memory.db", tmp_path / "literature.db"),
        llm=LLMSettings(base_url="https://invalid.test", api_key="SUPER_SECRET", model="test", features=("all",)),
        agent=dataclasses.replace(settings.agent, episodic=False, skills=dataclasses.replace(settings.agent.skills, enabled=False)))
    calls = []
    def complete(self, **kw):
        calls.append(kw)
        if "planning brain" in kw["system"]:
            payload = json.loads(kw["user"])
            available = {a["name"] for a in payload["available_actions"]}
            for action in ("summarize_dataset", "filter_significant_events", "rank_candidates", "run_enrichment", "generate_figures", "collect_literature_evidence", "interpret_candidates", "generate_report"):
                if action in available and action not in payload["action_counts"]:
                    return json.dumps({"action": action, "args": {}, "rationale": "recorded plan"})
        if kw.get("feature") == "interpret":
            return json.dumps({"lead": "Recorded model interpretation.",
                               "paragraphs": ["Recorded evidence-grounded narrative."], "highlights": []})
        return "{}"
    def call_once(self, system, user, model, max_tokens, json_output, timeout, feature):
        return complete(self, system=system, user=user, model=model, max_tokens=max_tokens,
                        json_output=json_output, timeout=timeout, feature=feature)
    monkeypatch.setattr(LLMEnhancer, "_call_once", call_once)
    outcome = run_analysis("Analyze splicing", "examples/demo_rmats", settings=settings,
                           project_id="TRACE", output_root=tmp_path / "record")
    path = outcome.output_dir / "agent_state.json"
    return settings, outcome, path, calls


def test_record_replay_identical(recorded, tmp_path, monkeypatch):
    settings, original, path, calls = recorded
    assert calls
    data = json.loads(path.read_text(encoding="utf-8"))
    assert any(c["stage"] == "model_plan" for c in data["model_calls"])
    assert any(c["stage"].startswith("enrichment:") for c in data["model_calls"])
    assert all(c["prompt_hash"] and "raw_response" in c for c in data["model_calls"])
    assert "SUPER_SECRET" not in path.read_text(encoding="utf-8")
    def forbidden(*a, **kw):
        pytest.fail("complete called in replay")
    monkeypatch.setattr(LLMEnhancer, "complete", forbidden)
    settings = dataclasses.replace(settings, llm=dataclasses.replace(settings.llm, api_key=""),
                                   agent=dataclasses.replace(settings.agent, replay=str(path)))
    replay = run_analysis("Analyze splicing", "examples/demo_rmats", settings=settings, output_root=tmp_path / "replay")
    assert compare(path, replay.output_dir / "agent_state.json") == []
    assert original.context.llm_insights["narrative"]["source"] == "llm"
    assert replay.context.llm_insights["narrative"] == original.context.llm_insights["narrative"]
    assert replay.team.params == original.team.params
    assert [s.action for s in replay.team.steps] == [s.action for s in original.team.steps]
    assert any(s.source == "replay" for s in replay.team.steps)
    for kind, report in original.report_paths.items():
        assert report.read_bytes() == replay.report_paths[kind].read_bytes()


def test_tamper_fails(recorded, tmp_path, monkeypatch):
    settings, _, path, _ = recorded
    data = json.loads(path.read_text(encoding="utf-8"))
    data["model_calls"][0]["raw_response"] = "tampered"
    altered = tmp_path / "tampered.json"
    altered.write_text(json.dumps(data), encoding="utf-8")
    settings = dataclasses.replace(settings, agent=dataclasses.replace(settings.agent, replay=str(altered)))
    monkeypatch.setattr(LLMEnhancer, "complete", lambda *a, **k: pytest.fail("network"))
    with pytest.raises(ReplayError, match="checksum"):
        run_analysis("Analyze splicing", "examples/demo_rmats", settings=settings, output_root=tmp_path / "failed")
    assert list((tmp_path / "failed").rglob("replay_errors.json"))
    assert not list((tmp_path / "failed").rglob("report.html"))


def test_input_change_fails_before_model(recorded, tmp_path, monkeypatch):
    settings, _, path, _ = recorded
    other_input = tmp_path / "input"
    other_input.mkdir()
    (other_input / "changed.tsv").write_text("different input", encoding="utf8")
    settings = dataclasses.replace(settings, agent=dataclasses.replace(settings.agent, replay=str(path)))
    monkeypatch.setattr(LLMEnhancer, "complete", lambda *a, **k: pytest.fail("LLM request"))
    with pytest.raises(ReplayError, match="fingerprints"):
        run_analysis("Analyze splicing", other_input, settings=settings, output_root=tmp_path / "bad-input")
    assert not list((tmp_path / "bad-input").rglob("report.html"))
