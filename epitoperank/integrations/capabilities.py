"""Capability probing: what optional backends are installed right now?

The agent consults this before deciding whether an external knowledge call
is worth attempting, and the report/API expose it so a user can see which
components are actually active.
"""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Capability:
    """One optional component the platform knows how to use."""

    name: str
    purpose: str
    available: bool
    version: str = ""
    backend: str = ""
    requires: str = ""

    def as_dict(self) -> dict[str, str]:
        """转成供 API 与报告使用的字典，available 保持布尔值。"""
        return {
            "name": self.name,
            "purpose": self.purpose,
            "available": self.available,
            "version": self.version,
            "backend": self.backend,
            "requires": self.requires,
        }


#: name -> (import name, purpose, extra requirement)
_SPEC: tuple[tuple[str, str, str, str], ...] = (
    (
        "enrichment",
        "gseapy",
        "GO/KEGG/Reactome/MSigDB over-representation analysis via Enrichr",
        "pip install gseapy",
    ),
    (
        "gene_annotation",
        "mygene",
        "Gene symbol / Ensembl / UniProt annotation via MyGene.info",
        "pip install mygene",
    ),
    (
        "statistics",
        "scipy",
        "Significance testing for the agent's hypothesis checks",
        "pip install scipy",
    ),
    (
        "http",
        "httpx",
        "Async HTTP for the literature, pathway and interpretation skills",
        "pip install httpx",
    ),
)


def _version_of(module: str) -> str:
    """先查包元数据、再导入模块取 __version__，两者都失败时返回空串。"""
    try:
        return str(metadata.version(module))
    except Exception:  # noqa: BLE001 - metadata is best-effort only
        try:
            mod = importlib.import_module(module)
            return str(getattr(mod, "__version__", "") or "")
        except Exception:  # noqa: BLE001
            return ""


@lru_cache(maxsize=1)
# 中文备注：外部集成：辅助处理capabilities（参数：无）
def capabilities() -> tuple[Capability, ...]:
    """Probe every known optional backend once per process."""
    found: list[Capability] = []
    for name, module, purpose, requires in _SPEC:
        try:
            importlib.import_module(module)
        except Exception:  # noqa: BLE001 - optional by definition
            found.append(
                Capability(
                    name=name,
                    purpose=purpose,
                    available=False,
                    backend=module,
                    requires=requires,
                )
            )
            continue
        found.append(
            Capability(
                name=name,
                purpose=purpose,
                available=True,
                version=_version_of(module),
                backend=module,
                requires=requires,
            )
        )
    return tuple(found)


# 中文备注：外部集成：判断backend（参数：name）
def has_backend(name: str) -> bool:
    """True when the capability ``name`` is importable."""
    return any(item.name == name and item.available for item in capabilities())


def available_backends() -> list[str]:
    """返回当前实际已安装的组件名列表。"""
    return [item.name for item in capabilities() if item.available]


def capability_report() -> dict[str, dict[str, str]]:
    """返回 组件名 -> 组件信息 的完整探测报告。"""
    return {item.name: item.as_dict() for item in capabilities()}
