"""Read-only view over a recorded ``agent_state.json`` decision trace.

The autonomous loop already persists every step (with its decision source),
every model call and every decision snapshot. This module turns that file into
a compact, UI-friendly summary so the autonomy is *visible* rather than only
auditable on disk.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from epitoperank.llm.trace import ModelTrace


def load_state(project_dir: str | Path) -> dict[str, Any]:
    """Load ``agent_state.json`` from a project directory (or the file itself)."""
    path = Path(project_dir)
    state_path = path / "agent_state.json" if path.is_dir() else path
    if not state_path.is_file():
        raise FileNotFoundError(f"no agent_state.json at {state_path}")
    data = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("agent_state.json must be a JSON object")
    return data


def summarize(state: dict[str, Any]) -> dict[str, Any]:
    """Build the decision-trace payload consumed by the web UI."""
    steps = [s for s in (state.get("steps") or []) if isinstance(s, dict)]
    calls = [c for c in (state.get("model_calls") or []) if isinstance(c, dict)]
    tool_calls = [c for c in (state.get("tool_calls") or []) if isinstance(c, dict)]
    decisions = [d for d in (state.get("meta", {}).get("decisions") or []) if isinstance(d, dict)]
    sources = Counter(str(s.get("source") or "rule") for s in steps)
    llm_steps = sources.get("llm", 0)
    total = len(steps)
    meta = state.get("meta") or {}
    recorded_integrity = meta.get("integrity")
    integrity_ok = bool(recorded_integrity) and recorded_integrity == ModelTrace.checksum(state)

    calls_view = [{
        "seq": c.get("seq"), "stage": c.get("stage"), "model": c.get("model"),
        "temperature": c.get("temperature_effective"),
        "prompt_hash": (c.get("prompt_hash") or "")[:16],
        "elapsed_ms": c.get("elapsed_ms"),
        "parsed": c.get("parsed"),
        "raw_response": str(c.get("raw_response") or "")[:1200],
    } for c in calls]
    steps_view = [{
        "index": s.get("index"), "action": s.get("action"),
        "source": str(s.get("source") or "rule"),
        "status": s.get("status"), "rationale": s.get("rationale"),
        "args": s.get("args") or {}, "issues": s.get("issues") or [],
        "seconds": s.get("seconds"),
    } for s in steps]

    return {
        "available": True,
        "schema_version": meta.get("schema_version"),
        "query": meta.get("query"),
        "project_id": meta.get("project_id"),
        "llm_enabled": meta.get("llm_enabled"),
        "model_name": meta.get("model_name"),
        "total_steps": total,
        "sources": dict(sources),
        "llm_steps": llm_steps,
        "llm_ratio": round(llm_steps / total, 3) if total else 0.0,
        "reflection_steps": sources.get("reflection", 0),
        "episodic_steps": sources.get("episodic", 0),
        "replay_steps": sources.get("replay", 0),
        "decision_count": len(decisions),
        "model_call_count": len(calls),
        "tool_call_count": len(tool_calls),
        "steps": steps_view,
        "model_calls": calls_view,
        "tool_calls": tool_calls,
        "params": state.get("params") or {},
        "errors": state.get("errors") or [],
        "input_fingerprints": meta.get("input_fingerprints") or {},
        "reports": meta.get("reports") or {},
        "integrity": recorded_integrity,
        "integrity_ok": integrity_ok,
        "replay_success": state.get("replay_success"),
    }
