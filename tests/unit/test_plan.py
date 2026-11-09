"""Reviewable plan contract, deviations and reproducibility proof."""
from __future__ import annotations

import pytest

from epitoperank.agent.actions import build_registry
from epitoperank.agent.plan import (
    AnalysisPlan,
    build_plan,
    plan_deviations,
    reproducibility_proof,
)
from epitoperank.config import load_settings
from epitoperank.llm.trace import ModelTrace


def test_neoantigen_goal_produces_a_prediction_chain():
    plan = build_plan("为 UPF1 敲低样本找 3 个可验证的 MHC-I 新抗原候选")
    assert plan.intent == "neoantigen"
    assert "mcp__predict_mhc_binding" in plan.expected_tools
    assert "mcp__lookup_epitope" in plan.expected_tools
    assert plan.thresholds["fdr"] == 0.05
    assert plan.budgets["max_steps"] >= 1
    plan.validate_against_registry(build_registry())


def test_generic_goal_stays_on_the_deterministic_chain():
    plan = build_plan("Analyze differential alternative splicing", settings=load_settings())
    assert plan.intent == "differential_AS"
    assert plan.source == "rule"
    assert "filter_significant_events" in plan.expected_tools
    assert not any(name.startswith("mcp__") for name in plan.expected_tools)


def test_from_dict_validates_contract_fields():
    raw = build_plan("Explore the dataset quality").as_dict()
    plan = AnalysisPlan.from_dict(raw)
    assert plan.goal
    raw["thresholds"]["fdr"] = 5
    with pytest.raises(ValueError, match="out of range"):
        AnalysisPlan.from_dict(raw)
    with pytest.raises(ValueError, match="goal"):
        AnalysisPlan.from_dict({})
    raw = build_plan("x").as_dict()
    raw["intent"] = "unknown"
    with pytest.raises(ValueError, match="intent"):
        AnalysisPlan.from_dict(raw)


def test_unknown_tools_are_rejected():
    plan = build_plan("Analyze splicing")
    plan.expected_tools.append("hallucinated_tool")
    with pytest.raises(ValueError, match="unknown tools"):
        plan.validate_against_registry(build_registry())


def test_deviations_expose_data_driven_changes():
    plan = build_plan("Analyze differential alternative splicing")
    steps = [
        {"action": "profile_dataset", "source": "rule", "rationale": "profile first"},
        {"action": "assess_quality", "source": "reflection", "rationale": "quality gate failed"},
        {"action": "mcp__peptide_properties", "source": "llm", "rationale": "model added a check"},
    ]
    view = plan_deviations(plan, steps)
    assert view["available"] is True
    assert view["adherence_ratio"] is not None
    assert view["planned_not_run"]
    assert any(item["action"] == "assess_quality" for item in view["autonomous_additions"])
    assert plan_deviations(None, steps)["available"] is False


def test_proof_bundle_contains_fingerprints_integrity_and_replay_command():
    plan = build_plan("Find MHC-I neoantigen candidates")
    state = {
        "steps": [{"action": "profile_dataset", "source": "rule"},
                  {"action": "mcp__predict_mhc_binding", "source": "llm"}],
        "model_calls": [{"seq": 0}], "tool_calls": [{"seq": 0}],
        "params": {}, "errors": [],
        "meta": {"schema_version": 1, "integrity": None, "query": "q",
                 "project_id": "P1", "input_dir": "E:/data",
                 "state_path": "E:/state/agent_state.json",
                 "input_fingerprints": {"SE.txt": "sha"},
                 "reports": {"html": "cafe"},
                 "analysis_plan": plan.as_dict()},
    }
    state["meta"]["integrity"] = ModelTrace.checksum(state)
    proof = reproducibility_proof(state)
    assert proof["integrity_ok"] is True
    assert proof["input_fingerprints"] == {"SE.txt": "sha"}
    assert proof["trajectory"]["tool_calls"] == 1
    assert proof["plan"]["intent"] == "neoantigen"
    assert "run.py replay" in proof["replay_command"]
    assert proof["deviations"]["available"] is True
    state["steps"].append({"action": "extra", "source": "rule"})
    assert reproducibility_proof(state)["integrity_ok"] is False
