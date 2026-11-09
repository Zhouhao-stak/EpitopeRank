"""Transparent composite ranking for candidate peptides.

No single number can establish that a peptide is a real neoantigen.  The
composite score here is a *triage* aid: it puts the peptides with the best
combination of binding, processing, expression, effect size and novelty at the
top of the table, and it records exactly which components were available for
each row.  Missing evidence is never imputed; the score is renormalised over
the components that exist and the tier drops accordingly.
"""

from __future__ import annotations

import math
from typing import Iterable, Mapping

DEFAULT_WEIGHTS: dict[str, float] = {
    "binding": 0.40,       # best MHC-I/II percentile rank
    "processing": 0.20,    # IEDB proteasome + TAP + MHC score
    "expression": 0.15,    # measured event/gene expression
    "effect": 0.15,        # |ΔPSI| of the source splicing event
    "novelty": 0.10,       # absent from the supplied normal proteomes
}

#: Human-readable definition of what each component measures.
COMPONENT_DEFINITIONS: dict[str, str] = {
    "binding": "1 / (1 + percentile_rank / 0.5); higher for lower (better) percentile rank",
    "processing": "logistic transform of the IEDB processing total score",
    "expression": "log1p(expression) / log1p(100), capped at 1 (unit-dependent)",
    "effect": "min(1, |ΔPSI| / 0.5)",
    "novelty": "1 when the peptide is absent from the supplied normal proteomes, else 0",
}

#: Evidence tiers: which components must be present for each tier.
TIER_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("A", ("binding", "processing", "novelty", "expression")),
    ("B", ("binding", "novelty")),
    ("C", ("binding",)),
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """把分量得分限制在 [low, high] 区间内。"""
    return max(low, min(high, value))


def _number(value: object) -> float | None:
    """把输入转成有限浮点数；布尔、None、非数值和 NaN/inf 均返回 None。"""
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


# 中文备注：肽预测：辅助处理component分数（参数：row）
def component_scores(row: Mapping[str, object]) -> dict[str, float]:
    """Compute the available components for one candidate row."""
    components: dict[str, float] = {}
    percentile = _number(row.get("percentile_rank"))
    if percentile is not None:
        components["binding"] = _clamp(1.0 / (1.0 + max(percentile, 0.0) / 0.5))

    total = _number(row.get("processing_total_score"))
    if total is not None:
        components["processing"] = _clamp(1.0 / (1.0 + math.exp(-1.5 * total)))

    expression = _number(row.get("expression"))
    if expression is not None and expression >= 0:
        components["expression"] = _clamp(math.log1p(expression) / math.log1p(100.0))

    delta_psi = _number(row.get("delta_psi"))
    if delta_psi is not None:
        components["effect"] = _clamp(abs(delta_psi) / 0.5)

    if isinstance(row.get("self_hit"), bool):
        components["novelty"] = 0.0 if row.get("self_hit") else 1.0

    return components


def evidence_tier(components: Mapping[str, float]) -> str:
    """按已有分量判定证据等级 A/B/C，均不满足则归为 D（无结合预测）。"""
    for tier, required in TIER_RULES:
        if all(name in components for name in required):
            return tier
    return "D"


# 中文备注：肽预测：辅助处理composite（参数：row、weights）
def composite(row: Mapping[str, object], weights: Mapping[str, float] | None = None) -> dict[str, object]:
    """Attach score, tier and provenance to one candidate row."""
    weights = dict(weights or DEFAULT_WEIGHTS)
    components = component_scores(row)
    available = {name: value for name, value in components.items() if name in weights}
    total_weight = sum(weights[name] for name in available)
    score = (sum(weights[name] * value for name, value in available.items()) / total_weight
             if total_weight else 0.0)
    missing = [name for name in weights if name not in available]
    return {
        **dict(row),
        "composite_score": round(score, 4),
        "components": {name: round(value, 4) for name, value in components.items()},
        "components_used": sorted(available),
        "components_missing": sorted(missing),
        "evidence_tier": evidence_tier(components),
    }


# 中文备注：肽预测：排序rank（参数：rows、weights、limit）
def rank(rows: Iterable[Mapping[str, object]], *, weights: Mapping[str, float] | None = None,
         limit: int | None = None) -> list[dict[str, object]]:
    """Score and sort candidate rows, best first."""
    scored = [composite(row, weights) for row in rows]
    scored.sort(
        key=lambda item: (
            -float(item["composite_score"]),
            _number(item.get("percentile_rank")) if _number(item.get("percentile_rank")) is not None else 1000.0,
            str(item.get("peptide", "")),
        )
    )
    for index, item in enumerate(scored, start=1):
        item["rank"] = index
    return scored[:limit] if limit else scored


# 中文备注：肽预测：描述describe（参数：无）
def describe() -> dict[str, object]:
    """Machine-readable description used by the API and the report."""
    return {
        "weights": dict(DEFAULT_WEIGHTS),
        "definitions": dict(COMPONENT_DEFINITIONS),
        "tiers": {tier: list(required) for tier, required in TIER_RULES} | {"D": ["no binding prediction"]},
        "note": "Composite score is a triage aid, not evidence of presentation or immunogenicity.",
    }
