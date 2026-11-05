"""Optional local MHC predictors.

The platform's default predictor is the IEDB REST API, which needs no local
model download.  When ``mhcflurry`` is installed the same interface can be
served offline, which matters for large screens, air-gapped deployments and
reproducible reruns.

Nothing here is imported at module load time; a missing package simply makes
:func:`available` return ``False``.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class LocalModelStatus:
    name: str
    available: bool
    version: str = ""
    detail: str = ""
    requires: str = "pip install mhcflurry"

    def as_dict(self) -> dict[str, object]:
        """把本地模型探测结果转为可序列化字典，供 API/报告展示。"""
        return {
            "name": self.name,
            "available": self.available,
            "version": self.version,
            "detail": self.detail,
            "requires": self.requires,
        }


def _version(module: object) -> str:
    """读取模块的 ``__version__``，缺失时返回空字符串。"""
    return str(getattr(module, "__version__", "") or "")


def mhcflurry_status() -> LocalModelStatus:
    """尝试导入 mhcflurry 探测本地可用性；不联网，导入失败即视为不可用。"""
    try:
        module = importlib.import_module("mhcflurry")
    except Exception as exc:  # noqa: BLE001 - optional by design
        return LocalModelStatus("mhcflurry", False, detail=str(exc)[:200])
    return LocalModelStatus("mhcflurry", True, version=_version(module),
                            detail="Class1AffinityPredictor / Class1PresentationPredictor")


def available() -> bool:
    """本地 MHCflurry 是否已安装，供调用方决定走本地打分还是 IEDB。"""
    return mhcflurry_status().available


def _load_predictor(presentation: bool = False):
    """加载并返回本地 MHCflurry 预测器（呈递或亲和力模型）。"""
    import mhcflurry  # local import keeps startup cheap

    if presentation and hasattr(mhcflurry, "Class1PresentationPredictor"):
        predictor = mhcflurry.Class1PresentationPredictor.load()
    else:
        predictor = mhcflurry.Class1AffinityPredictor.load()
    return predictor


def predict_mhci(peptides: Sequence[str], alleles: Sequence[str], *,
                 presentation: bool = False) -> list[dict[str, object]]:
    """Run MHCflurry locally and return records shaped like the IEDB client's.

    Raises :class:`RuntimeError` when the optional dependency is missing so
    callers can fall back to IEDB explicitly instead of silently degrading.
    """
    if not available():
        raise RuntimeError(
            "mhcflurry is not installed; install it with 'pip install mhcflurry' "
            "or use predictor='iedb'"
        )
    predictor = _load_predictor(presentation=presentation)
    records: list[dict[str, object]] = []
    for allele in alleles:
        frame = predictor.predict_to_dataframe(allele=allele, peptides=list(peptides))
        for row in frame.to_dict(orient="records"):
            peptide = str(row.get("peptide") or "").upper()
            percentile = row.get("mhcflurry_affinity_percentile")
            if percentile is None:
                percentile = row.get("mhcflurry_presentation_percentile")
            records.append({
                "peptide": peptide,
                "allele": allele,
                "mhc_class": 1,
                "method": "mhcflurry_presentation" if presentation else "mhcflurry_affinity",
                "method_label": "MHCflurry (local, presentation)" if presentation else "MHCflurry (local, affinity)",
                "score": row.get("mhcflurry_affinity"),
                "percentile_rank": percentile,
                "core": "",
                "request_id": "local",
                "source": "mhcflurry",
                "raw": {key: (None if value != value else value) for key, value in row.items()},
            })
    return records


def status() -> dict[str, object]:
    """返回本地预测器状态的字典形式，用于运行清单与界面展示。"""
    return mhcflurry_status().as_dict()
