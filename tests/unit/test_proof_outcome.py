"""可复现证明里的运行状态结论必须是中文、结构化且能解释失败。"""
from __future__ import annotations

from epitoperank.agent.plan import reproducibility_proof
from epitoperank.llm.trace import ModelTrace


def _state(*, stopped: str, candidates: int, figures: int = 0) -> dict:
    state = {
        "steps": [
            {"index": 0, "action": "profile_dataset", "source": "rule", "status": "ok"},
            {"index": 1, "action": "filter_significant_events", "source": "llm",
             "rationale": "Profiling done; filtering by FDR/dPSI is the next unmet criterion."},
            {"index": 2, "action": "assess_quality", "source": "llm",
             "rationale": "Filter failed twice; check quality gates at current thresholds."},
        ],
        "facts": {"candidates": candidates, "figures": figures},
        "model_calls": [], "tool_calls": [], "errors": [], "params": {},
        "meta": {
            "schema_version": 1, "integrity": None, "query": "找新抗原候选",
            "project_id": "P1", "input_dir": "E:/data", "stopped_reason": stopped,
            "input_fingerprints": {"a.tsv": "hash"}, "reports": {},
            "analysis_plan": {
                "goal": "找新抗原候选", "intent": "neoantigen",
                "thresholds": {"fdr": 0.05}, "expected_tools": ["profile_dataset"],
            },
        },
    }
    state["meta"]["integrity"] = ModelTrace.checksum(state)
    return state


def test_failed_run_exposes_chinese_failure_and_hint() -> None:
    proof = reproducibility_proof(_state(stopped="error budget exhausted (3 failures)", candidates=0))
    assert proof["run_status"] == "failed"
    assert "未产出候选数据" in proof["run_summary"]
    assert proof["failure"]["reason"] == "error budget exhausted (3 failures)"
    assert "sample_metadata.tsv" in proof["failure"]["hint"]
    assert proof["candidate_count"] == 0
    assert all("Replay uses" not in item for item in proof["limitations"])
    assert all(any("\u4e00" <= char <= "\u9fff" for char in item) for item in proof["limitations"])


def test_successful_run_is_marked_succeeded() -> None:
    proof = reproducibility_proof(_state(stopped="Goal satisfied: filtered, ranked, reported",
                                         candidates=20, figures=6))
    assert proof["run_status"] == "succeeded"
    assert proof["failure"] is None
    assert "20 个候选" in proof["run_summary"]


def test_autonomous_additions_carry_chinese_reason() -> None:
    proof = reproducibility_proof(_state(stopped="error budget exhausted (3 failures)", candidates=0))
    deviation = proof["deviations"]
    assert deviation["note"].startswith("计划是契约")
    assert "前置条件没有满足" in deviation["planned_not_run_reason"]
    additions = deviation["autonomous_additions"]
    assert additions
    assert all(item.get("reason_zh") for item in additions)
    assert all("Filter failed" not in item["reason_zh"] for item in additions)
