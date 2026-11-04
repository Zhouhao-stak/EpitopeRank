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
        return group_sample_ids(self.samples)

    @property
    def group_labels(self) -> tuple[str, str] | None:
        labels = sorted(self.groups)
        return (labels[0], labels[-1]) if len(labels) >= 2 else None

    def summary(self) -> dict[str, Any]:
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


#: Header markers that identify a single rMATS JC table.
_RMATS_MARKERS = ("IncLevel1", "IJC_SAMPLE_1", "SJC_SAMPLE_1")


def _looks_like_rmats_table(path: Path) -> bool:
    """True if ``path`` is one rMATS junction-count table."""
    if path.suffix.lower() not in {".txt", ".tsv", ".csv"}:
        return False
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            header = next(csv.reader(handle, delimiter="\t"), None)
    except (OSError, csv.Error):
        return False
    if not header:
        return False
    return any(marker in header for marker in _RMATS_MARKERS)


def _find_standard_event_table(directory: Path) -> Path | None:
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
    metadata_path = _find_file(directory, METADATA_FILENAMES)
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

    if directory.is_dir():
        if is_rmats_directory(directory):
            source_format = "rMATS"
            events = parse_rmats_directory(directory, group1, group2)
        else:
            standard_path = _find_standard_event_table(directory)
            if standard_path:
                source_format = "standard"
                events = load_events_tsv(standard_path)
            else:
                raise ValueError(
                    f"No recognizable rMATS data in {directory}. Expected the rMATS JC "
                    "tables (SE.MATS.JC.txt, A3SS.MATS.JC.txt, A5SS.MATS.JC.txt, "
                    "MXE.MATS.JC.txt, RI.MATS.JC.txt) or a standardized "
                    "AS_event_master.tsv produced by the upload step."
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
        raise ValueError(f"No AS events could be parsed from {directory}")

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
