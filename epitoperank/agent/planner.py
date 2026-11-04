"""Planner and critic roles for the analysis copilot.

A single ReAct loop is a good default, but it has two weaknesses that show up
as soon as the question is non-trivial:

* the model starts calling tools before deciding *what evidence would settle
  the question*, so it wanders and burns budget;
* nothing checks the final prose against the tool results, so a confident
  paragraph can contain an unverified number or skip a promised step.

This module adds the two missing roles:

``make_plan``
    one cheap structured call that turns the question into 2-5 evidence steps,
    success criteria and known risks.  Falls back to a deterministic plan when
    no model is configured or the reply is malformed.

``critique_answer``
    deterministic checks (tool coverage, grounding severity, required answer
    sections) plus an optional model review.  The copilot may run exactly one
    revision pass when the critic finds a high-severity issue.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from epitoperank.llm.chat import ChatClient, ChatError
from epitoperank.llm.structured import validate_schema

logger = logging.getLogger(__name__)

#: The four sections every copilot answer must contain.
REQUIRED_SECTIONS = ("结论", "关键证据", "建议的下一步", "局限")


def loads_json(text: str) -> Any:
    """Parse JSON even when the model wrapped it in a Markdown code fence."""
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[A-Za-z0-9_-]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        start, end = raw.find("{"), raw.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(raw[start:end + 1])
            except ValueError:
                return None
    return None

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["goal", "steps"],
    "properties": {
        "goal": {"type": "string"},
        "steps": {
            "type": "array",
            "minItems": 1,
            "maxItems": 6,
            "items": {
                "type": "object",
                "required": ["action"],
                "properties": {
                    "action": {"type": "string"},
                    "tool": {"type": "string"},
                    "arguments": {"type": "object"},
                    "purpose": {"type": "string"},
                },
            },
        },
        "success_criteria": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
    },
}

CRITIQUE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["verdict", "issues"],
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "revise"]},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["severity", "problem"],
                "properties": {
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "problem": {"type": "string"},
                    "fix": {"type": "string"},
                },
            },
        },
        "missing_evidence": {"type": "array", "items": {"type": "string"}},
    },
}

#: Keyword -> tool hints used by the deterministic planner.
TOOL_HINTS: tuple[tuple[tuple[str, ...], str, dict[str, Any]], ...] = (
    (("肽", "hla", "mhc", "新抗原", "neoantigen", "epitope", "表位"),
     "predict_peptides", {}),
    (("文献", "paper", "pubmed", "研究", "报道", "literature"), "search_literature", {}),
    (("通路", "富集", "go ", "kegg", "reactome", "pathway"), "enrichment_summary", {}),
    (("基因", "gene", "注释", "annotation", "功能"), "annotate_gene", {}),
    (("质量", "分组", "样本", "quality", "batch", "confound"), "dataset_quality", {}),
    (("候选", "排序", "rank", "top"), "top_candidates", {}),
)

PLANNER_PROMPT = """你是分析规划器。给定用户问题、项目状态和工具目录，产出一个 2-5 步的证据计划。

规则：
1. 每一步只做一件事，并写明要调用的工具名；工具必须在目录里。
2. 计划只覆盖回答该问题真正需要的事实，不要为了“全面”堆步骤。
3. success_criteria 写可判定的条件（例如“给出 top 5 候选及其 FDR”）。
4. risks 写数据层面的风险（无配对正常、样本量小、只有子集事件等）。
5. 只输出 JSON，不要 Markdown。"""

CRITIC_PROMPT = """你是科学审稿人。检查下面的回答是否被工具结果支持。

只关注四件事：
1. 回答里的数字/基因名/通路名是否出现在工具结果里；不在就报 high。
2. 计划中承诺的证据步骤是否真的执行了；缺了报 medium。
3. 是否缺少“结论/关键证据/建议的下一步/局限”四段之一；缺了报 low。
4. 是否把结合预测说成呈递/免疫原性，或把相关性说成因果；出现就报 high。
5. 工具结果摘要是压缩过的：摘要里没出现的数字不等于未溯源。数字溯源由程序完成且是
   权威判断；若“数字溯源检查”为 ok，不要以“数字未出现在工具结果中”为 high。

