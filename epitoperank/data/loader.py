"""Data layer: loading and validation of the Standard BioAnalysis Format.

EpitopeRank takes **rMATS input only**. Accepted layouts (auto-detected):

* a directory containing rMATS JC tables (``SE.MATS.JC.txt`` / ``.MATS.JCEC.txt``
  ...) plus an optional ``sample_metadata.tsv`` with the group assignment
* a single rMATS JC table
* a standardized ``AS_event_master.tsv`` — the internal contract produced by
  :mod:`epitoperank.data.ingestion` when a vendor rMATS export needs remapping
  (optional ``sample_metadata.tsv``, ``gene_annotation.tsv``,
  ``differential_expression.tsv``)

SUPPA2 / MAJIQ / LeafCutter / pre-computed delta-PSI inputs are no longer
accepted: one input contract keeps validation, tests and documentation honest.
The loader normalizes everything into one :class:`Dataset`.
"""

from __future__ import annotations

import csv
import gzip
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from epitoperank.splicing.parsers import (
    is_rmats_directory,
    parse_rmats_directory,
    parse_rmats_file,
)
from epitoperank.splicing.schema import (
    CORE_EVENT_FIELDS,
    StandardEvent,
    SampleMetadata,
    group_sample_ids,
    load_events_tsv,
    load_sample_metadata,
)

#: File names recognized in a standardized input directory.
STANDARD_EVENT_FILENAMES = (
    "AS_event_master.tsv",
    "as_event_master.tsv",
    "AS_event_master.csv",
    "as_event_master.csv",
    "AS_event_master_all.tsv",
    "as_event_master_all.tsv",
    "AS_event_master_all.csv",
    "as_event_master_all.csv",
    "events.tsv",
    "events.csv",
    "as_events.tsv",
    "as_events.csv",
)
METADATA_FILENAMES = (
    "sample_metadata.tsv",
    "sample_metadata.csv",
    "samples.tsv",
    "samples.csv",
    "metadata.tsv",
    "metadata.csv",
)
ANNOTATION_FILENAMES = (
    "gene_annotation.tsv",
    "gene_annotation.csv",
    "annotations.tsv",
    "gene_annotations.tsv",
)
DE_FILENAMES = (
    "differential_expression.tsv",
    "differential_expression.csv",
    "de_results.tsv",
    "de.tsv",
)

#: DE table columns required by the Standard BioAnalysis Format.
DE_FIELDS = ("gene_id", "log2FC", "pvalue", "padj", "baseMean")


@dataclass
class DifferentialGene:
    """One differential-expression row."""

    gene_id: str
    log2fc: float | None
    pvalue: float | None
    padj: float | None
    base_mean: float | None


@dataclass
class Dataset:
    """A loaded analysis input."""

    name: str
    source_dir: Path
    source_format: str
    events: list[StandardEvent]
    samples: list[SampleMetadata]
    annotation: dict[str, Any] = field(default_factory=dict)
    de_genes: list[DifferentialGene] = field(default_factory=list)
    extra_files: dict[str, Path] = field(default_factory=dict)

    @property
    def groups(self) -> dict[str, list[str]]:
        """按分组聚合样本，返回 {组名: [样本 ID, ...]}。"""
        return group_sample_ids(self.samples)

    @property
    def group_labels(self) -> tuple[str, str] | None:
        """返回排序后的首尾两个组名（对照组、实验组）；组数不足两个时返回 None。"""
        labels = sorted(self.groups)
        return (labels[0], labels[-1]) if len(labels) >= 2 else None

    def summary(self) -> dict[str, Any]:
        """生成数据集概要字典：事件数、样本数、各组规模、事件类型分布与注释/差异基因数量。"""
        event_types: dict[str, int] = {}
        for event in self.events:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
        return {
            "name": self.name,
            "source_dir": str(self.source_dir),
            "source_format": self.source_format,
            "event_count": len(self.events),
            "sample_count": len(self.samples),
            "groups": {group: len(ids) for group, ids in self.groups.items()},
            "event_types": event_types,
            "annotated_genes": len(self.annotation),
            "de_gene_count": len(self.de_genes),
        }


def _find_file(directory: Path, candidates: Iterable[str]) -> Path | None:
    """按候选文件名在目录中查找文件，同时兼容带数字前缀的供应商命名（如 01_sample_metadata.csv）。"""
    for name in candidates:
        path = directory / name
        if path.is_file():
            return path
    # Vendor exports often prefix the same names with a step number, e.g.
    # ``01_sample_metadata.csv`` or ``10_AS_event_master_all.csv``.
    lowered = [name.lower() for name in candidates]
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        filename = path.name.lower()
        for name in lowered:
            if not filename.endswith(name):
                continue
            prefix = filename[: len(filename) - len(name)].rstrip("_")
            if prefix == "" or prefix.isdigit():
                return path
    return None


def _has_standard_event_header(path: Path) -> bool:
    """True if the first row contains the full AS_event_master contract."""
    if path.suffix.lower() not in {".tsv", ".txt", ".csv"}:
        return False
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            header = next(csv.reader(handle, delimiter=delimiter), None)
    except (OSError, csv.Error):
        return False
    if not header:
        return False
    columns = {column.strip() for column in header}
    return set(CORE_EVENT_FIELDS).issubset(columns)


#: Header markers that identify a single rMATS JC table（小写，兼容各版本列名大小写）。
_RMATS_MARKERS = frozenset(
    {"inclevel1", "inc_level_1", "ijc_sample_1", "sjc_sample_1", "ijc_sample1", "sjc_sample1"}
)


