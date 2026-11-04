"""Tool-using analysis copilot ("agentic mode").

Why this exists
---------------
The deterministic pipeline answers *one* question: "given this event table,
what changed?". Real analyses are iterative — an analyst asks why a gene is
significant, whether the enrichment is confounded, what the literature says,
which peptides are worth testing, and what to check next. A single
prompt-to-narrative call cannot do that.

This module implements the mainstream modern-agent pattern:

    plan → call tool → observe → revise → ... → grounded answer

with explicit budgets (steps, tool calls, wall clock), native function calling,
per-call tracing, schema validation of tool arguments, and a numeric grounding
check of the final prose. When no model is configured it degrades to a
deterministic briefing instead of pretending to be an agent.

It is *not* a free-form SQL shell: tools only read the current project (plus
optional public APIs), and every argument is validated and range-clamped.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from epitoperank.config import Settings
from epitoperank.llm.chat import ChatClient, ChatError, ChatResult
from epitoperank.llm.structured import grounding_report, validate_schema
from epitoperank.memory.project_memory import ProjectMemory
from epitoperank.pipeline import list_projects, project_status

from .planner import (
    Plan,
    critique_answer,
    heuristic_plan,
    make_plan,
    revision_instruction,
)
from .tool_cache import CacheHit, ToolCache

MAX_STEPS = 6
MAX_TOOL_CALLS = 24
MAX_CALLS_PER_STEP = 6
MAX_NETWORK_CALLS = 8
MAX_TOOL_RESULT_CHARS = 6000
MAX_HISTORY_MESSAGES = 8
MAX_MODEL_CALLS = 10

#: Tools that touch the network (and therefore may be disabled or confirmed).
NETWORK_TOOLS = frozenset({
    "annotate_gene",
    "search_literature",
    "search_literature_passages",
    "pathway_enrichment",
    "predict_peptides",
})

#: Network tools whose result is stable enough to cache persistently.
CACHEABLE_TOOLS = frozenset(NETWORK_TOOLS)

#: Questions that benefit from an explicit plan before tool use.
PLAN_TRIGGERS = (
    "为什么", "比较", "评估", "建议", "下一步", "以及", "同时", "解释", "分析一下",
    "which", "why", "compare", "evaluate", "recommend", "next step", "how",
)

SYSTEM_PROMPT = """你是 EpitopeRank 的剪接分析协作智能体（agentic copilot），面向 RNA 剪接与肿瘤免疫研究。

工作方式：
1. 先判断用户问题需要哪些事实，再调用工具取数；不要把工具结果之外的数字、基因名、通路或文献写进回答。
2. 工具结果里的数字是唯一可信来源。缺失的数据要明确说“没有该数据”，不要估算或补全。
3. 需要多个视角时（例如同时看事件层面和肽层面），分步调用工具，不要臆测另一层的结果。
4. 不要重复相同参数的调用；已有结果足够时直接回答。
5. 科学边界：MHC 结合预测不等于抗原呈递或免疫原性；相关性不等于因果；没有配对正常样本时不能声称“肿瘤特异”。

最终回答使用 Markdown，固定四段：
## 结论
## 关键证据
## 建议的下一步
## 局限

