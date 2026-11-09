"""First-class MCP tools for the autonomous agent.

Previously the registry exposed a single generic ``call_mcp_tool`` action: the
model could not discover tool names, could not pass structured arguments (the
planner only allowed scalar values), and never saw tool results in ``facts``.
This module turns each built-in MCP tool into its own registry action with a
declared argument schema, validates model-supplied arguments against that
schema, and writes a structured result summary back to the blackboard.

Numerical work is still done by deterministic code. The model only decides
*which* tool to call and with which arguments.

All tool invocations pass through :func:`invoke_tool`, which is also the
recording/replay boundary: replay runs consume the recorded result instead of
touching the network.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from epitoperank.mcp.client import BUILTIN_SERVER_NAME

PEPTIDE_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]{4,40}$", re.I)
ALLELE_RE = re.compile(r"^HLA-[A-Z0-9*:\-]{2,24}$", re.I)

#: Compact argument declarations. ``type`` values: str/int/float/bool/list[str].
TOOL_SPECS: tuple[dict[str, Any], ...] = (
    {
        "name": "mcp__list_projects",
        "tool": "list_projects",
        "description": "List analyzed projects and their project_id",
        "params": {},
    },
    {
        "name": "mcp__project_summary",
        "tool": "project_summary",
        "description": "Summarize one project: samples, events, significant hits, top candidates",
        "params": {"project_id": {"type": "str", "required": True}},
    },
    {
        "name": "mcp__search_events",
        "tool": "search_events",
        "description": "Search splicing events by gene/type and FDR/dPSI gates",
        "params": {
            "project_id": {"type": "str", "required": True},
            "gene": {"type": "str", "max": 60},
            "event_type": {"type": "str", "choices": ("", "SE", "MXE", "A5SS", "A3SS", "RI")},
            "fdr_max": {"type": "float", "min": 0.0, "max": 1.0},
            "min_abs_dpsi": {"type": "float", "min": 0.0, "max": 1.0},
            "limit": {"type": "int", "min": 1, "max": 100},
        },
    },
    {
        "name": "mcp__explain_event_type",
        "tool": "explain_event_type",
        "description": "Explain SE/MXE/A5SS/A3SS/RI event types",
        "params": {"event_type": {"type": "str", "max": 12}},
    },
    {
        "name": "mcp__compute_delta_psi",
        "tool": "compute_delta_psi",
        "description": "Compute delta PSI = group2 - group1 and its direction",
        "params": {
            "group1_psi": {"type": "float", "required": True, "min": 0.0, "max": 1.0},
            "group2_psi": {"type": "float", "required": True, "min": 0.0, "max": 1.0},
        },
    },
    {
        "name": "mcp__peptide_capabilities",
        "tool": "peptide_capabilities",
        "description": "Report predictors, HLA reference tables and service limits before predicting",
        "params": {},
    },
    {
        "name": "mcp__peptide_properties",
        "tool": "peptide_properties",
        "description": "Offline physicochemical features for candidate peptides (no network)",
        "params": {
            "peptides": {"type": "list[str]", "required": True, "max": 50,
                         "item": "peptide"},
        },
    },
    {
        "name": "mcp__predict_mhc_binding",
        "tool": "predict_mhc_binding",
        "description": "Predict MHC-I/II binding via IEDB; returns percentile_rank per peptide/allele",
        "params": {
            "peptides": {"type": "list[str]", "required": True, "max": 20,
                         "item": "peptide"},
            "alleles": {"type": "list[str]", "required": True, "max": 4,
                        "item": "allele"},
            "mhc_class": {"type": "str", "choices": ("class1", "class2", "both")},
            "processing": {"type": "bool"},
        },
    },
    {
        "name": "mcp__lookup_epitope",
        "tool": "lookup_epitope",
        "description": "Check candidate peptides against known IEDB T-cell assay epitopes",
        "params": {
            "peptides": {"type": "list[str]", "required": True, "max": 10,
                         "item": "peptide"},
        },
    },
)

SPEC_BY_ACTION = {spec["name"]: spec for spec in TOOL_SPECS}
DEFAULT_SERVER = BUILTIN_SERVER_NAME


def compact_schema(params: dict[str, Any]) -> dict[str, str]:
    """One-line type hints for the planner prompt (keeps the payload small)."""
    output: dict[str, str] = {}
    for name, rule in params.items():
        kind = str(rule.get("type", "str"))
        suffix = "!" if rule.get("required") else ""
        cap = rule.get("max")
        if isinstance(cap, (int, float)) and kind.startswith("list"):
            suffix += f"<={int(cap)}"
        if rule.get("choices"):
            suffix += "|" + "/".join(str(c) for c in rule["choices"] if c)
        output[name] = kind + suffix
    return output


def validate_args(params: dict[str, Any], raw: Any) -> tuple[dict[str, Any], list[str]]:
    """Validate model-supplied arguments; return cleaned args and dropped keys.

    Unknown keys, wrong types and out-of-range values are dropped rather than
    raising, so a bad model suggestion degrades into a valid (or empty) call.
    """
    dropped: list[str] = []
    if not isinstance(raw, dict):
        return {}, ["<args-not-a-dict>"]
    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        rule = params.get(str(key))
        if rule is None:
            dropped.append(str(key))
            continue
        kind = str(rule.get("type", "str"))
        ok = True
        if kind == "str":
            ok = isinstance(value, str)
            if ok:
                value = value.strip()
                if rule.get("max") and len(value) > int(rule["max"]):
                    ok = False
                if ok and rule.get("choices") and value not in rule["choices"]:
                    ok = False
        elif kind == "int":
            ok = isinstance(value, int) and not isinstance(value, bool)
        elif kind == "float":
            ok = isinstance(value, (int, float)) and not isinstance(value, bool)
            if ok:
                value = float(value)
        elif kind == "bool":
            ok = isinstance(value, bool)
        elif kind == "list[str]":
            ok = isinstance(value, list) and all(isinstance(v, str) for v in value)
            if ok:
                value = [v.strip() for v in value]
                if rule.get("max") and len(value) > int(rule["max"]):
                    ok = False
                pattern = PEPTIDE_RE if rule.get("item") == "peptide" else (
                    ALLELE_RE if rule.get("item") == "allele" else None)
                if ok and pattern and not all(pattern.match(v) for v in value):
                    ok = False
                if ok and not value:
                    ok = False
        else:
            ok = False
        if ok and isinstance(value, (int, float)) and not isinstance(value, bool):
            low, high = rule.get("min"), rule.get("max")
            if low is not None and value < low:
                ok = False
            if high is not None and kind in ("int", "float") and value > high:
                ok = False
        if ok:
            cleaned[str(key)] = value
        else:
            dropped.append(str(key))
    for key, rule in params.items():
        if rule.get("required") and key not in cleaned:
            dropped.append(key + "<required-missing>")
    return cleaned, dropped


def summarize_result(tool: str, result: Any) -> dict[str, Any]:
    """Extract decision-relevant fields from an MCP result for ``state.facts``."""
    payload = result if isinstance(result, dict) else {"value": result}
    summary: dict[str, Any] = {"tool": tool, "ok": not bool(payload.get("error")),
                               "keys": sorted(payload)[:12]}
    if payload.get("error"):
        summary["error"] = str(payload["error"])[:200]
        return summary
    if tool == "predict_mhc_binding":
        rows = payload.get("predictions") or []
        percentiles = [float(r["percentile_rank"]) for r in rows
                       if isinstance(r, dict) and isinstance(r.get("percentile_rank"), (int, float))]
        summary.update(prediction_count=len(rows),
                       best_percentile=min(percentiles) if percentiles else None,
                       error_count=len(payload.get("errors") or []))
    elif tool == "lookup_epitope":
        matches = payload.get("matches") or payload.get("epitope_matches") or []
        if isinstance(matches, dict):
            summary["match_count"] = sum(len(v) for v in matches.values()
                                         if isinstance(v, (list, tuple)))
        else:
            summary["match_count"] = len(matches) if isinstance(matches, (list, tuple)) else 0
    elif tool == "peptide_properties":
        rows = payload.get("peptides") or []
        summary["peptide_count"] = len(rows) if isinstance(rows, list) else 0
    elif tool == "peptide_capabilities":
        summary["iedb_online"] = bool((payload.get("iedb") or {}).get("online"))
    elif tool == "search_events":
        rows = payload.get("events") or []
        summary["event_count"] = len(rows) if isinstance(rows, list) else 0
    return summary


def _local_invoke(tool: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """Offline fallback for built-in tools when the MCP HTTP server is down.

    Keeps the demo reproducible and usable without port 9100. Returns ``None``
    when the tool has no local implementation, so external MCP servers are
    still reached through the normal network path.
    """
    try:
        if tool in {"list_projects", "project_summary", "search_events",
                    "explain_event_type", "compute_delta_psi", "web_fetch"}:
            from epitoperank.mcp import demo_tools
            return demo_tools.call_tool(tool, args)
        if tool == "peptide_capabilities":
            from epitoperank.peptide import capabilities
            return capabilities()
        if tool == "peptide_properties":
            from epitoperank.peptide.properties import describe_many
            return {"peptides": describe_many(args["peptides"])}
        if tool == "predict_mhc_binding":
            from epitoperank.peptide import predict_peptides
            result = predict_peptides(args["peptides"], args["alleles"],
                                      mhc_class=args.get("mhc_class", "class1"),
                                      predictor="iedb",
                                      processing=bool(args.get("processing", False)))
            return {"predictions": result["predictions"], "errors": result["errors"]}
        if tool == "lookup_epitope":
            from epitoperank.peptide import IedbClient
            return {"matches": IedbClient().lookup_epitopes(args["peptides"], limit=3)}
    except Exception as error:  # noqa: BLE001 - fallback must never break a run
        return {"error": f"local tool {tool} failed: {error}"}
    return None


def invoke_tool(server: str, tool: str, args: dict[str, Any],
                *, network: bool = True) -> dict[str, Any]:
    """Single MCP boundary: replay uses the tape, otherwise call + record."""
    from epitoperank.llm.trace import ACTIVE

    def real_call() -> dict[str, Any]:
        if network and server == BUILTIN_SERVER_NAME:
            try:
                from epitoperank.llm.enrich import run_async
                from epitoperank.mcp import mcp_call_tool
                result = run_async(mcp_call_tool(server, tool, args))
                if isinstance(result, dict) and not result.get("error"):
                    return result
                error = str((result or {}).get("error", "empty result"))[:160]
            except Exception as exc:  # noqa: BLE001
                error = str(exc)[:160]
            local = _local_invoke(tool, args)
            if local is None:
                return {"error": f"MCP unavailable ({error})"}
            return local
        if network:
            from epitoperank.llm.enrich import run_async
            from epitoperank.mcp import mcp_call_tool
            return run_async(mcp_call_tool(server, tool, args))
        local = _local_invoke(tool, args)
        return local if local is not None else {"error": "network disabled and no local tool"}

    trace = ACTIVE.get()
    if trace is not None:
        return trace.tool_call(server, tool, args, real_call)
    return real_call()


def build_mcp_actions() -> list[Any]:
    """Build one registry Action per built-in MCP tool."""
    from .actions import Action

    actions = []
    for spec in TOOL_SPECS:
        def handler(context: Any, state: Any, _tool: str = spec["tool"],
                    _params: dict = spec["params"], _name: str = spec["name"], **kwargs: Any) -> str:
            from .mcp_actions import invoke_tool, summarize_result, validate_args

            args, dropped = validate_args(_params, kwargs)
            missing = [key for key, rule in _params.items()
                       if rule.get("required") and key not in args]
            if missing:
                return f"{_name} skipped: missing or invalid arguments ({', '.join(missing)})"
            network = bool(getattr(context.settings.agent, "allow_network", True))
            result = invoke_tool(DEFAULT_SERVER, _tool, args, network=network)
            summary = summarize_result(_tool, result)
            summary["dropped_args"] = dropped
            # Structured blackboard write-back: the next OODA iteration can now
            # see prediction outcomes instead of only "a tool was called".
            state.facts["last_mcp_tool"] = _tool
            state.facts["last_mcp_ok"] = bool(summary["ok"])
            state.facts["mcp_summaries"] = {
                **(state.facts.get("mcp_summaries") or {}), _tool: summary}
            if _tool == "predict_mhc_binding":
                state.facts["prediction_count"] = summary.get("prediction_count", 0)
                if summary.get("best_percentile") is not None:
                    state.facts["best_percentile"] = summary["best_percentile"]
            if dropped:
                context.log("agent", _name, "warning",
                            "dropped invalid model arguments: " + ", ".join(dropped))
            context.log("agent", _name, "ok", json.dumps(summary, ensure_ascii=False)[:400])
            return json.dumps(summary, ensure_ascii=False, default=str)

        actions.append(Action(spec["name"], spec["description"], handler,
                              arg_schema=spec["params"]))
    return actions
