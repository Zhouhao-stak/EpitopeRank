"""Tests for the copilot evaluation harness."""

from __future__ import annotations

import dataclasses
import json

import pytest

from splicegaip.agent.copilot import CopilotAnswer
from splicegaip.agent.evaluation import (
    Case,
    evaluate,
    load_cases,
    run_case,
    score,
    script_for_case,
    write_report,
)
from splicegaip.config import LLMSettings, load_settings
from splicegaip.llm.scripted import ScriptedChat
from splicegaip.memory.project_memory import ProjectMemory

PROJECT = "SPN-EVAL0001"


def make_settings(tmp_path):
    base = load_settings("tests/fixtures/config_test.yaml")
    paths = dataclasses.replace(
        base.paths,
        runtime_root=tmp_path,
        memory_db=tmp_path / "memory.sqlite3",
        literature_db=tmp_path / "literature.sqlite3",
    )
    llm = LLMSettings(base_url="", api_key="", model="")
    return dataclasses.replace(base, paths=paths, llm=llm)


def seed_project(settings, tmp_path):
    memory = ProjectMemory(settings.paths.memory_db)
    memory.create_project(PROJECT, "demo", "eval", source_dir=str(tmp_path))


def test_load_cases_parses_jsonl(tmp_path) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text(
        json.dumps({"id": "a", "message": "hi", "expected_tools": ["project_overview"]}) + "\n"
        + "\n"
        + json.dumps({"id": "b", "message": "there", "project_required": False}) + "\n",
        encoding="utf-8",
    )
    cases = load_cases(path)
    assert [case.id for case in cases] == ["a", "b"]
    assert cases[0].expected_tools == ["project_overview"]
    assert cases[1].project_required is False