只输出 JSON：{"verdict":"pass|revise","issues":[{"severity":"low|medium|high","problem":"...","fix":"..."}],"missing_evidence":["..."]}"""


@dataclass
class Plan:
    goal: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    source: str = "heuristic"

    def as_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": self.steps,
            "success_criteria": self.success_criteria,
            "risks": self.risks,
            "source": self.source,
        }

    def prompt_text(self, available_tools: Sequence[str]) -> str:
        lines = ["## 本轮证据计划", f"目标：{self.goal}", "步骤："]
        for index, step in enumerate(self.steps, start=1):
            tool = step.get("tool") or "-"
            if tool not in available_tools:
                tool = "（不可用，改用可用工具）"
            purpose = step.get("purpose") or step.get("action") or ""
            lines.append(f"{index}. {step.get('action', '')} | 工具：{tool} | {purpose}")
        if self.success_criteria:
            lines.append("完成标准：" + "；".join(self.success_criteria))
        if self.risks:
            lines.append("风险：" + "；".join(self.risks))
        return "\n".join(lines)


def _tool_names(tools: Sequence[Mapping[str, Any]]) -> list[str]:
    names = []
    for spec in tools:
        function = spec.get("function") if isinstance(spec, Mapping) else None
        if isinstance(function, Mapping) and function.get("name"):
            names.append(str(function["name"]))
        elif isinstance(spec, Mapping) and spec.get("name"):
            names.append(str(spec["name"]))
    return names


def heuristic_plan(message: str, *, project_id: str | None,
                   tools: Sequence[Mapping[str, Any]]) -> Plan:
    """Deterministic plan used offline or when the planner reply is unusable."""
    available = set(_tool_names(tools))
    text = (message or "").lower()
    steps: list[dict[str, Any]] = []
    if project_id and "project_overview" in available:
        steps.append({"action": "读取项目概览", "tool": "project_overview", "arguments": {},
                      "purpose": "确认事件量、样本分组与已有产物"})
    for keywords, tool, arguments in TOOL_HINTS:
        if tool in available and any(keyword in text for keyword in keywords):
            steps.append({"action": f"调用 {tool}", "tool": tool, "arguments": arguments,
                          "purpose": "补齐该问题需要的证据"})
    if not steps:
        for tool in ("project_overview", "dataset_quality", "top_candidates"):
            if tool in available:
                steps.append({"action": f"调用 {tool}", "tool": tool, "arguments": {},
                              "purpose": "先建立数据事实基线"})
                break
    if len(steps) < 2 and "query_events" in available:
        steps.append({"action": "检索显著事件", "tool": "query_events",
                      "arguments": {"significant_only": True, "limit": 20},
                      "purpose": "给出可引用的显著事件"})
    return Plan(
        goal=(message or "回答分析问题")[:200],
        steps=steps[:5],
        success_criteria=["每个结论都能在工具结果中找到对应数字或标识"],
        risks=["没有配对正常样本时不能声称肿瘤特异", "样本量小时复现率不可当作硬门槛"],
        source="heuristic",
    )


def _tool_catalogue(tools: Sequence[Mapping[str, Any]]) -> str:
    lines = []
    for spec in tools:
        function = spec.get("function") if isinstance(spec, Mapping) else None
        if not isinstance(function, Mapping):
            continue
        params = (function.get("parameters") or {}).get("properties") or {}
        lines.append(f"- {function.get('name')}: {function.get('description', '')[:160]}"
                     f" | 参数: {', '.join(params) if params else '无'}")
    return "\n".join(lines)


def _as_text(value: Any, limit: int = 300) -> str:
    """Coerce a model-provided scalar into trimmed text."""
    if isinstance(value, str):
        return value.strip()[:limit]
    if isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)):
        return str(value)[:limit]
    return ""


def _string_list(value: Any, *, limit: int = 6, max_len: int = 200) -> list[str]:
    """Normalise a list-ish model field into deduplicated strings."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, (int, float)) and not isinstance(item, bool):
            text = str(item)
        elif isinstance(item, Mapping):
            text = _as_text(item.get("problem") or item.get("text")
                            or item.get("title") or item.get("risk"), max_len)
        else:
            text = ""
        if text and text[:max_len] not in result:
            result.append(text[:max_len])
        if len(result) >= limit:
            break
    return result


