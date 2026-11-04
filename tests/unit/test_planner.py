"""Tests for the planner / critic roles."""

from __future__ import annotations

import json

import pytest

from epitoperank.agent.planner import (
    Plan,
    critique_answer,
    deterministic_critique,
    heuristic_plan,
    make_plan,
    revision_instruction,
)
from epitoperank.llm.scripted import ScriptedChat

TOOLS = [
    {"type": "function", "function": {"name": "project_overview", "description": "overview",
                                      "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "query_events", "description": "events",
                                      "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "predict_peptides", "description": "peptides",
                                      "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "search_literature", "description": "papers",
                                      "parameters": {"type": "object", "properties": {}}}},
]

# The exact reply a real DeepSeek planner returned: ``plan`` instead of
# ``steps``, integer ``step`` fields, per-step ``success_criteria`` and
# ``risks_extra``. It used to fall back to the heuristic plan silently.
REAL_PLAN_PAYLOAD = {
    "plan": [
        {"step": 1,
         "action": "读取项目概览，确认这些事件所属数据集、样本定义（p/FDR/效应量）",
         "tool": "project_overview",
         "success_criteria": "明确事件所属数据集与显著值定义"},
        {"step": 2,
         "action": "查询项目事件",
         "tool": "query_events",
         "success_criteria": "列出每条目标事件的注释"},
    ],
    "risks": ["样本缺失配对正常样本时，无法区分真实生物学信号与背景"],
    "risks_extra": ["样本量小", "阈值选择影响事件数"],
}


def test_heuristic_plan_uses_keywords() -> None:
    plan = heuristic_plan("用 HLA-A*02:01 预测候选肽，顺便查一下文献",
                          project_id="P1", tools=TOOLS)
    tools = [step["tool"] for step in plan.steps]
    assert "project_overview" in tools
    assert "predict_peptides" in tools
    assert "search_literature" in tools
    assert plan.source == "heuristic"


def test_heuristic_plan_without_project_still_has_steps() -> None:
    plan = heuristic_plan("这个数据质量怎么样？", project_id=None, tools=TOOLS)
    assert plan.steps
    assert all(step["tool"] in {"project_overview", "dataset_quality", "top_candidates", "query_events"}
               for step in plan.steps)


def test_make_plan_accepts_valid_model_reply() -> None:
    payload = {
        "goal": "评估证据",
        "steps": [{"action": "读概览", "tool": "project_overview", "arguments": {}, "purpose": "基线"}],
        "success_criteria": ["有事件数"],
        "risks": ["样本少"],
    }
    chat = ScriptedChat(script=[{"text": json.dumps(payload)}])
    plan = make_plan("看看项目", None, chat, project_id="P1", tools=TOOLS)
    assert plan.source == "llm"
    assert plan.steps[0]["tool"] == "project_overview"


def test_make_plan_falls_back_on_invalid_json() -> None:
    chat = ScriptedChat(script=[{"text": "not json"}])
    plan = make_plan("看看项目", None, chat, project_id="P1", tools=TOOLS)
    assert plan.source == "heuristic"


def test_make_plan_drops_unknown_tool() -> None:
    payload = {"goal": "x", "steps": [{"action": "hack", "tool": "drop_table", "arguments": {}}]}
    chat = ScriptedChat(script=[{"text": json.dumps(payload)}])
    plan = make_plan("看看", None, chat, project_id="P1", tools=TOOLS)
    assert plan.steps[0]["tool"] == ""


@pytest.mark.parametrize("fenced", [False, True])
def test_make_plan_accepts_real_deepseek_shape(fenced: bool) -> None:
    """The production reply used ``plan``/``step``/``success_criteria``/``risks_extra``."""
    text = json.dumps(REAL_PLAN_PAYLOAD, ensure_ascii=False)
    if fenced:
        text = f"```json\n{text}\n```"
    chat = ScriptedChat(script=[{"text": text}])
    plan = make_plan("分析这些事件", None, chat, project_id="P1", tools=TOOLS)

    assert plan.source == "llm"
    assert len(plan.steps) == 2
    assert [step["tool"] for step in plan.steps] == ["project_overview", "query_events"]
    assert plan.steps[0]["purpose"] == "明确事件所属数据集与显著值定义"
    assert plan.steps[1]["purpose"] == "列出每条目标事件的注释"
    assert plan.steps[0]["arguments"] == {}
    assert plan.goal == "分析这些事件"
    assert plan.success_criteria == [
        "明确事件所属数据集与显著值定义",
        "列出每条目标事件的注释",
    ]
    assert plan.risks == [
        "样本缺失配对正常样本时，无法区分真实生物学信号与背景",
        "样本量小",
        "阈值选择影响事件数",
    ]