def _looks_like_rmats_table(path: Path) -> bool:
    """True if ``path`` is one rMATS junction-count table.

    只按表头内容判断，不看文件名——客户的文件名千差万别，强制改名不可行。
    """
    name = path.name.lower()
    if name.endswith(".gz"):
        name = name[: -len(".gz")]
    if Path(name).suffix not in {".txt", ".tsv", ".csv", ".tab"}:
        return False
    try:
        opener = gzip.open if path.suffix.lower() == ".gz" else open
        with opener(path, "rt", encoding="utf-8-sig", errors="replace", newline="") as handle:
            header = next(csv.reader(handle, delimiter="\t"), None)
    except (OSError, csv.Error, UnicodeError):
        return False
    if not header:
        return False
    return any(column.strip().strip('"').lower() in _RMATS_MARKERS for column in header)


def _find_standard_event_table(directory: Path) -> Path | None:
    """定位标准化事件主表：先按约定文件名匹配，再回退到首个包含完整核心字段的表。"""
    path = _find_file(directory, STANDARD_EVENT_FILENAMES)
    if path:
        return path
    for candidate in sorted(directory.iterdir()):
        if candidate.is_file() and _has_standard_event_header(candidate):
            return candidate
    return None


def load_differential_expression(path: Path) -> list[DifferentialGene]:
    """Load a differential-expression table (gene_id/log2FC/pvalue/padj/baseMean)."""
    genes: list[DifferentialGene] = []
    delimiter = "," if path.suffix.lower() == ".csv" else "\t"
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle, delimiter=delimiter):
            gene_id = str(raw.get("gene_id", "")).strip()
            if not gene_id:
                continue
            genes.append(
                DifferentialGene(
                    gene_id=gene_id,
                    log2fc=_optional_float(raw.get("log2FC")),
                    pvalue=_optional_float(raw.get("pvalue")),
                    padj=_optional_float(raw.get("padj")),
                    base_mean=_optional_float(raw.get("baseMean")),
                )
            )
    return genes


def _optional_float(value: Any) -> float | None:
    """把单元格转成浮点数，空串、NA、NaN 等缺失标记返回 None。"""
    if value is None:
        return None
    text = str(value).strip()
    if text in {"", "NA", "NaN", "nan"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def load_dataset(input_path: str | Path) -> Dataset:
    """Load and normalize an analysis input directory.

    :raises FileNotFoundError: if the path does not exist.
    :raises ValueError: if no recognizable AS data is found.
    """
    directory = Path(input_path)
    if not directory.exists():
        raise FileNotFoundError(f"Input path not found: {directory}")

    samples: list[SampleMetadata] = []
    # 输入既可以是目录，也可以是单个文件；单文件时样本表放在同级目录里。
    is_directory_input = directory.is_dir()
    metadata_dir = directory if is_directory_input else directory.parent
    metadata_path = _find_file(metadata_dir, METADATA_FILENAMES) if metadata_dir.is_dir() else None
    if metadata_path:
        samples = load_sample_metadata(metadata_path)
    groups = group_sample_ids(samples)
    group_labels = sorted(groups)
    group1 = groups.get(group_labels[0], []) if group_labels else []
    group2 = groups.get(group_labels[-1], []) if len(group_labels) > 1 else []

    events: list[StandardEvent] = []
    source_format = "unknown"
    annotation: dict[str, Any] = {}
    de_genes: list[DifferentialGene] = []
    extra_files: dict[str, Path] = {}

    if is_directory_input:
        if is_rmats_directory(directory):
            source_format = "rMATS"
            events = parse_rmats_directory(directory, group1, group2)
        else:
            standard_path = _find_standard_event_table(directory)
            if standard_path:
                source_format = "standard"
                events = load_events_tsv(standard_path)
            else:
                seen = sorted(
                    entry.name
                    for entry in directory.iterdir()
                    if entry.is_file() and not entry.name.startswith(".")
                )[:8]
                raise ValueError(
                    f"No recognizable rMATS data in {directory}. "
                    "文件名不限定，程序按表头字段自动识别 SE/A3SS/A5SS/MXE/RI 五类结果表，"
                    "也接受 gzip 压缩；但文件内必须保留 rMATS 的计数列"
                    "（IncLevel1、IJC_SAMPLE_1、SJC_SAMPLE_1）与坐标列。"
                    "若数据已标准化，也可提供 AS_event_master.tsv。"
                    f"当前目录内的文件：{', '.join(seen) if seen else '（空目录）'}"
                )
        annotation_path = _find_file(directory, ANNOTATION_FILENAMES)
        if annotation_path:
            from epitoperank.analysis.enrichment import load_gene_annotation

            annotation = load_gene_annotation(annotation_path)
            extra_files["gene_annotation"] = annotation_path
        de_path = _find_file(directory, DE_FILENAMES)
        if de_path:
            de_genes = load_differential_expression(de_path)
            extra_files["differential_expression"] = de_path
    else:
        # A single file was given: one rMATS JC table or a standardized table.
        if _looks_like_rmats_table(directory):
            source_format = "rMATS"
            events = parse_rmats_file(directory)
        else:
            source_format = "standard"
            events = load_events_tsv(directory)

    if not events:
        raise ValueError(
            f"No AS events could be parsed from {directory}. "
            "文件里没有可解析的事件行；若只有 A3SS/A5SS 数据，这两类表头完全相同，"
            "需要在文件名中带上 A3SS 或 A5SS 才能确定类型。"
        )

    return Dataset(
        name=directory.name,
        source_dir=directory,
        source_format=source_format,
        events=events,
        samples=samples,
        annotation=annotation,
        de_genes=de_genes,
        extra_files=extra_files,
    )