def _normalize_plan_payload(payload: Mapping[str, Any], message: str,
                            available: set[str]) -> dict[str, Any] | None:
    """Accept the small shape variations real models produce for a plan.

    Observed in production: ``plan`` instead of ``steps``, ``step`` as an
    integer, ``success_criteria`` per step and ``risks_extra`` at the top
    level.  Normalising here keeps schema validation strict without throwing
    away a usable plan.
    """
    raw_steps: list[Any] | None = None
    for key in ("steps", "plan", "tasks"):
        candidate = payload.get(key)
        if isinstance(candidate, list) and candidate:
            raw_steps = candidate
            break
    if raw_steps is None:
        return None

    steps: list[dict[str, Any]] = []
    step_criteria: list[str] = []
    for index, raw in enumerate(raw_steps, start=1):
        if isinstance(raw, str):
            action = raw.strip()
            if not action:
                continue
            steps.append({"action": action[:200], "tool": "", "arguments": {}, "purpose": ""})
            continue
        if not isinstance(raw, Mapping):
            continue
        action_value = raw.get("action") or raw.get("title")
        if action_value:
            action = _as_text(action_value, 200)
        else:
            step_value = raw.get("step")
            if isinstance(step_value, str) and step_value.strip():
                action = step_value.strip()[:200]
            else:
                action = f"步骤 {index}"
        purpose = _as_text(
            raw.get("purpose") or raw.get("success_criteria")
            or raw.get("description") or raw.get("goal"), 300,
        )
        criteria = raw.get("success_criteria")
        if isinstance(criteria, str) and criteria.strip():
            step_criteria.append(criteria.strip()[:200])
        arguments = raw.get("arguments")
        if not isinstance(arguments, Mapping):
            arguments = {}
        tool = _as_text(raw.get("tool") or raw.get("tool_name"), 80)
        steps.append({
            "action": action,
            "tool": tool if tool in available else "",
            "arguments": dict(arguments),
            "purpose": purpose,
        })
    if not steps:
        return None
    steps = steps[:6]

    goal = _as_text(payload.get("goal") or payload.get("objective") or message, 300)
    top_criteria = _string_list(payload.get("success_criteria"), limit=6)
    success_criteria = top_criteria or step_criteria[:6]

    risks = _string_list(payload.get("risks"), limit=6)
    for item in _string_list(payload.get("risks_extra"), limit=6):
        if item not in risks and len(risks) < 6:
            risks.append(item)

    return {
        "goal": goal or (message or "回答分析问题")[:300],
        "steps": steps,
        "success_criteria": success_criteria,
        "risks": risks,
    }


