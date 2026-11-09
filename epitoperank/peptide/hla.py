"""HLA allele parsing, validation and curated allele panels.

The parser is strict on purpose: a typo in an allele name silently changes
every downstream prediction, so malformed names are rejected instead of being
guessed at.  Panels are *commonly typed alleles*, not population frequencies;
frequency-weighting requires the AFND / IEDB population data for the cohort
being studied and is not bundled here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Class-I loci handled by the IEDB MHC-I tools.
CLASS_I_LOCI = ("A", "B", "C", "E", "F", "G")
#: Class-II loci handled by the IEDB MHC-II tools.
CLASS_II_LOCI = ("DRB1", "DRB3", "DRB4", "DRB5", "DQA1", "DQB1", "DPA1", "DPB1")

#: Two-field (allele group + protein) class-I name, e.g. ``HLA-A*02:01``.
_CLASS_I_RE = re.compile(r"^HLA-(?P<locus>[ABC])\*(?P<group>\d{2,3}):(?P<protein>\d{2,3})$")
#: Class-II single-chain name, e.g. ``HLA-DRB1*15:01``.
_CLASS_II_RE = re.compile(
    r"^HLA-(?P<locus>DRB[1-5]|DQA1|DQB1|DPA1|DPB1)"
    r"\*(?P<group>\d{2,3}):(?P<protein>\d{2,3})$"
)
#: Class-II alpha/beta pair, e.g. ``DPA1*01:03/DPB1*04:01``.
_CLASS_II_PAIR_RE = re.compile(
    r"^(?:HLA-)?(?P<alpha>(?:DQA1|DPA1)\*\d{2,3}:\d{2,3})/(?P<beta>(?:DQB1|DPB1)\*\d{2,3}:\d{2,3})$"
)

#: Curated, partial HLA supertype map (Sidney et al. 2008 class-I supertypes).
#: Unknown alleles deliberately return ``None`` instead of a guess.
SUPERTYPES: dict[str, str] = {
    "HLA-A*01:01": "A01",
    "HLA-A*02:01": "A02",
    "HLA-A*02:03": "A02",
    "HLA-A*02:06": "A02",
    "HLA-A*02:07": "A02",
    "HLA-A*03:01": "A03",
    "HLA-A*11:01": "A03",
    "HLA-A*23:01": "A24",
    "HLA-A*24:02": "A24",
    "HLA-A*26:01": "A26",
    "HLA-A*30:01": "A03",
    "HLA-A*31:01": "A03",
    "HLA-A*33:01": "A03",
    "HLA-A*68:01": "A03",
    "HLA-A*68:02": "A02",
    "HLA-B*07:02": "B07",
    "HLA-B*08:01": "B08",
    "HLA-B*15:01": "B62",
    "HLA-B*27:05": "B27",
    "HLA-B*35:01": "B07",
    "HLA-B*40:01": "B44",
    "HLA-B*44:02": "B44",
    "HLA-B*44:03": "B44",
    "HLA-B*57:01": "B58",
    "HLA-B*58:01": "B58",
}

#: Commonly typed class-I alleles in research cohorts.  A convenience default,
#: **not** a population frequency table.
CLASS_I_PANEL: tuple[str, ...] = (
    "HLA-A*01:01", "HLA-A*02:01", "HLA-A*03:01", "HLA-A*11:01",
    "HLA-A*23:01", "HLA-A*24:02", "HLA-A*26:01", "HLA-A*31:01",
    "HLA-B*07:02", "HLA-B*08:01", "HLA-B*15:01", "HLA-B*27:05",
    "HLA-B*35:01", "HLA-B*40:01", "HLA-B*44:02", "HLA-B*44:03",
    "HLA-B*57:01", "HLA-B*58:01", "HLA-C*07:02", "HLA-C*04:01",
)

#: Commonly typed class-II alleles (DRB1 plus a representative DP/DQ pair).
CLASS_II_PANEL: tuple[str, ...] = (
    "HLA-DRB1*01:01", "HLA-DRB1*03:01", "HLA-DRB1*04:01", "HLA-DRB1*07:01",
    "HLA-DRB1*09:01", "HLA-DRB1*11:01", "HLA-DRB1*13:02", "HLA-DRB1*15:01",
    "HLA-DPA1*01:03/DPB1*04:01", "HLA-DQA1*05:01/DQB1*02:01",
)


class HlaError(ValueError):
    """Raised for an allele name that cannot be used for prediction."""


@dataclass(frozen=True)
class HlaAllele:
    """A validated allele with its locus and MHC class."""

    name: str
    locus: str
    mhc_class: int
    supertype: str | None = None

    def as_dict(self) -> dict[str, object]:
        """导出等位基因名、基因座、MHC 类别与（若已知）超型。"""
        return {
            "allele": self.name,
            "locus": self.locus,
            "mhc_class": self.mhc_class,
            "supertype": self.supertype,
        }


# 中文备注：肽预测：规范化HLA 型别（参数：value、strict）
def normalize_allele(value: object, *, strict: bool = True) -> str:
    """Return the canonical IEDB name, e.g. ``HLA-A*02:01``.

    Accepts the common shorthands ``A*02:01``, ``HLA-A*02:1`` (single-digit
    protein field) and class-II alpha/beta pairs.  With ``strict=False`` a
    non-conforming string is returned stripped and uppercased instead of
    raising, which is convenient for user-facing form validation.
    """
    if not isinstance(value, str):
        raise HlaError("allele must be a string")
    raw = "".join(value.split()).upper()
    if not raw:
        raise HlaError("allele is empty")
    raw = raw.replace("HLA-", "")
    pair = _CLASS_II_PAIR_RE.match(raw)
    if pair:
        return f"HLA-{pair.group('alpha')}/{pair.group('beta')}"
    if "*" not in raw:
        raise HlaError(f"allele must include a '*' separator: {value!r}")
    locus, _, rest = raw.partition("*")
    group, _, protein = rest.partition(":")
    if not protein:
        raise HlaError(f"allele needs at least two fields, e.g. A*02:01: {value!r}")
    # Normalise the protein field to two digits (02:1 -> 02:01).
    if len(protein) == 1:
        protein = protein.zfill(2)
    candidate = f"HLA-{locus}*{group}:{protein}"
    if _CLASS_I_RE.match(candidate) or _CLASS_II_RE.match(candidate):
        return candidate
    if strict:
        raise HlaError(
            f"unsupported HLA allele {value!r}; use two-field names such as "
            "HLA-A*02:01 or HLA-DRB1*15:01"
        )
    return candidate


# 中文备注：肽预测：辅助处理MHCclass（参数：allele）
def mhc_class(allele: str) -> int:
    """1 for A/B/C, 2 for DR/DQ/DP."""
    name = normalize_allele(allele)
    if _CLASS_I_RE.match(name):
        return 1
    if _CLASS_II_RE.match(name) or _CLASS_II_PAIR_RE.match(name.replace("HLA-", "", 1)):
        return 2
    raise HlaError(f"cannot determine MHC class for {allele!r}")


def locus(allele: str) -> str:
    """抽取基因座名称，如 ``HLA-DRB1*15:01`` 返回 ``DRB1``。"""
    name = normalize_allele(allele)
    return name.replace("HLA-", "").split("*", 1)[0].split("/", 1)[0]


def describe(allele: str) -> HlaAllele:
    """标准化等位基因名并返回含基因座、MHC 类别、超型的完整描述。"""
    name = normalize_allele(allele)
    return HlaAllele(
        name=name,
        locus=locus(name),
        mhc_class=mhc_class(name),
        supertype=SUPERTYPES.get(name),
    )


# 中文备注：肽预测：解析panel（参数：values、allow_mixed_classes）
def parse_panel(values: object, *, allow_mixed_classes: bool = False) -> list[HlaAllele]:
    """Validate an allele list and return deduplicated :class:`HlaAllele` objects."""
    if isinstance(values, str):
        values = [item for item in re.split(r"[,\s;]+", values) if item]
    if not isinstance(values, (list, tuple, set)):
        raise HlaError("alleles must be a list of allele names")
    alleles = []
    seen: set[str] = set()
    for value in values:
        allele = describe(str(value))
        if allele.name in seen:
            continue
        seen.add(allele.name)
        alleles.append(allele)
    if not alleles:
        raise HlaError("at least one HLA allele is required")
    classes = {allele.mhc_class for allele in alleles}
    if len(classes) > 1 and not allow_mixed_classes:
        raise HlaError(
            "class-I and class-II alleles must be predicted separately "
            "(set allow_mixed_classes=True to split them)"
        )
    return alleles


def split_by_class(alleles: list[HlaAllele]) -> dict[int, list[HlaAllele]]:
    """按 MHC 类别（1 或 2）把等位基因分组，供两类预测分别提交。"""
    grouped: dict[int, list[HlaAllele]] = {1: [], 2: []}
    for allele in alleles:
        grouped[allele.mhc_class].append(allele)
    return grouped


# 中文备注：肽预测：辅助处理panel（参数：name）
def panel(name: str) -> list[str]:
    """Look up a bundled convenience panel by name."""
    key = name.strip().lower().replace("-", "_")
    if key in {"class1_common", "class_i", "class1"}:
        return list(CLASS_I_PANEL)
    if key in {"class2_common", "class_ii", "class2"}:
        return list(CLASS_II_PANEL)
    raise HlaError(f"unknown HLA panel {name!r} (use class1_common or class2_common)")
