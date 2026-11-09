"""The decision engine: the agent's 'brain'.

One call answers "what do I do next, and why?". The engine is rule-first:

* blockers the reflector can fix come first (self-correction);
* otherwise a data-aware plan chain decides the next analytical step;
* an optional model advisory may add an *extra* insight step when the
  mandatory work is done — it can never override the safety order.

Rules run offline, so the agent behaves like an agent even without a model.
"""

from __future__ import annotations

from epitoperank.llm.trace import ReplayError

import json
from dataclasses import dataclass, field
from typing import Any, Sequence

from .actions import build_registry
from .interactive import ACCEPT_LIMITATION, EXTERNAL_CALL, RELAX_THRESHOLDS
from .reflector import MAX_RETRIES, remediate
from .skills_bridge import skills_enabled
from .state import AgentState
from epitoperank.llm.trace import traced_decision, model_request

DECIDE_SYSTEM = (
    "You are the decision module of EpitopeRank, an autonomous alternative-splicing "
    "analysis agent. You are given the agent's current state as JSON (facts about the "
    "dataset, parameters in use, open issues, actions already done). Choose ONE next "
    "action from the allowed list that adds the most scientific value, or answer "
    '{"action": null} if nothing further is worth doing. Reply with JSON only: '
    '{"action": "<name>", "args": {...}, "rationale": "<=30 words>"}. '
    "Never invent numbers; never repeat an action that is already done."
)

#: 自主规划提示词：允许模型使用全量动作表（含联网/写文件工具），并要求
#: 明确说明为什么这一步在当前证据下最有价值。执行与校验仍完全在本地。
PLAN_SYSTEM = (
    "You are the planning brain of EpitopeRank, an autonomous computational-biology "
    "agent running an OODA loop (observe, verify, decide, act, reflect). You are given "
    "the current blackboard as JSON: completed facts, open issues, chosen thresholds, "
    "actions already executed, unmet goal criteria, and the FULL list of available "
    "actions (including web_fetch, ORF reconstruction and MCP tool calls). "
    "Choose exactly ONE next action that best advances the unmet criteria. "
    "Prefer actions whose required facts are already satisfied. Do not repeat an "
    "action that has already succeeded unless there is a concrete reason in the issues. "
    "If a required input is missing (for example a CDS pair table), prefer an action "
    "that can create it from the available data. Reply with JSON only: "
    '{"action": "<name>", "args": {...}, "rationale": "<=30 words"}. '
    "Use only scalar argument values. Never invent numbers, gene names or file paths."
)


#: Actions that make no sense to repeat once they succeeded.
ONCE_ACTIONS = frozenset(
    {
        "summarize_dataset",
        "run_enrichment",
        "generate_figures",
        "collect_literature_evidence",
        "interpret_candidates",
        "generate_report",
        # Phase 2 actions: repeating them cannot add information.
        "test_hypothesis",
        "annotate_genes",
        "search_literature",
        "enrich_pathways",
        "interpret_splice_event",
    }
)

#: Actions that reach out to the network; gated by the skills kill switch.
EXTERNAL_ACTIONS = frozenset(
    {"annotate_genes", "search_literature", "enrich_pathways", "interpret_splice_event"}
)


@dataclass
class Decision:
    """What the agent decided to do next."""

    kind: str  # "act" | "stop"
    action: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    source: str = "rule"  # rule | reflection | llm | episodic
    confidence: float = 1.0

    def as_dict(self) -> dict[str, Any]:
        """序列化为字典（置信度保留两位小数），写入决策轨迹。"""
        return {
            "kind": self.kind,
            "action": self.action,
            "args": dict(self.args),
            "rationale": self.rationale,
            "source": self.source,
            "confidence": round(self.confidence, 2),
        }


def accept(state: AgentState, code: str, reason: str) -> None:
    """Record an issue as an accepted limitation (it no longer blocks)."""
    accepted = list(state.facts.get("accepted_limitations", []))
    accepted.append({"code": code, "reason": reason})
    state.facts["accepted_limitations"] = accepted
    state.resolve_issue(code)


