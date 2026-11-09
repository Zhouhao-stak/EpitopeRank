"""Reviewable analysis-plan contract and reproducibility proof.

A natural-language objective is turned into an explicit, editable plan before
any work starts: which tools may run, which thresholds apply, what outputs are
expected and what the hard budgets are. The approved plan is persisted into
``agent_state.json`` so a run can later be audited against its own contract.

The plan is a *contract*, not a script: the OODA loop may deviate from it when
the data demands it. Deviations are recorded explicitly instead of being hidden.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from epitoperank.llm.trace import ModelTrace

NEOANTIGEN_RE = re.compile(r"neoantigen|新抗原|peptide|肽|MHC|HLA|vaccine|疫苗", re.I)
EXPLORATION_RE = re.compile(r"explor|探索|overview|概览|quality|质控|survey", re.I)

BASE_TOOLS = (
    "profile_dataset", "summarize_dataset", "filter_significant_events",
    "rank_candidates", "test_hypothesis", "generate_figures",
    "collect_literature_evidence", "interpret_candidates", "generate_report",
)
NEOANTIGEN_TOOLS = (
    "mcp__peptide_capabilities", "mcp__peptide_properties",
    "mcp__predict_mhc_binding", "mcp__lookup_epitope",
)
EXPLORATION_TOOLS = ("assess_quality", "consult_knowledge")


@dataclass
class AnalysisPlan:
    """An editable analysis contract, persisted with the run."""

    goal: str
    intent: str
    thresholds: dict[str, Any] = field(default_factory=dict)
    expected_tools: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    budgets: dict[str, Any] = field(default_factory=dict)
    source: str = "rule"
    created_at: str = ""
    notes: list[str] = field(default_factory=list)

    # 中文备注：序列化为字典（参数：无）
    def as_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal, "intent": self.intent,
            "thresholds": dict(self.thresholds),
            "expected_tools": list(self.expected_tools),
            "expected_outputs": list(self.expected_outputs),
            "budgets": dict(self.budgets), "source": self.source,
            "created_at": self.created_at, "notes": list(self.notes),
        }

    @classmethod
    # 中文备注：从字典构造对象（参数：raw）
    def from_dict(cls, raw: Any) -> "AnalysisPlan":
        if not isinstance(raw, dict):
            raise ValueError("plan must be a JSON object")
        goal = str(raw.get("goal") or "").strip()[:600]
        if not goal:
            raise ValueError("plan.goal is required")
        intent = str(raw.get("intent") or "differential_AS")
        if intent not in {"differential_AS", "neoantigen", "exploration"}:
            raise ValueError("unsupported plan.intent")
        # 中文备注：智能体内核：列出string（参数：key、limit）
        def string_list(key, limit=40):
            value = raw.get(key) or []
            if not isinstance(value, list):
                raise ValueError(f"plan.{key} must be a list")
            return [str(item)[:120] for item in value[:limit]]
        thresholds = raw.get("thresholds") or {}
        budgets = raw.get("budgets") or {}
        if not isinstance(thresholds, dict) or not isinstance(budgets, dict):
            raise ValueError("plan thresholds/budgets must be objects")
        for key in ("fdr", "delta_psi"):
            if key in thresholds:
                value = float(thresholds[key])
                if not 0 < value < 1:
                    raise ValueError(f"plan.thresholds.{key} out of range")
                thresholds[key] = value
        return cls(
            goal=goal, intent=intent, thresholds=dict(thresholds),
            expected_tools=string_list("expected_tools"),
            expected_outputs=string_list("expected_outputs"),
            budgets=dict(budgets),
            source=str(raw.get("source") or "user")[:20],
            created_at=str(raw.get("created_at") or "")[:40],
            notes=string_list("notes", 10),
        )

    # 中文备注：智能体内核：校验against注册表（参数：registry）
    def validate_against_registry(self, registry: dict[str, Any]) -> None:
        """Reject unknown tool names so an edited plan cannot invent actions."""
        unknown = [name for name in self.expected_tools if name not in registry]
        if unknown:
            raise ValueError("unknown tools in plan: " + ", ".join(unknown[:8]))


# 中文备注：由自然语言目标生成可审阅的分析计划（参数：query、settings、enhancer）
def build_plan(query: str, *, settings: Any = None, enhancer: Any = None) -> AnalysisPlan:
    """Build a deterministic plan from the objective; optionally refine wording.

    Thresholds and budgets always come from local configuration, never from the
    model, so the contract remains reproducible. A model may only shorten the
    tool list and rewrite the goal sentence; every suggestion is filtered
    against the actual action registry.
    """
    from epitoperank.agent.actions import build_registry

    registry = build_registry()
    text = str(query or "").strip() or "Analyze differential alternative splicing"
    if NEOANTIGEN_RE.search(text):
        intent = "neoantigen"
        tools = list(BASE_TOOLS[:-1]) + list(NEOANTIGEN_TOOLS) + [BASE_TOOLS[-1]]
        outputs = ["ranked splicing events", "candidate peptide table",
                   "MHC binding predictions", "HTML report"]
    elif EXPLORATION_RE.search(text):
        intent = "exploration"
        tools = ["profile_dataset", "assess_quality", "summarize_dataset",
                 "consult_knowledge", "generate_figures", "generate_report"]
        outputs = ["dataset profile", "quality assessment", "HTML report"]
    else:
        intent = "differential_AS"
        tools = list(BASE_TOOLS)
        outputs = ["ranked splicing events", "enrichment terms",
                   "publication figures", "HTML report"]
    tools = [name for name in tools if name in registry]

    analysis = getattr(settings, "analysis", None)
    agent = getattr(settings, "agent", None)
    thresholds = {
        "fdr": float(getattr(analysis, "fdr_threshold", 0.05)),
        "delta_psi": float(getattr(analysis, "delta_psi_threshold", 0.1)),
        "min_support_reads": int(getattr(analysis, "min_support_reads", 10)),
        "top_candidates": int(getattr(analysis, "top_candidates", 20)),
    }
    budgets = {
        "max_steps": int(getattr(agent, "max_steps", 20)),
        "max_seconds": int(getattr(agent, "max_seconds", 900)),
        "max_errors": int(getattr(agent, "max_errors", 3)),
        "plan_budget": int(getattr(agent, "plan_budget", 8)),
    }
    plan = AnalysisPlan(
        goal=text[:600], intent=intent, thresholds=thresholds,
        expected_tools=tools, expected_outputs=outputs, budgets=budgets,
        source="rule", created_at=datetime.now(timezone.utc).isoformat(),
        notes=["Thresholds and budgets come from config, not from the model."],
    )

    if enhancer is not None and getattr(enhancer, "enabled", False):
        from epitoperank.llm.trace import model_request

        payload = {"goal": plan.goal, "intent": plan.intent,
                   "candidate_tools": tools, "thresholds": thresholds}
        try:
            raw = model_request(
                enhancer, stage="analysis_plan",
                system=("You review an analysis plan. Reply with JSON only: "
                        '{"goal":"<one sentence>","tools":["<subset of candidate_tools>"]}. '
                        "Keep every tool name exactly as given; do not invent tools."),
                user=json.dumps(payload, ensure_ascii=False)[:3000],
                max_tokens=300, json_output=True, timeout=60)
            parsed = json.loads(str(raw or ""))
            if isinstance(parsed, dict):
                goal = str(parsed.get("goal") or "").strip()
                if goal:
                    plan.goal = goal[:600]
                subset = parsed.get("tools")
                if isinstance(subset, list) and subset:
                    keep = [name for name in tools if name in subset]
                    if keep:
                        plan.expected_tools = keep
                plan.source = "llm"
                plan.notes.append("Model refined the goal and tool subset; thresholds unchanged.")
        except Exception:  # noqa: BLE001 - review is advisory, never blocking
            plan.notes.append("Model plan review unavailable; kept the deterministic plan.")
    return plan


# 中文备注：比较计划与实际执行轨迹的偏差（参数：plan、steps）
def plan_deviations(plan: AnalysisPlan | None, steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare the approved contract with what the agent actually did."""
    executed = [str(s.get("action") or "") for s in steps if isinstance(s, dict)]
    if plan is None:
        return {"available": False, "planned_count": 0, "executed_count": len(executed),
                "planned_not_run": [], "autonomous_additions": [], "adherence_ratio": None}
    planned = list(plan.expected_tools)
    planned_set, executed_set = set(planned), set(executed)
    not_run = [name for name in planned if name not in executed_set]
    additions = []
    seen = set()
    for index, (name, step) in enumerate(zip(executed, steps)):
        if name in planned_set or name in seen:
            continue
        seen.add(name)
        additions.append({
            "action": name, "step": index, "source": step.get("source"),
            "reason": str(step.get("rationale") or "data-driven decision")[:200],
        })
    adhered = len([name for name in planned if name in executed_set])
    return {
        "available": True, "planned_count": len(planned),
        "executed_count": len(executed),
        "adherence_ratio": round(adhered / len(planned), 3) if planned else None,
        "planned_not_run": not_run,
        "autonomous_additions": additions[:20],
        "note": "Deviations are expected: the OODA loop reacts to observed facts.",
    }