def _normalize_critique_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Accept string issues, ``review`` text and a missing verdict."""
    issues: list[dict[str, str]] = []

    def add(problem: Any, severity: Any = "medium", fix: Any = "") -> None:
        text = _as_text(problem, 300)
        if not text:
            return
        level = str(severity or "medium").strip().lower()
        if level not in {"low", "medium", "high"}:
            level = "medium"
        item = {"severity": level, "problem": text, "fix": _as_text(fix, 300)}
        if item not in issues and len(issues) < 8:
            issues.append(item)

    raw_issues = payload.get("issues")
    if isinstance(raw_issues, list):
        for item in raw_issues:
            if isinstance(item, str):
                add(item)
            elif isinstance(item, Mapping):
                add(item.get("problem") or item.get("review") or item.get("issue")
                    or item.get("message") or item.get("title"),
                    item.get("severity"), item.get("fix"))
    elif isinstance(raw_issues, Mapping):
        add(raw_issues.get("problem") or raw_issues.get("review"),
            raw_issues.get("severity"), raw_issues.get("fix"))
    elif isinstance(raw_issues, str):
        add(raw_issues)

    # A bare {"review": "..."} is a problem statement, not a verdict.
    add(payload.get("review"), payload.get("severity"))

    verdict = payload.get("verdict")
    if verdict not in {"pass", "revise"}:
        verdict = "revise" if any(item["severity"] == "high" for item in issues) else "pass"
    return {
        "verdict": verdict,
        "issues": issues[:8],
        "missing_evidence": _string_list(payload.get("missing_evidence"), limit=8),
    }


def _structured_call(client: ChatClient, system: str, user: str, *,
                     max_tokens: int = 1800) -> Mapping[str, Any] | None:
    """Ask for JSON, retrying without chain-of-thought if the reply is unusable.

    DeepSeek's thinking mode can consume the whole completion budget, and with
    thinking forced off the JSON quality occasionally drops. Trying the normal
    mode first and a no-thinking retry second is the pragmatic compromise.
    """
    for thinking in (None, "disabled"):
        try:
            result = client.complete(
                [{"role": "system", "content": system},
                 {"role": "user", "content": user}],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=max_tokens,
                thinking=thinking,
            )
        except ChatError:
            continue
        if os.getenv("EPITOPERANK_DEBUG_STRUCTURED"):
            logger.warning("structured reply thinking=%s finish=%s text=%r",
                           thinking, result.finish_reason, (result.text or "")[:600])
        payload = loads_json(result.text)
        if isinstance(payload, Mapping):
            return payload
    return None


def make_plan(message: str, settings: Any, client: ChatClient | None, *,
              project_id: str | None, tools: Sequence[Mapping[str, Any]],
              history: Sequence[Mapping[str, Any]] | None = None) -> Plan:
    """Ask the model for an evidence plan, falling back to the heuristic one."""
    fallback = heuristic_plan(message, project_id=project_id, tools=tools)
    if client is None or not getattr(client, "available", False):
        return fallback
    context = f"当前项目：{project_id or '未选择'}。"
    recent = ""
    for item in list(history or [])[-4:]:
        if isinstance(item, Mapping) and item.get("content"):
            recent += f"\n[{item.get('role')}] {str(item.get('content'))[:300]}"
    prompt = (
        f"{context}\n工具目录：\n{_tool_catalogue(tools)}\n\n"
        f"最近对话：{recent or '无'}\n\n用户问题：{message[:2000]}"
    )
    payload = _structured_call(client, PLANNER_PROMPT, prompt, max_tokens=1800)
    if not isinstance(payload, Mapping):
        return fallback
    available = set(_tool_names(tools))
    normalized = _normalize_plan_payload(payload, message, available)
    if normalized is None:
        return fallback
    if validate_schema(normalized, PLAN_SCHEMA):
        return fallback
    return Plan(
        goal=normalized["goal"],
        steps=normalized["steps"],
        success_criteria=normalized["success_criteria"],
        risks=normalized["risks"],
        source="llm",
    )


def deterministic_critique(answer: str, *, tool_calls: Sequence[Mapping[str, Any]],
                           grounding: Mapping[str, Any], plan: Plan | None,
                           project_id: str | None) -> dict[str, Any]:
    """Cheap checks that do not need a model."""
    issues: list[dict[str, str]] = []
    missing: list[str] = []
    if project_id and not tool_calls:
        issues.append({"severity": "high", "problem": "没有读取任何项目数据就给出结论",
                       "fix": "先调用 project_overview / dataset_quality"})
    if grounding.get("severity") == "warn":
        unverified = [str(item) for item in grounding.get("unverified") or []]
        issues.append({"severity": "high",
                       "problem": ("以下数字未在工具结果中出现：" + ", ".join(unverified[:10]))
                       if unverified else "回答中的数字未在工具结果中出现",
                       "fix": "删除或核对未溯源数字"})
    elif grounding.get("severity") == "review":
        issues.append({"severity": "medium", "problem": "少量数字未在工具结果中出现",
                       "fix": "逐条核对"})
    if plan is not None:
        called = {str(call.get("tool")) for call in tool_calls}
        for step in plan.steps:
            tool = step.get("tool")
            if tool and tool not in called:
                missing.append(str(tool))
        if missing:
            issues.append({"severity": "medium",
                           "problem": "计划中的工具未执行：" + ", ".join(sorted(set(missing))),
                           "fix": "执行或从回答中删除对应结论"})
    for section in REQUIRED_SECTIONS:
        if f"## {section}" not in (answer or ""):
            issues.append({"severity": "low", "problem": f"缺少「{section}」段落",
                           "fix": f"补上 {section}"})
            break
    verdict = "revise" if any(item["severity"] == "high" for item in issues) else "pass"
    return {"verdict": verdict, "issues": issues, "missing_evidence": sorted(set(missing)),
            "source": "heuristic"}


def critique_answer(message: str, answer: str, *, settings: Any, client: ChatClient | None,
                    plan: Plan | None, tool_calls: Sequence[Mapping[str, Any]],
                    grounding: Mapping[str, Any], project_id: str | None) -> dict[str, Any]:
    """Deterministic critique plus an optional model review."""
    base = deterministic_critique(answer, tool_calls=tool_calls, grounding=grounding,
                                  plan=plan, project_id=project_id)
    if client is None or not getattr(client, "available", False):
        return base
    facts = "\n".join(
        f"- {call.get('tool')}({json.dumps(call.get('arguments') or {}, ensure_ascii=False)[:160]})"
        f" -> {str(call.get('summary') or call.get('error') or '')[:220]}"
        for call in tool_calls[-12:]
    )
    prompt = (
        f"用户问题：{message[:1200]}\n\n工具调用与结果：\n{facts or '无'}\n\n"
        f"回答全文：\n{answer[:5000]}\n\n"
        f"数字溯源检查：{json.dumps(grounding, ensure_ascii=False)[:800]}"
    )
    payload = _structured_call(client, CRITIC_PROMPT, prompt, max_tokens=1600)
    if not isinstance(payload, Mapping):
        return base
    normalized = _normalize_critique_payload(payload)
    if validate_schema(normalized, CRITIQUE_SCHEMA):
        return base
    called = {str(call.get("tool")) for call in tool_calls}
    missing_tools = ([str(step.get("tool")) for step in plan.steps
                      if step.get("tool") and step.get("tool") not in called]
                     if plan is not None else [])
    issues = []
    for item in normalized["issues"]:
        entry = dict(item)
        if entry["severity"] == "high":
            problem = entry["problem"].lower()
            # The deterministic grounding check is authoritative for numbers:
            # a critic that cannot see the full tables must not block a
            # verified answer on a "number not grounded" claim.
            if grounding.get("severity") == "ok" and any(
                    marker in problem for marker in
                    ("数字", "number", "溯源", "ground", "统计量", "fdr", "百分位")):
                entry["severity"] = "medium"
            elif not missing_tools and any(
                    marker in problem for marker in ("未执行", "missing", "not executed", "没有调用")):
                entry["severity"] = "medium"
        issues.append(entry)
    # Never let the model downgrade a deterministic high-severity finding.
    for item in base["issues"]:
        if item["severity"] == "high" and item not in issues:
            issues.append(item)
    # Revisions are expensive and can degrade a good answer; only a concrete
    # high-severity issue (deterministic or semantic) justifies one.
    verdict = "revise" if any(item["severity"] == "high" for item in issues) else "pass"
    return {
        "verdict": verdict,
        "issues": issues[:8],
        "missing_evidence": normalized["missing_evidence"][:8],
        "source": "llm",
    }


def revision_instruction(critique: Mapping[str, Any]) -> str:
    """User-turn text that asks for a corrected final answer."""
    lines = ["上一版回答没有通过审稿，请只修正问题、不要新增未经工具验证的内容："]
    for item in critique.get("issues") or []:
        lines.append(f"- [{item.get('severity')}] {item.get('problem')} → {item.get('fix') or '删除或核对'}")
    lines.append("保持四段式（结论 / 关键证据 / 建议的下一步 / 局限）。")
    return "\n".join(lines)