def test_load_cases_rejects_bad_line(tmp_path) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text("{not json}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_cases(path)


def test_script_for_case_calls_expected_tools() -> None:
    case = Case(id="x", message="q", expected_tools=["project_overview"])
    script = script_for_case(case)
    assert script[0]["tools"][0]["name"] == "project_overview"
    assert "## 结论" in script[1]["text"]


def test_score_counts_recall_and_forbidden() -> None:
    case = Case(id="x", message="q", expected_tools=["a", "b"], forbid_tools=["c"])
    answer = CopilotAnswer(
        answer="## 结论\n## 关键证据\n## 建议的下一步\n## 局限",
        tool_calls=[{"tool": "a"}, {"tool": "c"}],
        grounding={"severity": "ok"}, mode="llm",
    )
    row = score(case, answer)
    assert row["tool_recall"] == 0.5
    assert row["forbidden_hits"] == ["c"]
    assert row["passed"] is False


def test_score_passes_grounded_answer() -> None:
    case = Case(id="x", message="q", expected_tools=["project_overview"])
    answer = CopilotAnswer(
        answer="## 结论\n## 关键证据\n## 建议的下一步\n## 局限",
        tool_calls=[{"tool": "project_overview"}],
        grounding={"severity": "ok"}, mode="llm",
    )
    assert score(case, answer)["passed"] is True


def test_run_case_uses_scripted_model(tmp_path) -> None:
    settings = make_settings(tmp_path)
    seed_project(settings, tmp_path)
    case = Case(id="overview", message="项目里有什么？",
                expected_tools=["project_overview", "dataset_quality"])
    answer = run_case(case, settings, project_id=PROJECT)
    assert answer.mode == "llm"
    assert [call["tool"] for call in answer.tool_calls] == ["project_overview", "dataset_quality"]
    assert answer.grounding["severity"] == "ok"


def test_evaluate_aggregates(tmp_path) -> None:
    settings = make_settings(tmp_path)
    seed_project(settings, tmp_path)
    cases = [
        Case(id="a", message="项目里有什么？", expected_tools=["project_overview"]),
        Case(id="b", message="有哪些项目？", expected_tools=["list_projects"],
             project_required=False),
    ]
    payload = evaluate(cases, settings, project_id=PROJECT)
    assert payload["summary"]["case_count"] == 2
    assert payload["summary"]["pass_rate"] == 1.0
    assert payload["summary"]["total_tool_calls"] == 2


def test_evaluate_reports_failure_without_crashing(tmp_path) -> None:
    settings = make_settings(tmp_path)
    seed_project(settings, tmp_path)
    case = Case(id="bad", message="q", expected_tools=["project_overview"], forbid_tools=["project_overview"])
    payload = evaluate([case], settings, project_id=PROJECT)
    assert payload["summary"]["pass_rate"] == 0.0
    assert payload["cases"][0]["forbidden_hits"] == ["project_overview"]


def test_write_report(tmp_path) -> None:
    payload = {"cases": [{"id": "a", "passed": True, "tool_recall": 1.0, "tool_precision": 1.0,
                          "grounding_ok": True, "sections_ok": True, "tool_calls": 1, "tokens": 10}],
               "summary": {"case_count": 1, "pass_rate": 1.0, "avg_tool_recall": 1.0,
                           "avg_tool_precision": 1.0, "grounding_ok_rate": 1.0,
                           "sections_ok_rate": 1.0, "total_tokens": 10, "elapsed_seconds": 0.1}}
    paths = write_report(payload, tmp_path / "report")
    assert (tmp_path / "report" / "agent_eval.json").is_file()
    assert "Copilot evaluation" in (tmp_path / "report" / "agent_eval.md").read_text(encoding="utf-8")
    assert paths["json"].endswith("agent_eval.json")


def test_script_for_case_passes_tool_arguments() -> None:
    case = Case(id="args", message="q", expected_tools=["query_events"],
                tool_arguments={"query_events": {"significant_only": True, "limit": 7}})
    script = script_for_case(case)
    assert script[0]["tools"][0]["arguments"] == {"significant_only": True, "limit": 7}


def test_plan_case_script_starts_with_json_plan_and_scores_passed(tmp_path) -> None:
    settings = make_settings(tmp_path)
    seed_project(settings, tmp_path)
    case = Case(
        id="plan",
        message="比较分组质量和候选事件，并给出下一步建议与局限。",
        expected_tools=["project_overview", "dataset_quality"],
        strategy="plan",
    )
    script = script_for_case(case)
    plan_payload = json.loads(script[0]["text"])
    assert plan_payload["steps"]
    assert "goal" in plan_payload

    answer = run_case(case, settings, project_id=PROJECT)
    assert answer.strategy == "plan"
    assert answer.plan.get("source") == "llm"
    assert answer.critique.get("verdict") == "pass"
    row = score(case, answer)
    assert row["passed"] is True
    assert row["strategy"] == "plan"


def test_score_counts_cache_hits_on_duplicate_calls(tmp_path) -> None:
    settings = make_settings(tmp_path)
    seed_project(settings, tmp_path)
    case = Case(id="dup", message="读两次项目概览",
                expected_tools=["project_overview", "project_overview"])
    answer = run_case(case, settings, project_id=PROJECT)
    assert [call["tool"] for call in answer.tool_calls] == [
        "project_overview", "project_overview"]
    assert answer.tool_calls[1]["cached"] is True
    row = score(case, answer)
    assert row["cache_hits"] == 1
    payload = evaluate([case], settings, project_id=PROJECT)
    assert payload["summary"]["total_cache_hits"] == 1


def test_score_fails_when_required_section_missing() -> None:
    case = Case(id="partial", message="q", expected_tools=["project_overview"])
    answer = CopilotAnswer(
        answer="## 结论\n只写了一段结论，没有证据、下一步和局限。",
        tool_calls=[{"tool": "project_overview"}],
        grounding={"severity": "ok"}, mode="llm",
    )
    row = score(case, answer)
    assert row["sections_ok"] is False
    assert row["passed"] is False


class _BrokenChat:
    """A client that fails inside the loop (not a factory that raises)."""

    available = True
    model = "broken"

    def complete(self, *args, **kwargs):
        raise RuntimeError("simulated transport failure")


def test_evaluate_isolates_a_raising_case(tmp_path) -> None:
    settings = make_settings(tmp_path)
    seed_project(settings, tmp_path)
    bad = Case(id="bad", message="q", expected_tools=["project_overview"])
    good = Case(id="good", message="项目里有什么？", expected_tools=["project_overview"])

    def factory(case: Case):
        if case.id == "bad":
            return _BrokenChat()
        return ScriptedChat(script=script_for_case(case))

    payload = evaluate([bad, good], settings, project_id=PROJECT, chat_factory=factory)
    assert payload["summary"]["case_count"] == 2
    assert payload["cases"][0]["id"] == "bad"
    assert "error" in payload["cases"][0]
    assert payload["cases"][0]["passed"] is False
    assert payload["cases"][1]["passed"] is True
    assert payload["summary"]["pass_rate"] == 0.5