用户用中文提问就用中文回答；基因名、PSI、FDR、HLA 等术语保留英文。"""

OFFLINE_NOTE = (
    "当前未配置可用的大模型（MODEL_API_BASE_URL / MODEL_API_KEY / MODEL_NAME），"
    "以下为确定性事实摘要；配置模型后可进行多轮工具调用分析。"
)
OFFLINE_FORCED_NOTE = (
    "本次请求按要求使用离线模式（force_offline），未调用模型；"
    "以下为确定性事实摘要。如需模型分析，请关闭 force_offline。"
)


# ----------------------------------------------------------------------
# Tool plumbing
# ----------------------------------------------------------------------
@dataclass
class ToolResult:
    ok: bool
    summary: str
    data: Any = None
    error: str = ""
    cached: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "summary": self.summary,
            "data": self.data,
            "error": self.error,
            "cached": self.cached,
        }

    def as_content(self) -> str:
        payload = json.dumps(self.as_dict(), ensure_ascii=False, default=str)
        if len(payload) > MAX_TOOL_RESULT_CHARS:
            payload = payload[:MAX_TOOL_RESULT_CHARS] + "…(truncated)"
        return payload


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[[dict[str, Any]], ToolResult]


def _clamp(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _float_arg(value: Any, default: float | None, low: float, high: float) -> float | None:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def _clean_text(value: Any, limit: int = 200) -> str:
    return str(value or "").strip()[:limit]


class CopilotTools:
    """Project-scoped tool registry with budgets, caching and tracing."""

    def __init__(self, settings: Settings, project_id: str | None = None, *,
                 allow_network: bool = True, use_cache: bool = True,
                 cache_dir: str | Path | None = None,
                 cache_ttl: float = 1800.0) -> None:
        self.settings = settings
        self.project_id = project_id or ""
        self.memory = ProjectMemory(settings.paths.memory_db)
        self.calls: list[dict[str, Any]] = []
        self.results: list[Any] = []
        self.budget = MAX_TOOL_CALLS
        self.network_budget = MAX_NETWORK_CALLS
        self.allow_network = bool(allow_network)
        self._skills: Any = None
        self._status_cache: dict[str, Any] | None = None
        self._session_cache: dict[str, ToolResult] = {}
        root = Path(cache_dir) if cache_dir else settings.paths.runtime_root / "cache"
        self.cache = ToolCache(root / "tool_cache.sqlite3", ttl=cache_ttl,
                               enabled=use_cache)
        self._specs: dict[str, ToolSpec] = self._build_specs()
        if not self.allow_network:
            self._specs = {name: spec for name, spec in self._specs.items()
                           if name not in NETWORK_TOOLS}

    # -- registry -------------------------------------------------------
    def _build_specs(self) -> dict[str, ToolSpec]:
        specs = [
            ToolSpec(
                "list_projects",
                "List analysed projects with counters (id, name, events, significant events).",
                {"type": "object", "properties": {}},
                lambda args: self._list_projects(),
            ),
            ToolSpec(
                "project_overview",
                "Read the current project: samples, groups, event counts, event types, top candidates, "
                "enrichment terms, artifacts and recent workflow log.",
                {"type": "object", "properties": {
                    "project_id": {"type": "string", "description": "Optional project id; defaults to the active project."},
                }},
                lambda args: self._overview(_clean_text(args.get("project_id"), 64)),
            ),
            ToolSpec(
                "query_events",
                "Query splicing events from the project memory with filters; returns ranked rows.",
                {"type": "object", "properties": {
                    "gene": {"type": "string", "description": "Gene symbol or gene id substring."},
                    "event_type": {"type": "string", "enum": ["SE", "MXE", "A3SS", "A5SS", "RI"]},
                    "fdr_max": {"type": "number", "minimum": 0, "maximum": 1},
                    "min_abs_dpsi": {"type": "number", "minimum": 0, "maximum": 1},
                    "significant_only": {"type": "boolean"},
                    "order_by": {"type": "string", "enum": ["fdr", "delta_psi", "gene"]},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                }},
                lambda args: self._query_events(args),
            ),
            ToolSpec(
                "top_candidates",
                "Return the ranked candidate events stored for the project.",
                {"type": "object", "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                }},
                lambda args: self._top_candidates(_clamp(args.get("limit"), 20, 1, 50)),
            ),
            ToolSpec(
                "enrichment_summary",
                "Return stored GO/KEGG/Reactome enrichment results for the project.",
                {"type": "object", "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                }},
                lambda args: self._enrichment(_clamp(args.get("limit"), 20, 1, 50)),
            ),
            ToolSpec(
                "dataset_quality",
                "Assess dataset completeness: sample groups, event-type composition, significance ratio, "
                "stored plan and artifacts. Use this before strong claims.",
                {"type": "object", "properties": {}},
                lambda args: self._quality(),
            ),
            ToolSpec(
                "annotate_gene",
                "Annotate one gene via MyGene.info (symbol, Entrez, Ensembl, UniProt, summary).",
                {"type": "object", "properties": {
                    "gene": {"type": "string", "description": "HGNC symbol, e.g. TP53."},
                }, "required": ["gene"]},
                lambda args: self._annotate(_clean_text(args.get("gene"), 40)),
            ),
            ToolSpec(
                "search_literature",
                "Search PubMed for a question or gene and return titles/abstract snippets.",
                {"type": "object", "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 20},
                }, "required": ["query"]},
                lambda args: self._literature(_clean_text(args.get("query"), 300),
                                             _clamp(args.get("max_results"), 8, 1, 20)),
            ),
            ToolSpec(
                "search_literature_passages",
                "Full-text evidence search: open-access Europe PMC articles, locally "
                "BM25-ranked passages with PMID/PMCID/section. Use this when the answer "
                "needs what a paper actually measured, not just its title.",
                {"type": "object", "properties": {
                    "query": {"type": "string"},
                    "max_articles": {"type": "integer", "minimum": 1, "maximum": 5},
                    "max_passages": {"type": "integer", "minimum": 1, "maximum": 10},
                }, "required": ["query"]},
                lambda args: self._literature_passages(
                    _clean_text(args.get("query"), 300),
                    _clamp(args.get("max_articles"), 3, 1, 5),
                    _clamp(args.get("max_passages"), 6, 1, 10)),
            ),
            ToolSpec(
                "pathway_enrichment",
                "Run GO/KEGG over-representation on a gene list (network via Enrichr/GSEApy).",
                {"type": "object", "properties": {
                    "genes": {"type": "array", "items": {"type": "string"}, "maxItems": 200},
                    "ontologies": {"type": "array", "items": {"type": "string"}},
                }, "required": ["genes"]},
                lambda args: self._pathways(args),
            ),
            ToolSpec(
                "predict_peptides",
                "Run the peptide pipeline for this project (needs splice_orfs/coding_pairs CDS table) and "
                "return ranked MHC-I/II candidates. Prediction only; not presentation or immunogenicity.",
                {"type": "object", "properties": {
                    "alleles": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
                    "mhc_class": {"type": "string", "enum": ["class1", "class2", "both"]},
                    "processing": {"type": "boolean"},
                }, "required": ["alleles"]},
                lambda args: self._peptides(args),
            ),
            ToolSpec(
                "read_interpretation",
                "Read the stored biological interpretation text for the project.",
                {"type": "object", "properties": {}},
                lambda args: self._interpretation(),
            ),
            ToolSpec(
                "read_plan",
                "Read the stored analysis plan: goal, thresholds, hypothesis-test results, "
                "limitations and validation suggestions.",
                {"type": "object", "properties": {}},
                lambda args: self._plan(),
            ),
        ]
        return {spec.name: spec for spec in specs}

    def specs(self) -> list[dict[str, Any]]:
        return [
            {"type": "function", "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            }}
            for spec in self._specs.values()
        ]

    def describe(self) -> list[dict[str, Any]]:
        return [
            {"name": spec.name, "description": spec.description,
             "parameters": spec.parameters}
            for spec in self._specs.values()
        ]

    # -- execution ------------------------------------------------------
    def execute(self, name: str, arguments: Mapping[str, Any] | None) -> ToolResult:
        started = time.monotonic()
        args = dict(arguments or {})
        spec = self._specs.get(name)
        session_key = name + "|" + json.dumps(args, ensure_ascii=False, sort_keys=True, default=str)
        cache_key = ToolCache.key(self.project_id, name, args)
        if spec is None:
            if name in NETWORK_TOOLS and not self.allow_network:
                result = ToolResult(False, f"network tool disabled: {name}", error="network_disabled")
            else:
                result = ToolResult(False, f"unknown tool: {name}", error="unknown_tool")
        elif len(self.calls) >= self.budget:
            result = ToolResult(False, "tool budget exhausted", error="budget")
        elif session_key in self._session_cache:
            previous = self._session_cache[session_key]
            result = ToolResult(previous.ok, previous.summary, previous.data,
                                previous.error, cached=True)
        else:
            errors = validate_schema(args, spec.parameters)
            if errors:
                result = ToolResult(False, "invalid arguments", error="; ".join(errors[:4]))
            else:
                result = self._run_with_cache(name, spec, args, cache_key)
                if result.ok:
                    self._session_cache[session_key] = result
        elapsed = round(time.monotonic() - started, 3)
        self.results.append(result.data)
        self.calls.append({
            "tool": name,
            "arguments": {key: (str(value)[:120] if not isinstance(value, (int, float, bool)) else value)
                          for key, value in args.items()},
            "ok": result.ok,
            "cached": result.cached,
            "summary": result.summary[:300],
            "error": result.error[:300],
            "elapsed_seconds": elapsed,
        })
        return result

    def _run_with_cache(self, name: str, spec: ToolSpec, args: Mapping[str, Any],
                        cache_key: str) -> ToolResult:
        """Persistent cache for network tools, then the real call."""
        if name in CACHEABLE_TOOLS:
            hit: CacheHit | None = self.cache.get(cache_key)
            if hit and isinstance(hit.value, Mapping):
                return ToolResult(True, str(hit.value.get("summary") or "cached result"),
                                  hit.value.get("data"), "", cached=True)
        if name in NETWORK_TOOLS:
            if self.network_budget <= 0:
                return ToolResult(False, "network tool budget exhausted", error="network_budget")
            self.network_budget -= 1
        try:
            result = spec.func(args)
        except Exception as error:  # noqa: BLE001 - tools must not kill the loop
            return ToolResult(False, f"{type(error).__name__}: {str(error)[:300]}",
                              error="exception")
        if result.ok and name in CACHEABLE_TOOLS:
            self.cache.put(cache_key, {"summary": result.summary, "data": result.data})
        return result

    # -- helpers --------------------------------------------------------
    def _require_project(self) -> tuple[str, dict[str, Any] | None]:
        project_id = self.project_id
        if not project_id:
            return "", None
        return project_id, self._overview_payload(project_id)

    def _overview_payload(self, project_id: str) -> dict[str, Any] | None:
        if self._status_cache is not None and self._status_cache.get("project", {}).get("project_id") == project_id:
            return self._status_cache
        payload = project_status(project_id, self.settings)
        self._status_cache = payload
        return payload

    def _skills_bridge(self) -> Any:
        if self._skills is None:
            from epitoperank.agent.skills_bridge import SkillBridge

            self._skills = SkillBridge(settings=self.settings, enabled=True,
                                       timeout=20.0, budget=8)
        return self._skills

    # -- tool implementations -------------------------------------------
    def _list_projects(self) -> ToolResult:
        projects = list_projects(self.settings)[:20]
        rows = [{
            "project_id": item.get("project_id"),
            "name": item.get("name"),
            "events": item.get("events") or item.get("event_count"),
            "significant": item.get("significant"),
            "created_at": item.get("created_at"),
        } for item in projects]
        return ToolResult(True, f"{len(rows)} projects", {"projects": rows})

    def _overview(self, project_id: str = "") -> ToolResult:
        target = project_id or self.project_id
        if not target:
            return ToolResult(False, "no active project; call list_projects first", error="no_project")
        payload = self._overview_payload(target)
        if payload is None:
            return ToolResult(False, f"project {target} not found", error="not_found")
        project = payload.get("project", {})
        samples = payload.get("samples") or []
        groups: dict[str, int] = {}
        for sample in samples:
            group = str(sample.get("group_name") or sample.get("group")
                        or sample.get("condition") or "unknown")
            groups[group] = groups.get(group, 0) + 1
        data = {
            "project_id": project.get("project_id"),
            "name": project.get("name"),
            "source_dir": project.get("source_dir"),
            "events": payload.get("events"),
            "significant": payload.get("significant"),
            "event_types": payload.get("event_types"),
            "samples": len(samples),
            "groups": groups,
            "candidates_total": payload.get("candidates_total"),
            "top_candidates": payload.get("candidates", [])[:5],
            "top_enrichment": payload.get("enrichment", [])[:5],
            "artifacts": [item.get("kind") for item in (payload.get("artifacts") or [])],
            "plan_goal": (payload.get("plan") or {}).get("goal"),
            "recent_logs": [
                {"agent": item.get("agent"), "action": item.get("action"), "status": item.get("status")}
                for item in (payload.get("logs") or [])[-5:]
            ],
        }
        return ToolResult(True, f"{data['events']} events / {data['significant']} significant", data)

    def _query_events(self, args: Mapping[str, Any]) -> ToolResult:
        if not self.project_id:
            return ToolResult(False, "no active project", error="no_project")
        filters: dict[str, Any] = {}
        gene = _clean_text(args.get("gene"), 40)
        if gene:
            filters["search"] = gene
        event_type = _clean_text(args.get("event_type"), 5)
        if event_type:
            filters["event_type"] = event_type
        fdr_max = _float_arg(args.get("fdr_max"), None, 0.0, 1.0)
        if fdr_max is not None:
            filters["fdr_max"] = fdr_max
        min_abs = _float_arg(args.get("min_abs_dpsi"), None, 0.0, 1.0)
        if min_abs is not None:
            filters["min_abs_delta"] = min_abs
        if args.get("significant_only"):
            filters["significant_only"] = True
        order_by = args.get("order_by") if args.get("order_by") in {"fdr", "delta_psi", "gene"} else "fdr"
        limit = _clamp(args.get("limit"), 20, 1, 100)
        rows = self.memory.query_events(self.project_id, limit=limit, order_by=order_by, **filters)
        compact = [{
            "event_id": row.get("event_id"),
            "gene": row.get("gene_symbol") or row.get("gene_id"),
            "event_type": row.get("event_type"),
            "fdr": row.get("fdr"),
            "delta_psi": row.get("delta_psi"),
            "psi_g1": row.get("mean_psi_group1"),
            "psi_g2": row.get("mean_psi_group2"),
            "coordinates": row.get("genomic_coordinates"),
        } for row in rows]
        return ToolResult(True, f"{len(compact)} events", {"filters": filters, "events": compact})

    def _top_candidates(self, limit: int) -> ToolResult:
        if not self.project_id:
            return ToolResult(False, "no active project", error="no_project")
        rows = self.memory.load_candidates(self.project_id)
        compact = [{
            "gene": row.get("gene_symbol") or row.get("gene_id"),
            "event_id": row.get("event_id"),
            "event_type": row.get("event_type"),
            "fdr": row.get("fdr"),
            "delta_psi": row.get("delta_psi"),
            "score": row.get("score"),
        } for row in rows[:limit]]
        return ToolResult(True, f"{len(compact)} candidates (of {len(rows)})", {"candidates": compact})

    def _enrichment(self, limit: int) -> ToolResult:
        if not self.project_id:
            return ToolResult(False, "no active project", error="no_project")
        rows = self.memory.load_enrichment(self.project_id)
        compact = [{
            "term": row.get("term"),
            "ontology": row.get("ontology"),
            "genes": row.get("gene_count"),
            "fold": row.get("fold_enrichment"),
            "fdr": row.get("fdr"),
        } for row in rows[:limit]]
        return ToolResult(True, f"{len(compact)} terms (of {len(rows)})", {"terms": compact})

    def _quality(self) -> ToolResult:
        if not self.project_id:
            return ToolResult(False, "no active project", error="no_project")
        payload = self._overview_payload(self.project_id) or {}
        events = int(payload.get("events") or 0)
        significant = int(payload.get("significant") or 0)
        samples = payload.get("samples") or []
        groups: dict[str, int] = {}
        for sample in samples:
            group = str(sample.get("group_name") or sample.get("group")
                        or sample.get("condition") or "unknown")
            groups[group] = groups.get(group, 0) + 1
        data = {
            "events": events,
            "significant": significant,
            "significant_ratio": round(significant / events, 4) if events else None,
            "samples": len(samples),
            "groups": groups,
            "balanced_groups": len(set(groups.values())) <= 1 if groups else None,
            "event_types": payload.get("event_types"),
            "plan": payload.get("plan"),
            "artifacts": [item.get("kind") for item in payload.get("artifacts") or []],
            "warnings": [
                "未提供配对正常样本时不能声称肿瘤特异"
                if not any("normal" in str(group).lower() for group in groups) else
                "存在 normal 组，仍须核对配对关系与样本量"
            ],
        }
        return ToolResult(True, f"{significant}/{events} significant", data)

    def _annotate(self, gene: str) -> ToolResult:
        if not gene:
            return ToolResult(False, "gene is required", error="bad_argument")
        from epitoperank.skills.gene_annotation import GeneAnnotationSkill

        bridge = self._skills_bridge()
        result = bridge.run_skill("gene_annotation", GeneAnnotationSkill, gene_symbol=gene)
        if result is None:
            return ToolResult(False, "gene annotation unavailable (network or budget)", error="skipped")
        return ToolResult(True, f"annotated {gene}", result.data)

    def _literature(self, query: str, limit: int) -> ToolResult:
        if not query:
            return ToolResult(False, "query is required", error="bad_argument")
        from epitoperank.skills.literature_search import LiteratureSearchSkill

        bridge = self._skills_bridge()
        result = bridge.run_skill("literature_search", LiteratureSearchSkill,
                                  query=query, max_results=limit, include_abstracts=True)
        if result is None:
            return ToolResult(False, "literature search unavailable (network or budget)", error="skipped")
        return ToolResult(True, f"literature for {query}", result.data)

    def _literature_passages(self, query: str, max_articles: int,
                             max_passages: int) -> ToolResult:
        if not query:
            return ToolResult(False, "query is required", error="bad_argument")
        from epitoperank.knowledge.literature_rag import RagError, search_passages

        try:
            payload = search_passages(query, max_articles=max_articles,
                                      max_passages=max_passages)
        except RagError as error:
            return ToolResult(False, f"full-text retrieval failed: {str(error)[:250]}",
                              error="rag_error")
        passages = payload.get("passages") or []
        articles = payload.get("articles") or []
        return ToolResult(True, f"{len(passages)} passages from {len(articles)} open-access articles",
                          {"articles": articles[:max_articles], "passages": passages})

    def _pathways(self, args: Mapping[str, Any]) -> ToolResult:
        genes = [str(item).strip() for item in (args.get("genes") or []) if str(item).strip()]
        if not genes:
            return ToolResult(False, "genes is required", error="bad_argument")
        from epitoperank.skills.pathway_enrichment import PathwayEnrichmentSkill

        ontologies = [str(item) for item in (args.get("ontologies") or ["GO", "KEGG"])]
        bridge = self._skills_bridge()
        result = bridge.run_skill("pathway_enrichment", PathwayEnrichmentSkill,
                                  genes=genes[:200], ontologies=ontologies)
        if result is None:
            return ToolResult(False, "pathway enrichment unavailable (network or budget)", error="skipped")
        return ToolResult(True, f"enrichment for {len(genes)} genes", result.data)

    def _peptides(self, args: Mapping[str, Any]) -> ToolResult:
        if not self.project_id:
            return ToolResult(False, "no active project", error="no_project")
        payload = self._overview_payload(self.project_id) or {}
        source = payload.get("project", {}).get("source_dir") or ""
        directory = Path(source).expanduser()
        if not directory.is_dir():
            return ToolResult(False, "project source directory is unavailable", error="no_source")
        from epitoperank.neoantigen import discover_cds_tables, pick_cds_table

        cds_table = pick_cds_table(discover_cds_tables(directory))
        if cds_table is None:
            return ToolResult(False, "项目里没有可用的 CDS 表（需要 event_id / reference_cds / altered_cds / junction_nt 四列，文件名不限）",
                              error="no_cds")
        alleles = [str(item) for item in (args.get("alleles") or []) if str(item).strip()][:8]
        if not alleles:
            return ToolResult(False, "alleles is required", error="bad_argument")
        mhc_class = args.get("mhc_class") if args.get("mhc_class") in {"class1", "class2", "both"} else "both"
        processing = bool(args.get("processing", False))
        from epitoperank.peptide import PeptideOptions, run as run_peptide

        output = self.settings.paths.runtime_root / "projects" / self.project_id / "peptide_results" / f"copilot-{int(time.time())}"
        options = PeptideOptions(alleles=alleles, mhc_class=mhc_class,
                                 processing=processing, lookup_epitopes=False,
                                 max_predictions=600)
        result = run_peptide(output_dir=output, input_dir=directory,
                             cds_table=cds_table, options=options)
        top = []
        ranked = output / "ranked_candidates.tsv"
        if ranked.is_file():
            import csv

            with ranked.open(encoding="utf-8") as handle:
                for row in list(csv.DictReader(handle, delimiter="\t"))[:10]:
                    top.append({
                        "peptide": row.get("peptide"),
                        "allele": row.get("best_allele"),
                        "percentile": row.get("percentile_rank"),
                        "tier": row.get("evidence_tier"),
                        "score": row.get("composite_score"),
                    })
        return ToolResult(True, f"{result['candidate_count']} peptides, {result['prediction_count']} predictions",
                          {"output_dir": str(output), "top": top,
                           "errors": result.get("errors", [])[:3]})

    def _interpretation(self) -> ToolResult:
        if not self.project_id:
            return ToolResult(False, "no active project", error="no_project")
        rows = self.memory.load_interpretations(self.project_id)
        compact = [{"agent": row.get("agent"), "content": str(row.get("content") or "")[:4000]}
                   for row in rows[-3:]]
        return ToolResult(True, f"{len(compact)} interpretation blocks", {"interpretations": compact})

    def _plan(self) -> ToolResult:
        if not self.project_id:
            return ToolResult(False, "no active project", error="no_project")
        plan = self.memory.load_plan(self.project_id) or {}
        if not plan:
            return ToolResult(False, "no stored plan for this project", error="no_plan")
        keys = ("goal", "steps", "thresholds", "params", "hypotheses",
                "limitations", "potential_limitations", "validation")
        compact = {key: plan.get(key) for key in keys if key in plan}
        return ToolResult(True, f"plan with {len(compact)} sections", compact)


# ----------------------------------------------------------------------
# The agent loop
# ----------------------------------------------------------------------
@dataclass
class CopilotAnswer:
    answer: str = ""
    mode: str = "llm"  # llm | offline | error
    project_id: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    steps: int = 0
    usage: dict[str, int] = field(default_factory=dict)
    grounding: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    model: str = ""
    strategy: str = "react"  # react | plan
    plan: dict[str, Any] = field(default_factory=dict)
    critique: dict[str, Any] = field(default_factory=dict)
    cache: dict[str, Any] = field(default_factory=dict)
    cancelled: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "mode": self.mode,
            "project_id": self.project_id,
            "tool_calls": self.tool_calls,
            "steps": self.steps,
            "usage": self.usage,
            "grounding": self.grounding,
            "errors": self.errors,
            "elapsed_seconds": self.elapsed_seconds,
            "model": self.model,
            "strategy": self.strategy,
            "plan": self.plan,
            "critique": self.critique,
            "cache": self.cache,
            "cancelled": self.cancelled,
        }


def _history_messages(history: Sequence[Mapping[str, Any]] | None) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for item in list(history or [])[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(item, Mapping):
            continue
        role = str(item.get("role") or "")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content[:4000]})
    return messages


def _offline_answer(tools: CopilotTools, message: str, *,
                    forced: bool = False, available: bool = False) -> CopilotAnswer:
    """Deterministic briefing used when the model is absent or bypassed.

    ``forced`` distinguishes "the caller asked for offline" from "no model is
    configured", so a configured server does not tell the user it has no key
    just because ``force_offline=true`` was sent.
    """
    started = time.monotonic()
    overview = tools.execute("project_overview", {})
    candidates = tools.execute("top_candidates", {"limit": 10}) if overview.ok else None
    enrichment = tools.execute("enrichment_summary", {"limit": 10}) if overview.ok else None
    quality = tools.execute("dataset_quality", {}) if overview.ok else None

    note = OFFLINE_FORCED_NOTE if (forced and available) else OFFLINE_NOTE
    lines = ["## 结论", "", note, ""]
    if overview.ok:
        data = overview.data or {}
        lines += [f"项目 **{data.get('name') or data.get('project_id')}**："
                  f"{data.get('events')} 个剪接事件，其中显著事件 {data.get('significant')} 个；"
                  f"样本 {data.get('samples')} 个，分组 {json.dumps(data.get('groups'), ensure_ascii=False)}。", ""]
        lines += ["## 关键证据", ""]
        lines.append(f"- 事件类型构成：{json.dumps(data.get('event_types'), ensure_ascii=False)}")
        if quality.ok and quality.data:
            lines.append(f"- 显著性比例：{quality.data.get('significant_ratio')}")
            for warning in quality.data.get("warnings") or []:
                lines.append(f"- 质量提示：{warning}")
        top = (candidates.data or {}).get("candidates", []) if candidates else []
        if top:
            lines.append("- 候选事件（前 5）：")
            for row in top[:5]:
                lines.append(f"  - {row.get('gene')} {row.get('event_type')} "
                             f"ΔPSI={row.get('delta_psi')} FDR={row.get('fdr')}")
        terms = (enrichment.data or {}).get("terms", []) if enrichment else []
        if terms:
            lines.append("- 富集条目（前 5）：")
            for row in terms[:5]:
                lines.append(f"  - {row.get('term')} ({row.get('ontology')}, FDR={row.get('fdr')})")
        lines += ["", "## 建议的下一步", "",
                  "- 配置 `MODEL_API_KEY` / `MODEL_API_BASE_URL` / `MODEL_NAME` 后启用工具调用型分析。",
                  "- 先确认分组配对与样本量，再讨论“肿瘤特异”。",
                  "- 如需候选肽，提供 `splice_orfs`/`coding_pairs` 表并运行肽预测。", ""]
        lines += ["## 局限", "",
                  "- 本摘要只读取已完成的分析结果，没有重新计算统计量。",
                  "- 未进行文献、通路与肽层面的外部核对。", ""]
    else:
        projects = tools.execute("list_projects", {})
        rows = (projects.data or {}).get("projects", []) if projects.ok else []
        lines += ["## 关键证据", "", "当前没有选中项目。可用项目："]
        for row in rows[:10]:
            lines.append(f"- {row.get('project_id')} · {row.get('name')} · 事件 {row.get('events')}")
        lines += ["", "## 建议的下一步", "", "- 在界面选择或创建一个项目后重试。", ""]
        lines += ["## 局限", "", "- 无项目上下文，无法回答项目问题。", ""]

    return CopilotAnswer(
        answer="\n".join(lines),
        mode="offline",
        project_id=tools.project_id,
        tool_calls=list(tools.calls),
        steps=len(tools.calls),
        usage={},
        grounding={"checked": 0, "unverified": [], "severity": "ok", "note": "offline"},
        errors=[],
        elapsed_seconds=round(time.monotonic() - started, 3),
        model="",
    )


def _should_plan(message: str) -> bool:
    text = (message or "").lower()
    if len(text) > 120:
        return True
    if text.count("?") + text.count("？") >= 2:
        return True
    return any(trigger in text for trigger in PLAN_TRIGGERS)


def _emit(on_event: Callable[[dict[str, Any]], None] | None,
          event: str, data: Any) -> None:
    if on_event is None:
        return
    try:
        on_event({"event": event, "data": data})
    except Exception:  # noqa: BLE001 - a broken listener must not break the answer
        pass


#: Template artefacts some providers occasionally leak into message content
#: (observed on DeepSeek after a tool-using turn when tools are then disabled).
_ARTIFACT_LINE = re.compile(r"(?m)^.*(?:DSML|<\|(?:im_start|tool_call|endoftext)\|).*$\n?")
_ARTIFACT_TAG = re.compile(r"<[^>\n]{0,40}DSML[^>\n]{0,40}>")


def _sanitize_model_text(text: str) -> str:
    """Drop provider template/tool-call artefacts from model prose."""
    if not text:
        return text
    if "DSML" not in text and "<|" not in text:
        return text
    cleaned = _ARTIFACT_LINE.sub("", text)
    cleaned = _ARTIFACT_TAG.sub("", cleaned)
    return cleaned.strip()


def ask(
    message: str,
    settings: Settings,
    *,
    project_id: str | None = None,
    history: Sequence[Mapping[str, Any]] | None = None,
    max_steps: int = MAX_STEPS,
    client: ChatClient | None = None,
    force_offline: bool = False,
    mode: str = "auto",
    allow_network: bool = True,
    use_cache: bool = True,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    cancel: Callable[[], bool] | None = None,
    max_revisions: int = 1,
) -> CopilotAnswer:
    """Answer one analyst question with tool use (or a deterministic briefing).

    ``mode`` selects the orchestration strategy:

    * ``react`` — the classic bounded tool loop;
    * ``plan`` — plan first, execute, then critic review (one revision allowed);
    * ``auto`` — plan for multi-part/long questions, react otherwise.
    """
    text = (message or "").strip()
    if not text:
        raise ValueError("message is required")
    strategy = mode if mode in {"plan", "react"} else (
        "plan" if _should_plan(text) else "react")
    started = time.monotonic()
    tools = CopilotTools(settings, project_id=project_id, allow_network=allow_network,
                         use_cache=use_cache)
    chat = client or ChatClient(settings)

    if force_offline or not chat.available:
        answer = _offline_answer(tools, text, forced=force_offline,
                                 available=chat.available)
        answer.strategy = strategy
        if strategy == "plan":
            plan = heuristic_plan(text, project_id=project_id, tools=tools.specs())
            answer.plan = plan.as_dict()
            _emit(on_event, "plan", plan.as_dict())
        answer.critique = critique_answer(
            text, answer.answer, settings=settings, client=None, plan=None,
            tool_calls=tools.calls, grounding=answer.grounding, project_id=project_id,
        )
        _emit(on_event, "critique", answer.critique)
        answer.elapsed_seconds = round(time.monotonic() - started, 3)
        answer.cache = tools.cache.stats()
        if not force_offline and not chat.available:
            answer.errors.append("LLM endpoint not configured")
        _emit(on_event, "offline", {"mode": answer.mode})
        return answer

    system = SYSTEM_PROMPT
    if project_id:
        system += f"\n\n当前项目：{project_id}。默认使用该项目的记忆与文件；需要其他项目时调用 list_projects。"
    else:
        system += "\n\n当前未选择项目；需要项目数据时先调用 list_projects，再把 project_id 传给工具。"
    if not allow_network:
        system += "\n\n本轮已禁用联网工具（文献/注释/通路/肽预测）。需要这些证据时明确说明未获取。"

    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    messages += _history_messages(history)
    messages.append({"role": "user", "content": text[:8000]})
    specs = tools.specs()
    tool_names = [item["function"]["name"] for item in specs]
    answer = CopilotAnswer(project_id=project_id or "", model=chat.model,
                           strategy=strategy)
    plan: Plan | None = None

    if strategy == "plan":
        plan = make_plan(text, settings, chat, project_id=project_id, tools=specs,
                         history=history)
        messages[0]["content"] = system + "\n\n" + plan.prompt_text(tool_names)
        answer.plan = plan.as_dict()
        _emit(on_event, "plan", plan.as_dict())

    final_text = ""
    steps = 0
    model_calls = 0

    for step in range(max(1, int(max_steps))):
        if cancel is not None and cancel():
            answer.cancelled = True
            answer.errors.append("cancelled by client")
            break
        if model_calls >= MAX_MODEL_CALLS:
            answer.errors.append("model call budget exhausted")
            break
        steps = step + 1
        _emit(on_event, "step", {"step": steps, "max_steps": max_steps})
        try:
            result: ChatResult = chat.complete(messages, tools=specs)
            model_calls += 1
        except ChatError as error:
            answer.errors.append(str(error))
            break
        if not result.tool_calls:
            final_text = _sanitize_model_text(result.text.strip())
            break
        messages.append(result.message)
        for call in result.tool_calls[:MAX_CALLS_PER_STEP]:
            if cancel is not None and cancel():
                answer.cancelled = True
                break
            _emit(on_event, "tool_start", {"tool": call.name, "arguments": call.parsed()})
            outcome = tools.execute(call.name, call.parsed())
            _emit(on_event, "tool_result", {
                "tool": call.name,
                "ok": outcome.ok,
                "cached": outcome.cached,
                "summary": outcome.summary[:300],
                "error": outcome.error[:200],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.name,
                "content": outcome.as_content(),
            })
        # Keep the transcript bounded even under many tool calls.
        if len(messages) > 40:
            messages = messages[:1] + messages[-38:]
        if answer.cancelled:
            break

    if not final_text and not answer.cancelled:
        # Force a synthesis turn when the model kept calling tools.
        try:
            result = chat.complete(messages + [{
                "role": "user",
                "content": "请停止调用工具，基于上面已有结果给出最终回答（四段式，不要编造数字）。",
            }], tools=None)
            model_calls += 1
            final_text = _sanitize_model_text(result.text.strip())
        except ChatError as error:
            answer.errors.append(str(error))

    if not final_text:
        if answer.cancelled:
            final_text = "（本次请求已被取消，未生成完整回答。）"
        else:
            fallback = _offline_answer(tools, text)
            final_text = fallback.answer
            answer.mode = "offline"
            answer.errors.append("model produced no final answer; returned deterministic briefing")

    grounding = grounding_report(final_text, tools.results)
    critique = critique_answer(
        text, final_text, settings=settings,
        client=chat if strategy == "plan" else None,
        plan=plan, tool_calls=tools.calls, grounding=grounding, project_id=project_id,
    )
    _emit(on_event, "critique", critique)

    if (critique.get("verdict") == "revise" and max_revisions > 0
            and not answer.cancelled and chat.available):
        try:
            messages.append({"role": "assistant", "content": final_text})
            messages.append({"role": "user", "content": revision_instruction(critique)})
            # Keep the system prompt: slicing only the tail can drop it and the
            # revision then loses the tool/grounding rules.
            revision_messages = [messages[0]] + messages[-9:]
            result = chat.complete(revision_messages, tools=None)
            model_calls += 1
            revised = _sanitize_model_text((result.text or "").strip())
            usable = bool(revised) and "## 结论" in revised and len(revised) >= 80
            if usable:
                final_text = revised
                grounding = grounding_report(final_text, tools.results)
                critique = critique_answer(
                    text, final_text, settings=settings, client=None, plan=plan,
                    tool_calls=tools.calls, grounding=grounding, project_id=project_id,
                )
                _emit(on_event, "revision", {"grounding": grounding, "critique": critique})
            else:
                answer.errors.append("revision output was unusable; kept the original answer")
                _emit(on_event, "revision_rejected", {"reason": "artefact or missing sections"})
        except ChatError as error:
            answer.errors.append(f"revision failed: {error}")

    answer.answer = final_text
    answer.tool_calls = list(tools.calls)
    answer.steps = steps
    answer.usage = chat.usage.as_dict()
    answer.grounding = grounding
    answer.critique = critique
    answer.cache = tools.cache.stats()
    answer.elapsed_seconds = round(time.monotonic() - started, 3)
    _emit(on_event, "final", {"steps": steps, "elapsed_seconds": answer.elapsed_seconds})
    return answer


def status(settings: Settings, *, project_id: str | None = None,
           allow_network: bool = True) -> dict[str, Any]:
    """Describe the copilot's readiness without spending tokens."""
    chat = ChatClient(settings)
    tools = CopilotTools(settings, project_id=project_id, allow_network=allow_network)
    return {
        "chat": chat.status(),
        "tools": tools.describe(),
        "network_tools": sorted(NETWORK_TOOLS),
        "allow_network": allow_network,
        "limits": {
            "max_steps": MAX_STEPS,
            "max_tool_calls": MAX_TOOL_CALLS,
            "max_calls_per_step": MAX_CALLS_PER_STEP,
            "max_network_calls": MAX_NETWORK_CALLS,
            "max_model_calls": MAX_MODEL_CALLS,
            "max_tool_result_chars": MAX_TOOL_RESULT_CHARS,
        },
        "cache": tools.cache.stats(),
        "strategies": ["react", "plan", "auto"],
        "mode": "llm" if chat.available else "offline",
    }
