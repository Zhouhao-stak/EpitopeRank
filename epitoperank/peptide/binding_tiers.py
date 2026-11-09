"""HLA 结合预测结果的自动分级、排序与导出。

判读口径（README 与 docs/PEPTIDE.md 一致）：
* ``percentile_rank < 0.5``  → ``strong``（强结合）
* ``0.5 <= rank < 2.0``     → ``weak``（弱结合）
* ``rank >= 2.0``           → ``none``（不列为候选）

此前这个分级需要人工读取 ``mhc_i_predictions.tsv`` 后自行统计；
本模块让平台在每次预测后自动产出 ``ranked_candidates.tsv``，
并把分档计数、Top 候选写进 manifest。
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

STRONG_CUTOFF = 0.5
WEAK_CUTOFF = 2.0

RANKED_FIELDS = (
    "rank", "peptide", "allele", "percentile_rank", "binding_tier", "score",
    "event_id", "gene_symbol", "gene_id", "event_type", "fdr", "delta_psi",
    "length", "start_aa", "junction_aa", "method",
)


def classify(percentile_rank: Any) -> tuple[str, float | None]:
    """返回 ``(binding_tier, 数值 rank)``；无法解析时 tier 为 ``unknown``。"""
    try:
        value = float(percentile_rank)
    except (TypeError, ValueError):
        return "unknown", None
    if value < STRONG_CUTOFF:
        return "strong", value
    if value < WEAK_CUTOFF:
        return "weak", value
    return "none", value


def rank_predictions(scores: Iterable[dict], candidates: Iterable[dict]) -> list[dict]:
    """把预测分数与候选肽元数据合并，按 percentile_rank 升序排名。

    同一肽可能来自多个事件，取 FDR 最小（并列时取 |ΔPSI| 最大）的事件作为代表，
    其余关联仍保留在 ``splice_peptides.tsv`` 中。
    """
    by_peptide: dict[str, dict] = {}
    for item in candidates:
        peptide = str(item.get("peptide") or "")
        if not peptide:
            continue
        current = by_peptide.get(peptide)
        if current is None or _candidate_key(item) < _candidate_key(current):
            by_peptide[peptide] = item
    rows = []
    for score in scores:
        peptide = str(score.get("peptide") or "")
        tier, value = classify(score.get("percentile_rank"))
        meta = by_peptide.get(peptide, {})
        rows.append({
            "peptide": peptide,
            "allele": str(score.get("allele") or ""),
            "percentile_rank": score.get("percentile_rank", ""),
            "binding_tier": tier,
            "score": score.get("score", ""),
            "event_id": meta.get("event_id", ""),
            "gene_symbol": meta.get("gene_symbol", ""),
            "gene_id": meta.get("gene_id", ""),
            "event_type": meta.get("event_type", ""),
            "fdr": meta.get("fdr", ""),
            "delta_psi": meta.get("delta_psi", ""),
            "length": meta.get("length", ""),
            "start_aa": meta.get("start_aa", ""),
            "junction_aa": meta.get("junction_aa", ""),
            "method": score.get("method", ""),
            "_sort": value if value is not None else float("inf"),
        })
    rows.sort(key=lambda r: (r["_sort"], r["peptide"], r["allele"]))
    for index, row in enumerate(rows, 1):
        row["rank"] = index
    return rows


def _candidate_key(item: dict) -> tuple[float, float]:
    """候选事件排序键：FDR 小者优先，其次 |ΔPSI| 大者优先。"""
    # 中文备注：肽预测：辅助处理float（参数：value、default）
    def _float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    fdr = _float(item.get("fdr"), 1.0)
    dpsi = abs(_float(item.get("delta_psi"), 0.0))
    return (fdr, -dpsi)


def write_ranked(path: str | Path, rows: Iterable[dict]) -> Path:
    """写出排好序的候选表。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RANKED_FIELDS, delimiter="\t",
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return target


def tier_summary(rows: Iterable[dict], *, top: int = 10) -> dict:
    """统计各档数量并给出 Top 候选，供 manifest 与界面状态栏使用。"""
    items = list(rows)
    counts = {tier: 0 for tier in ("strong", "weak", "none", "unknown")}
    for row in items:
        counts[row.get("binding_tier", "unknown")] = counts.get(row.get("binding_tier", "unknown"), 0) + 1
    best = [{
        "rank": row.get("rank"), "peptide": row.get("peptide"),
        "allele": row.get("allele"), "percentile_rank": row.get("percentile_rank"),
        "binding_tier": row.get("binding_tier"), "gene_symbol": row.get("gene_symbol"),
        "event_id": row.get("event_id"),
    } for row in items[:top]]
    return {
        "strong_cutoff": STRONG_CUTOFF, "weak_cutoff": WEAK_CUTOFF,
        "strong_count": counts["strong"], "weak_count": counts["weak"],
        "not_binding_count": counts["none"], "unknown_count": counts["unknown"],
        "total": len(items), "top_candidates": best,
        "interpretation": "percentile_rank < 0.5% 为强结合，< 2% 为弱结合；"
                          "EL 分数不等于实测亲和力或免疫原性。",
    }