class DecisionEngine:
    """Rule-first decision engine with an optional model advisory."""

    def __init__(
        self,
        state: AgentState,
        settings: Any | None = None,
        *,
        llm_advisory: bool = True,
        gate: Any | None = None,
    ) -> None:
        """构造决策引擎：载入动作注册表，并装配可选的模型顾问与人工确认闸门。"""
        self.state = state
        self.settings = settings
        self.registry = build_registry()
        self.llm_advisory = bool(llm_advisory)
        self._advisory_calls = 0
        agent_cfg = getattr(settings, "agent", None)
        #: 模型在 OODA 每一步参与规划；关闭后行为与旧版规则链完全一致。
        self.autonomous_planning = bool(getattr(agent_cfg, "autonomous_planning", True))
        self.plan_budget = max(0, int(getattr(agent_cfg, "plan_budget", 8) or 0))
        self._plan_calls = 0
        self.trace: list[dict[str, Any]] = []
        #: Optional human-in-the-loop gate (``autonomy: assisted``).
        self.gate = gate
        self._asked: set[str] = set()

    # -- public -----------------------------------------------------------
    @traced_decision
    def decide(self) -> Decision:
        """决定下一步动作：目标已达成则（或追加一步增强后）停止，否则先修 blocker、再按计划链推进。"""
        state = self.state
        satisfied, unmet = state.goal.evaluate(state)
        if satisfied:
            # 自主规划模式下模型已在每一步参与过决策，不再重复追加收尾洞察。
            if not self.autonomous_planning:
                decision = self._optional_insight()
                if decision is not None:
                    return decision
            return Decision("stop", rationale="Goal satisfied: " + ", ".join(c.code for c in state.goal.criteria))

        decision = self._fix_blockers()
        if decision is not None:
            return decision

        # 模型规划优先：每个 OODA 迭代都让模型从「完整动作表」里选下一步，
        # 规则链退居安全回退。校验、执行、预算仍全部在本地。
        decision = self._model_plan(unmet)
        if decision is not None:
            return decision

        decision = self._plan_step(unmet)
        if decision is not None:
            return decision

        if unmet:
            return Decision(
                "stop",
                rationale="Remaining criteria cannot be met within the action set: " + ", ".join(unmet),
            )
        return Decision("stop", rationale="Nothing left to do.")

    # -- self-correction --------------------------------------------------
    def _fix_blockers(self) -> Decision | None:
        """按严重程度遍历 blocker，返回第一条仍可执行的补救决策；无可补救则记为已接受限制。"""
        state = self.state
        for issue in state.blockers():
            if issue.code == "no_significant_events":
                decision = self._handle_empty_result(issue.code)
                if decision is not None:
                    return decision
                continue
            remedy = remediate(issue.code, state)
            if remedy is None or state.count_of(remedy.action) >= MAX_RETRIES.get(remedy.action, 1):
                self._accept(issue.code, f"No further remediation available ({issue.message})", issue.message)
                continue
            return Decision(
                "act",
                remedy.action,
                remedy.args,
                remedy.rationale,
                source="reflection",
                confidence=0.8,
            )
        return None

    def _handle_empty_result(self, code: str) -> Decision | None:
        """Zero significant events: re-filter with new params, else adapt, else accept."""
        state = self.state
        current = {"fdr": state.params.get("fdr"), "delta_psi": state.params.get("delta_psi")}
        used = state.facts.get("filtered_with")
        if used and used != current:
            return Decision(
                "act",
                "filter_significant_events",
                {"fdr_threshold": current["fdr"], "delta_psi_threshold": current["delta_psi"]},
                "Re-filtering with the newly adapted thresholds.",
                source="reflection",
            )
        if state.count_of("adapt_thresholds") < MAX_RETRIES["adapt_thresholds"]:
            remedy = remediate(code, state)
            if remedy is not None:
                return Decision("act", remedy.action, remedy.args, remedy.rationale, source="reflection")
        if int(state.params.get("expected_significant", 0)) == 0:
            self._accept(
                code,
                "No events pass even the most exploratory gate; reported as a limitation.",
                "zero events at every gate in the grid",
            )
            return None
        self._accept(
            code,
            "Threshold adaptation exhausted; reporting the empty result transparently.",
            "threshold adaptation exhausted",
        )
        return None

    def _accept(self, code: str, reason: str, detail: str = "") -> bool:
        """Record an issue as an accepted limitation (ask first when assisted)."""
        if code in self._asked:
            return True
        self._asked.add(code)
        if self.gate is not None and not self.gate.approve(
            ACCEPT_LIMITATION,
            "accept_limitation",
            f"Accept '{code}' as a reported limitation instead of fixing it?",
            detail or reason,
            default=True,
        ):
            return False
        accept(self.state, code, reason)
        return True

    # -- planning ---------------------------------------------------------
    def _plan_step(self, unmet: Sequence[str]) -> Decision | None:
        """依据当前事实拼出候选动作链，返回第一个未重复、前置条件满足且已获人工放行的动作。"""
        state = self.state
        facts = state.facts
        chain: list[tuple[str, dict[str, Any], str]] = []

        if not facts.get("profiled"):
            chain.append(("profile_dataset", {}, "Decide from evidence: profile the dataset first."))
        if not any(step.action == "summarize_dataset" for step in state.steps):
            chain.append(("summarize_dataset", {}, "Record the dataset overview for the methods section."))
        if not facts.get("filtered"):
            args = {"fdr_threshold": state.params.get("fdr"), "delta_psi_threshold": state.params.get("delta_psi")}
            chain.append(
                (
                    "filter_significant_events",
                    {key: value for key, value in args.items() if value is not None},
                    "Apply the significance and quality gates.",
                )
            )
        elif not facts.get("ranked"):
            chain.append(("rank_candidates", {"top_n": state.params.get("top_n")}, "Rank candidates by the composite score."))

        # -- Phase 2: challenge the result before interpreting it ----------
        if facts.get("has_significant") and not facts.get("hypotheses_run") and self._hypothesis_enabled():
            chain.append(
                (
                    "test_hypothesis",
                    {},
                    "Challenge the result with pre-registered statistical tests before interpreting it.",
                )
            )

        if facts.get("has_annotation") and not any(step.action == "run_enrichment" for step in state.steps):
            chain.append(("run_enrichment", {}, "Annotation is available: run functional enrichment."))
        if self._needs_external_enrichment():
            chain.append(
                (
                    "enrich_pathways",
                    {},
                    (
                        "No local annotation: query an external pathway database for over-representation."
                        if not facts.get("has_annotation")
                        else "Local enrichment found nothing; try an external pathway database."
                    ),
                )
            )
        if not facts.get("figures"):
            chain.append(("generate_figures", {}, "Produce the figure set."))
        if not facts.get("evidence_done") and facts.get("candidates", 0) > 0:
            chain.append(("collect_literature_evidence", {"max_per_gene": 2}, "Gather literature evidence for the candidates."))

        # -- Step 3: check lab-level recurrence before interpreting ----------
        if facts.get("candidates") and not facts.get("knowledge_checked"):
            chain.append(
                ("consult_knowledge", {}, "Check lab-level recurrence before interpreting.")
            )

        # -- Phase 2: external knowledge (only when the kill switch allows) --
        external_ok = skills_enabled(self.settings)
        if external_ok:
            if self._needs_literature_search():
                chain.append(
                    (
                        "search_literature",
                        {"max_results": 5},
                        "Evidence coverage is thin; search PubMed/Europe PMC for the top gene.",
                    )
                )
            if not facts.get("annotated_genes") and facts.get("candidates", 0) > 0:
                chain.append(("annotate_genes", {}, "Annotate the candidate genes from an external source."))
            
            # Step 5: bioservices enhanced capabilities (when available)
            if not facts.get("ensembl_annotations") and facts.get("candidates", 0) > 0:
                try:
                    from epitoperank.integrations import bioservices_client
                    if bioservices_client.backend_available():
                        chain.append(
                            (
                                "annotate_genes_enhanced",
                                {"use_ensembl": True, "use_uniprot": False},
                                "Enhance gene annotations with Ensembl transcript details.",
                            )
                        )
                except ReplayError:
                    raise
                except Exception:
                    pass
            
            if not facts.get("bioservices_pathways") and facts.get("candidates", 0) > 0:
                try:
                    from epitoperank.integrations import bioservices_client
                    if bioservices_client.backend_available():
                        chain.append(
                            (
                                "enrich_pathways_bioservices",
                                {"use_kegg": True, "use_reactome": True},
                                "Supplement enrichment with KEGG/Reactome native pathways.",
                            )
                        )
                except ReplayError:
                    raise
                except Exception:
                    pass

        if not facts.get("interpreted"):
            chain.append(("interpret_candidates", {}, "Interpret the candidates biologically."))
        if external_ok and not facts.get("interpreted_events") and facts.get("candidates", 0) > 0:
            chain.append(
                (
                    "interpret_splice_event",
                    {},
                    "Interpret the clinical/functional meaning of the top splicing event.",
                )
            )
        if not facts.get("reported"):
            chain.append(("generate_report", {}, "Write the report."))

        for action_name, args, rationale in chain:
            if action_name in ONCE_ACTIONS and self._already_ok(action_name):
                continue
            if state.count_of(action_name) >= MAX_RETRIES.get(action_name, 3):
                continue
            if not self._requirements_met(action_name):
                continue
            if not self._cleared(action_name, rationale, args):
                continue
            clean = {key: value for key, value in args.items() if value is not None}
            return Decision("act", action_name, clean, rationale, source="rule")
        return None

    def _cleared(self, action_name: str, rationale: str, args: dict[str, Any]) -> bool:
        """Ask a human before decisions that are hard to undo (assisted mode)."""
        gate = self.gate
        if gate is None or not getattr(gate, "interactive", False):
            return True
        key = f"action:{action_name}"
        if key in self._asked:
            return True
        if action_name in EXTERNAL_ACTIONS:
            self._asked.add(key)
            return gate.approve(
                EXTERNAL_CALL,
                action_name,
                f"Call the external knowledge service for '{action_name}'?",
                rationale,
            )
        if action_name == "adapt_thresholds":
            self._asked.add(key)
            configured = self.state.context.settings.analysis
            return gate.approve(
                RELAX_THRESHOLDS,
                action_name,
                f"Relax the significance gates away from the configured "
                f"FDR<{configured.fdr_threshold}, |dPSI|>{configured.delta_psi_threshold}?",
                f"strategy={args.get('strategy', 'balanced')}; {rationale}",
            )
        return True

    def _hypothesis_enabled(self) -> bool:
        """是否启用假设检验（读取 agent.hypothesis_testing，缺省开启）。"""
        block = getattr(self.settings, "agent", None)
        return bool(getattr(block, "hypothesis_testing", True))

    def _needs_external_enrichment(self) -> bool:
        """True when no enrichment exists yet and an external call is worth it."""
        facts = self.state.facts
        if int(facts.get("enriched_terms", 0)) > 0:
            return False
        if any(step.action == "enrich_pathways" for step in self.state.steps):
            return False
        if facts.get("has_annotation"):
            # Only fall back to an external source after the local one ran.
            return any(step.action == "run_enrichment" for step in self.state.steps)
        return True

    def _needs_literature_search(self) -> bool:
        """True when the collected evidence covers too few candidate genes."""
        facts = self.state.facts
        if any(step.action == "search_literature" for step in self.state.steps):
            return False
        targets = int(facts.get("evidence_targets", 0))
        covered = int(facts.get("evidence_genes", 0))
        if targets == 0:
            return int(facts.get("candidates", 0)) > 0
        return covered / max(targets, 1) < 0.5

    def _already_ok(self, action_name: str) -> bool:
        """该动作此前是否已成功执行过（用于 once-only 动作去重）。"""
        return any(step.action == action_name and step.status == "ok" for step in self.state.steps)

    def _requirements_met(self, action_name: str) -> bool:
        """检查注册表中该动作声明的 requires 事实是否全部为真。"""
        action = self.registry.get(action_name)
        if action is None:
            return False
        return all(bool(self.state.facts.get(fact)) for fact in action.requires)

    # -- autonomous model planning ---------------------------------------
    def _model_plan(self, unmet: list[str]) -> Decision | None:
        """让模型在 OODA 的当前迭代里，从完整动作表中选择下一步动作。

        与旧的 ``_optional_insight`` 不同：这里在目标未达成时、每一步都会调用，
        动作范围是注册表全量（含联网 / 写文件类工具），因此模型可以连续多步
        自己规划，而不是只补一条洞察。所有提议仍要经过本地校验：
        动作是否存在、前置事实是否满足、重试次数是否超限、参数是否为标量。
        任何异常都静默退回规则链，离线运行不受影响。
        """
        if not self.autonomous_planning or self._plan_calls >= self.plan_budget:
            return None
        settings = self.settings
        if settings is None or not getattr(getattr(settings, "llm", None), "usable", False):
            return None
        state = self.state
        # 安全闸门：出图/出报告不能在筛选、排序、解读之前被模型提前触发，
        # 否则会写出一份内容不完整的报告并让目标提前达成。
        early_guard = {
            "generate_figures": ("filtered",),
            "generate_report": ("filtered", "ranked", "interpreted"),
        }
        from .mcp_actions import compact_schema

        available = [
            {"name": name, "description": action.description,
             **({"params": compact_schema(action.arg_schema)}
                if getattr(action, "arg_schema", None) else {})}
            for name, action in self.registry.items()
            if self._requirements_met(name)
            and not state_overused(state, name)
            and all(bool(state.facts.get(f)) for f in early_guard.get(name, ()))
        ]
        if not available:
            return None
        payload = {
            "unmet_criteria": unmet,
            "facts": state.facts,
            "issues": [issue.as_dict() for issue in state.issues],
            "params": state.params,
            "action_counts": dict(state.action_counts),
            "steps": [getattr(step, "action", "") for step in state.steps[-8:]],
            "available_actions": available,
        }
        self._plan_calls += 1
        try:
            from epitoperank.llm.enrich import LLMEnhancer, extract_json

            enhancer = LLMEnhancer(settings)
            text = model_request(enhancer,
                stage="model_plan",
                system=PLAN_SYSTEM,
                user=json.dumps(payload, ensure_ascii=False, default=str)[:9000],
                max_tokens=400, json_output=True, timeout=60,
            )
            data = extract_json(text or "")
            if not isinstance(data, dict):
                return None
            action = str(data.get("action") or "")
            if action not in {item["name"] for item in available}:
                return None
            raw_args = data.get("args") if isinstance(data.get("args"), dict) else {}
            selected = self.registry.get(action)
            if selected is not None and getattr(selected, "arg_schema", None):
                # Declared-schema tools (MCP) may receive structured values such
                # as peptide lists, but every value is validated and required
                # arguments must be present before the proposal is accepted.
                from .mcp_actions import validate_args

                args, _dropped = validate_args(selected.arg_schema, raw_args)
                if any(rule.get("required") and key not in args
                       for key, rule in selected.arg_schema.items()):
                    return None
            else:
                # Legacy actions keep the scalar-only guard: no arbitrary
                # structures or path objects may reach deterministic tools.
                args = {str(k): v for k, v in raw_args.items()
                        if isinstance(v, (str, int, float, bool))}
            rationale = str(data.get("rationale") or "model planning")[:200]
            decision = Decision("act", action, args, rationale,
                                source="llm", confidence=0.75)
            self.trace.append({"kind": "model_plan", "action": action,
                               "args": args, "rationale": rationale})
            return decision
        except ReplayError:
            raise
        except Exception:  # noqa: BLE001 - 规划是可选增强，失败必须回退规则链
            return None

    # -- optional model advisory -----------------------------------------
    def _optional_insight(self) -> Decision | None:
        """Once the mandatory work is done, ask the model for an extra step."""
        state = self.state
        if not self.llm_advisory or self._advisory_calls >= 2:
            return None
        settings = self.settings
        if settings is None or not getattr(getattr(settings, "llm", None), "usable", False):
            return None
        genes = state.context.top_genes(3) if state.context.candidates else []
        if not genes or state.count_of("deep_dive_gene") >= 1:
            return None
        self._advisory_calls += 1
        decision = self._ask_model(genes)
        if decision is not None:
            return decision
        return Decision(
            "act",
            "deep_dive_gene",
            {"gene": genes[0]},
            "Zoom into the top-ranked gene for a deeper, evidence-backed section.",
            source="rule",
            confidence=0.6,
        )

    def _ask_model(self, genes: list[str]) -> Decision | None:
        """向模型请求一步额外的可选动作；异常或输出不合规时一律返回 None。"""
        try:
            from epitoperank.llm.enrich import LLMEnhancer

            enhancer = LLMEnhancer(self.settings)
            payload = {
                "facts": self.state.facts,
                "issues": [issue.as_dict() for issue in self.state.issues],
                "top_genes": genes,
                "allowed_actions": [
                    "deep_dive_gene",
                    "collect_literature_evidence",
                    "run_enrichment",
                    "search_literature",
                    "annotate_genes",
                    "interpret_splice_event",
                ],
            }
            text = model_request(enhancer,
                stage="insight",
                system=DECIDE_SYSTEM,
                user=json.dumps(payload, ensure_ascii=False)[:4000],
                max_tokens=200,
                json_output=True,
                timeout=45,
            )
            if not text:
                return None
            from epitoperank.llm.enrich import extract_json

            data = extract_json(text)
            if not isinstance(data, dict):
                return None
            action = str(data.get("action") or "")
            args = data.get("args") if isinstance(data.get("args"), dict) else {}
            if action not in self.registry or not self._requirements_met(action):
                return None
            if state_overused(self.state, action):
                return None
            if action == "deep_dive_gene" and "gene" not in args and genes:
                args["gene"] = genes[0]
            return Decision(
                "act",
                action,
                args,
                str(data.get("rationale") or "model advisory")[:200],
                source="llm",
                confidence=0.7,
            )
        except ReplayError:
            raise
        except Exception:  # noqa: BLE001 - advisory is strictly optional
            return None


def state_overused(state: AgentState, action: str) -> bool:
    """该动作的执行次数是否已达重试上限。"""
    return state.count_of(action) >= MAX_RETRIES.get(action, 3)