# 中文备注：汇总一次运行的可复现证明（参数：state）
def reproducibility_proof(state: dict[str, Any]) -> dict[str, Any]:
    """Self-contained, read-only proof bundle for one recorded run."""
    from collections import Counter

    meta = state.get("meta") or {}
    steps = [s for s in (state.get("steps") or []) if isinstance(s, dict)]
    raw_plan = meta.get("analysis_plan")
    plan = None
    if isinstance(raw_plan, dict):
        try:
            plan = AnalysisPlan.from_dict(raw_plan)
        except ValueError:
            plan = None
    recorded = meta.get("integrity")
    input_dir = str(meta.get("input_dir") or "<input-dir>")
    state_path = str(meta.get("state_path") or "<agent_state.json>")
    sources = Counter(str(s.get("source") or "rule") for s in steps)
    return {
        "project_id": meta.get("project_id"), "query": meta.get("query"),
        "schema_version": meta.get("schema_version"),
        "llm_enabled": meta.get("llm_enabled"), "model_name": meta.get("model_name"),
        "input_dir": input_dir,
        "input_fingerprints": meta.get("input_fingerprints") or {},
        "config": meta.get("config") or {},
        "trajectory": {
            "steps": len(steps), "sources": dict(sources),
            "model_calls": len(state.get("model_calls") or []),
            "tool_calls": len(state.get("tool_calls") or []),
        },
        "reports": meta.get("reports") or {},
        "integrity": recorded,
        "integrity_ok": bool(recorded) and recorded == ModelTrace.checksum(state),
        "plan": plan.as_dict() if plan else None,
        "deviations": plan_deviations(plan, steps),
        "replay_command": (
            "venv/Scripts/python.exe run.py replay "
            f'--input "{input_dir}" --trace "{state_path}" --out <out-dir>'),
        "limitations": [
            "Replay uses an isolated runtime state; a shared lab knowledge base "
            "can change enrichment bonuses between runs.",
            "External services (IEDB, PubMed) are consumed from recorded snapshots; "
            "live responses are not guaranteed to be identical.",
        ],
    }
