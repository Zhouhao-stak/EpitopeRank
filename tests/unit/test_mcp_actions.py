"""First-class MCP tools: discovery, schema validation and result write-back."""
from __future__ import annotations

import json

import pytest

from epitoperank.agent.mcp_actions import (
    TOOL_SPECS,
    compact_schema,
    invoke_tool,
    summarize_result,
    validate_args,
)
from epitoperank.agent.actions import build_registry
from epitoperank.config import load_settings
from epitoperank.llm.trace import ACTIVE, ModelTrace, ReplayError


def test_registry_exposes_each_builtin_tool_as_its_own_action():
    registry = build_registry()
    names = {spec["name"] for spec in TOOL_SPECS}
    assert len(names) == 9
    assert names <= set(registry)
    assert registry["call_mcp_tool"].arg_schema is None
    assert registry["mcp__predict_mhc_binding"].arg_schema is not None
    assert len(registry) >= 33


def test_structured_prediction_arguments_are_accepted():
    params = dict(TOOL_SPECS[7])["params"]
    args, dropped = validate_args(params, {
        "peptides": ["NLVPMVATV", "GILGFVFTL"],
        "alleles": ["HLA-A*02:01"],
        "mhc_class": "class2",
        "processing": True,
        "unexpected": "drop me",
    })
    assert args["peptides"] == ["NLVPMVATV", "GILGFVFTL"]
    assert args["mhc_class"] == "class2"
    assert args["processing"] is True
    assert dropped == ["unexpected"]


def test_invalid_peptide_allele_ranges_and_choices_are_dropped():
    params = dict(TOOL_SPECS[7])["params"]
    args, dropped = validate_args(params, {
        "peptides": ["NOT-A-PEPTIDE"], "alleles": ["HLA-A*02:01"],
        "mhc_class": "class9",
    })
    assert "peptides" not in args and "mhc_class" not in args
    assert "peptides" in dropped and "mhc_class" in dropped
    assert "peptides<required-missing>" in dropped
    args2, _ = validate_args(params, {
        "peptides": ["A" * 41], "alleles": ["HLA-A*02:01"]})
    assert "peptides" not in args2
    args3, dropped3 = validate_args(params, {
        "peptides": ["NLVPMVATV"], "alleles": ["not-an-allele"]})
    assert "alleles" not in args3
    assert any("alleles" in item for item in dropped3)


def test_compact_schema_stays_small_for_the_planner_prompt():
    schema = compact_schema(dict(TOOL_SPECS[7])["params"])
    assert schema["peptides"].startswith("list[str]!")
    assert "class1/class2/both" in schema["mhc_class"]
    assert len(json.dumps(schema)) < 300


def test_prediction_and_epitope_results_are_summarised_for_the_blackboard():
    prediction = summarize_result("predict_mhc_binding", {
        "predictions": [{"percentile_rank": 0.06}, {"percentile_rank": 0.9}],
        "errors": []})
    assert prediction["prediction_count"] == 2
    assert prediction["best_percentile"] == 0.06
    assert summarize_result("predict_mhc_binding", {"error": "offline"})["ok"] is False
    matches = summarize_result("lookup_epitope",
                               {"matches": {"NLVPMVATV": [{"assay": "x"}, {}]}})
    assert matches["match_count"] == 2


def test_builtin_tools_run_offline_without_the_mcp_server():
    props = invoke_tool("epitoperank-builtin", "peptide_properties",
                        {"peptides": ["NLVPMVATV"]}, network=False)
    assert props["peptides"][0]["peptide"] == "NLVPMVATV"
    psi = invoke_tool("epitoperank-builtin", "compute_delta_psi",
                      {"group1_psi": 0.2, "group2_psi": 0.7}, network=False)
    assert psi["delta_psi"] == pytest.approx(0.5)
    assert invoke_tool("epitoperank-builtin", "peptide_capabilities",
                       {}, network=False)["predictors"]


def test_mcp_actions_write_structured_results_back_to_facts():
    class DummySettings:
        class Agent:
            allow_network = False
        agent = Agent()

    class DummyContext:
        settings = DummySettings()
        logs = []

        def log(self, *args):
            self.logs.append(args)

    class DummyState:
        facts = {}

    registry = build_registry()
    action = registry["mcp__peptide_properties"]
    context, state = DummyContext(), DummyState()
    result = action.func(context, state, peptides=["NLVPMVATV"])
    assert "peptide_count" in result
    assert state.facts["last_mcp_tool"] == "peptide_properties"
    assert state.facts["mcp_summaries"]["peptide_properties"]["peptide_count"] == 1
    assert state.facts["last_mcp_ok"] is True


def test_tool_call_tape_records_and_replays_without_network(tmp_path):
    settings = load_settings()
    record = ModelTrace(settings)
    token = ACTIVE.set(record)
    try:
        result = invoke_tool("epitoperank-builtin", "compute_delta_psi",
                             {"group1_psi": 0.1, "group2_psi": 0.6}, network=False)
    finally:
        ACTIVE.reset(token)
    assert result["delta_psi"] == pytest.approx(0.5)
    assert len(record.tool_calls) == 1
    assert record.tool_calls[0]["args"]["group1_psi"] == 0.1

    data = {"meta": {"schema_version": 1, "integrity": None, "decisions": []},
            "model_calls": [], "tool_calls": record.tool_calls,
            "steps": [], "params": {}, "errors": []}
    data["meta"]["integrity"] = ModelTrace.checksum(data)
    path = tmp_path / "agent_state.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    replay = ModelTrace(settings, replay=str(path))

    def forbidden():
        pytest.fail("replay must not call the network")

    replayed = replay.tool_call("epitoperank-builtin", "compute_delta_psi",
                                {"group1_psi": 0.1, "group2_psi": 0.6}, forbidden)
    assert replayed == result
    replay.finish()


def test_replay_rejects_changed_tool_arguments(tmp_path):
    settings = load_settings()
    data = {"meta": {"schema_version": 1, "integrity": None, "decisions": []},
            "model_calls": [], "steps": [], "params": {}, "errors": [],
            "tool_calls": [{"seq": 0, "server": "s", "tool": "t",
                            "args": {"x": 1}, "result": {"ok": True}}]}
    data["meta"]["integrity"] = ModelTrace.checksum(data)
    path = tmp_path / "agent_state.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    replay = ModelTrace(settings, replay=str(path))
    with pytest.raises(ReplayError, match="mismatch"):
        replay.tool_call("s", "t", {"x": 2}, lambda: {"ok": True})
