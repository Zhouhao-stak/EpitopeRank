"""Evaluation harness for the analysis copilot.

Agent quality is not a vibe; it is a set of measurable behaviours:

* did it call the tools a competent analyst would call?
* did it avoid irrelevant tools?
* did it keep its numbers grounded in tool results?
* did it keep the required answer structure?
* how much latency and how many tokens did that cost?

``evaluate`` runs a golden set of questions through the real copilot loop.  In
CI it uses :class:`~splicegaip.llm.scripted.ScriptedChat`, so the harness is
deterministic and free; with a configured model the same cases become a live
regression suite.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from splicegaip.agent.copilot import CopilotAnswer, ask
from splicegaip.agent.planner import REQUIRED_SECTIONS
from splicegaip.config import Settings
from splicegaip.llm.scripted import ScriptedChat

FINAL_ANSWER = (
    "## 结论\n"
    "已读取项目数据；以下判断只基于工具返回的结果。\n\n"
    "## 关键证据\n"
    "见本次调用记录中的工具结果。\n\n"
    "## 建议的下一步\n"
    "先核对分组与样本量，再决定是否做外部证据核对。\n\n"
    "## 局限\n"
    "本回答没有新增未经工具验证的数字或外部证据。"
)


@dataclass
class Case:
    id: str
    message: str
    expected_tools: list[str] = field(default_factory=list)
    forbid_tools: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=lambda: list(REQUIRED_SECTIONS))
    project_required: bool = True
    strategy: str = "react"
    tool_arguments: dict[str, dict[str, Any]] = field(default_factory=dict)
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "message": self.message,
            "expected_tools": self.expected_tools,
            "forbid_tools": self.forbid_tools,
            "sections": self.sections,
            "project_required": self.project_required,
            "strategy": self.strategy,
            "notes": self.notes,
        }


def load_cases(path: str | Path) -> list[Case]:
    """Read a JSONL golden set."""
    cases: list[Case] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                payload = json.loads(line)
            except ValueError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {error}") from error
            if not isinstance(payload, Mapping) or not payload.get("id") or not payload.get("message"):
                raise ValueError(f"{path}:{line_number}: case requires id and message")
            cases.append(Case(
                id=str(payload["id"]),
                message=str(payload["message"]),
                expected_tools=[str(item) for item in payload.get("expected_tools") or []],
                forbid_tools=[str(item) for item in payload.get("forbid_tools") or []],
                sections=[str(item) for item in payload.get("sections") or REQUIRED_SECTIONS],
                project_required=bool(payload.get("project_required", True)),
                strategy=str(payload.get("strategy") or "react"),
                tool_arguments=dict(payload.get("tool_arguments") or {}),
                notes=str(payload.get("notes") or ""),
            ))
    if not cases:
        raise ValueError(f"no cases in {path}")
    return cases


def script_for_case(case: Case) -> list[dict[str, Any]]:
    """Turn expected tools into a scripted model transcript."""
    plan_payload = {
        "goal": case.message[:160],
        "steps": [
            {"action": f"调用 {tool}", "tool": tool,
             "arguments": case.tool_arguments.get(tool, {}), "purpose": "收集证据"}
            for tool in case.expected_tools
        ] or [{"action": "读取项目概览", "tool": "project_overview", "arguments": {},
               "purpose": "建立事实基线"}],
        "success_criteria": ["每个结论都有工具结果支持"],
        "risks": ["样本分组或配对关系可能不完整"],
    }
    tool_step = {
        "tools": [
            {"name": tool, "arguments": case.tool_arguments.get(tool, {})}
            for tool in case.expected_tools
        ]
    }
    script: list[dict[str, Any]] = []
    if case.strategy == "plan":
        script.append({"text": json.dumps(plan_payload, ensure_ascii=False)})
    script.append(tool_step)
    script.append({"text": FINAL_ANSWER})
    if case.strategy == "plan":
        script.append({"text": json.dumps({"verdict": "pass", "issues": []})})
    return script


def run_case(case: Case, settings: Settings, *, project_id: str | None = None,
             chat: Any | None = None, force_offline: bool = False,
             allow_network: bool = False) -> CopilotAnswer:
    """Run one case through the real copilot loop."""
    if chat is None:
        chat = ScriptedChat(script=script_for_case(case))
    return ask(
        case.message,
        settings,
        project_id=project_id if case.project_required else None,
        client=chat,
        force_offline=force_offline,
        mode=case.strategy,
        allow_network=allow_network and not force_offline,
    )


def score(case: Case, answer: CopilotAnswer) -> dict[str, Any]:
    called = [str(call.get("tool")) for call in answer.tool_calls]
    expected = set(case.expected_tools)
    forbidden = set(case.forbid_tools)
    hits = expected & set(called)
    recall = len(hits) / len(expected) if expected else 1.0
    precision = len(hits) / len(set(called)) if called else 1.0
    sections_ok = all(f"## {section}" in (answer.answer or "") for section in case.sections)
    grounding_ok = (answer.grounding or {}).get("severity") == "ok"
    forbidden_hits = sorted(forbidden & set(called))
    passed = recall >= 0.8 and not forbidden_hits and sections_ok and grounding_ok
    return {
        "id": case.id,
        "passed": passed,
        "tool_recall": round(recall, 3),
        "tool_precision": round(precision, 3),
        "missing_tools": sorted(expected - set(called)),
        "unexpected_tools": sorted(set(called) - expected),
        "forbidden_hits": forbidden_hits,
        "sections_ok": sections_ok,
        "grounding_ok": grounding_ok,
        "grounding_severity": (answer.grounding or {}).get("severity"),
        "mode": answer.mode,
        "strategy": answer.strategy,
        "steps": answer.steps,
        "tool_calls": len(called),
        "cache_hits": sum(1 for call in answer.tool_calls if call.get("cached")),
        "elapsed_seconds": answer.elapsed_seconds,
        "tokens": (answer.usage or {}).get("total_tokens", 0),
        "critique_verdict": (answer.critique or {}).get("verdict"),
        "errors": answer.errors[:3],
    }


def evaluate(cases: Sequence[Case], settings: Settings, *,
             project_id: str | None = None,
             chat_factory: Callable[[Case], Any] | None = None,
             force_offline: bool = False,
             allow_network: bool = False,
             progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Run every case and aggregate the metrics."""
    started = time.monotonic()
    rows: list[dict[str, Any]] = []
    for case in cases:
        try:
            chat = chat_factory(case) if chat_factory else None
            answer = run_case(case, settings, project_id=project_id, chat=chat,
                              force_offline=force_offline, allow_network=allow_network)
            row = score(case, answer)
        except Exception as error:  # noqa: BLE001 - a broken case must not stop the suite
            row = {"id": case.id, "passed": False, "error": f"{type(error).__name__}: {error}",
                   "tool_recall": 0.0, "tool_precision": 0.0, "sections_ok": False,
                   "grounding_ok": False, "tool_calls": 0, "cache_hits": 0,
                   "elapsed_seconds": 0.0, "tokens": 0}
        rows.append(row)
        if progress is not None:
            progress(row)

    def average(key: str) -> float:
        values = [float(row.get(key) or 0.0) for row in rows]
        return round(sum(values) / len(values), 3) if values else 0.0

    summary = {
        "case_count": len(rows),
        "passed": sum(1 for row in rows if row.get("passed")),
        "pass_rate": round(sum(1 for row in rows if row.get("passed")) / len(rows), 3) if rows else 0.0,
        "avg_tool_recall": average("tool_recall"),
        "avg_tool_precision": average("tool_precision"),
        "grounding_ok_rate": round(sum(1 for row in rows if row.get("grounding_ok")) / max(len(rows), 1), 3),
        "sections_ok_rate": round(sum(1 for row in rows if row.get("sections_ok")) / max(len(rows), 1), 3),
        "total_tool_calls": sum(int(row.get("tool_calls") or 0) for row in rows),
        "total_cache_hits": sum(int(row.get("cache_hits") or 0) for row in rows),
        "total_tokens": sum(int(row.get("tokens") or 0) for row in rows),
        "avg_elapsed_seconds": average("elapsed_seconds"),
        "elapsed_seconds": round(time.monotonic() - started, 2),
    }
    return {
        "cases": rows,
        "summary": summary,
        "project_id": project_id,
        "force_offline": force_offline,
        "allow_network": allow_network,
    }