def test_critique_accepts_string_issues_and_derives_verdict() -> None:
    """String issues and a missing verdict are normalised, not rejected."""
    payload = {"issues": ["数字 0.001 未溯源", "缺少局限"]}
    chat = ScriptedChat(script=[{"text": json.dumps(payload, ensure_ascii=False)}])
    report = critique_answer(
        "问题",
        "## 结论\nx\n## 关键证据\ny\n## 建议的下一步\nz\n## 局限\nw",
        settings=None, client=chat, plan=None,
        tool_calls=[{"tool": "project_overview"}],
        grounding={"severity": "ok", "unverified": []}, project_id=None,
    )
    assert report["verdict"] == "pass"
    assert len(report["issues"]) == 2
    assert all(item["severity"] == "medium" for item in report["issues"])
    assert "数字 0.001 未溯源" in [item["problem"] for item in report["issues"]]


def test_critique_derives_revise_from_high_severity() -> None:
    payload = {
        "issues": [{"severity": "high", "problem": "把结合预测说成呈递"}],
        "review": "补充说明",
    }
    chat = ScriptedChat(script=[{"text": json.dumps(payload, ensure_ascii=False)}])
    report = critique_answer(
        "问题",
        "## 结论\nx\n## 关键证据\ny\n## 建议的下一步\nz\n## 局限\nw",
        settings=None, client=chat, plan=None,
        tool_calls=[{"tool": "project_overview"}],
        grounding={"severity": "ok", "unverified": []}, project_id=None,
    )
    assert report["verdict"] == "revise"
    problems = [item["problem"] for item in report["issues"]]
    assert "把结合预测说成呈递" in problems
    assert "补充说明" in problems


def test_critique_accepts_review_only_payload() -> None:
    chat = ScriptedChat(script=[{"text": json.dumps({"review": "工具结果与结论不一致"},
                                                    ensure_ascii=False)}])
    report = critique_answer(
        "问题",
        "## 结论\nx\n## 关键证据\ny\n## 建议的下一步\nz\n## 局限\nw",
        settings=None, client=chat, plan=None,
        tool_calls=[{"tool": "project_overview"}],
        grounding={"severity": "ok", "unverified": []}, project_id=None,
    )
    assert any("工具结果与结论不一致" in item["problem"] for item in report["issues"])
    assert report["verdict"] == "pass"


def test_deterministic_critique_flags_no_tools() -> None:
    report = deterministic_critique("## 结论\n没问题", tool_calls=[], grounding={"severity": "ok"},
                                    plan=None, project_id="P1")
    assert report["verdict"] == "revise"
    assert any(item["severity"] == "high" for item in report["issues"])


def test_deterministic_critique_flags_ungrounded_numbers() -> None:
    report = deterministic_critique(
        "## 结论\nFDR 是 0.001\n## 关键证据\nx\n## 建议的下一步\ny\n## 局限\nz",
        tool_calls=[{"tool": "project_overview"}],
        grounding={"severity": "warn", "unverified": ["0.001"]},
        plan=None, project_id="P1",
    )
    assert report["verdict"] == "revise"
    assert "0.001" in " ".join(item["problem"] for item in report["issues"])


def test_critique_never_downgrades_high_severity() -> None:
    chat = ScriptedChat(script=[{"text": json.dumps({"verdict": "pass", "issues": []})}])
    report = critique_answer(
        "问题", "## 结论\nx", settings=None, client=chat, plan=None,
        tool_calls=[], grounding={"severity": "ok", "unverified": []}, project_id="P1",
    )
    assert report["verdict"] == "revise"
    assert any(item["severity"] == "high" for item in report["issues"])


def test_revision_instruction_lists_issues() -> None:
    text = revision_instruction({"issues": [{"severity": "high", "problem": "数字未溯源", "fix": "删除"}]})
    assert "数字未溯源" in text
    assert "四段式" in text


def test_critique_downgrades_numeric_high_when_grounding_ok() -> None:
    """The program's grounding check is authoritative over critic guesses."""
    payload = {"issues": [{"severity": "high", "problem": "数字 FDR 未溯源"}]}
    chat = ScriptedChat(script=[{"text": json.dumps(payload, ensure_ascii=False)}])
    report = critique_answer(
        "问题",
        "## 结论\nx\n## 关键证据\ny\n## 建议的下一步\nz\n## 局限\nw",
        settings=None, client=chat, plan=None,
        tool_calls=[{"tool": "project_overview"}],
        grounding={"severity": "ok", "unverified": []}, project_id=None,
    )
    assert report["verdict"] == "pass"
    assert report["issues"][0]["severity"] == "medium"


def test_critique_keeps_semantic_high_when_grounding_ok() -> None:
    payload = {"issues": [{"severity": "high", "problem": "把相关性说成因果"}]}
    chat = ScriptedChat(script=[{"text": json.dumps(payload, ensure_ascii=False)}])
    report = critique_answer(
        "问题",
        "## 结论\nx\n## 关键证据\ny\n## 建议的下一步\nz\n## 局限\nw",
        settings=None, client=chat, plan=None,
        tool_calls=[{"tool": "project_overview"}],
        grounding={"severity": "ok", "unverified": []}, project_id=None,
    )
    assert report["verdict"] == "revise"


def test_plan_prompt_text_marks_unavailable_tools() -> None:
    plan = Plan(goal="g", steps=[{"action": "a", "tool": "nope", "purpose": "p"}])
    text = plan.prompt_text(["project_overview"])
    assert "不可用" in text