def write_report(payload: Mapping[str, Any], output_dir: str | Path) -> dict[str, str]:
    """Write the JSON payload and a human-readable Markdown table."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "agent_eval.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Copilot evaluation",
        "",
        f"- cases: {payload['summary']['case_count']}",
        f"- pass rate: {payload['summary']['pass_rate']}",
        f"- tool recall: {payload['summary']['avg_tool_recall']}",
        f"- tool precision: {payload['summary']['avg_tool_precision']}",
        f"- grounding ok: {payload['summary']['grounding_ok_rate']}",
        f"- sections ok: {payload['summary']['sections_ok_rate']}",
        f"- tokens: {payload['summary']['total_tokens']}",
        f"- elapsed: {payload['summary']['elapsed_seconds']} s",
        "",
        "| case | pass | recall | precision | grounding | sections | tools | tokens |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["cases"]:
        lines.append(
            "| {id} | {passed} | {recall} | {precision} | {ground} | {sections} | {tools} | {tokens} |".format(
                id=row.get("id"), passed="✅" if row.get("passed") else "❌",
                recall=row.get("tool_recall"), precision=row.get("tool_precision"),
                ground=row.get("grounding_ok"), sections=row.get("sections_ok"),
                tools=row.get("tool_calls"), tokens=row.get("tokens"),
            )
        )
    markdown_path = target / "agent_eval.md"
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(markdown_path)}
