"""Self/normal-proteome filtering for candidate peptides.

The only question answered here is: *does this exact peptide already occur in
the supplied normal protein sequences?*  Absence from the supplied databases
is not proof that a peptide is tumour-specific — it only means the peptide was
not found in what was provided.  That limitation is written into every result
record and into the run manifest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from .sequences import SelfReference, file_sha256, normalize_peptide, read_fasta, unique

NOVELTY_NOTE = (
    "Novelty is limited to the supplied reference proteomes; absence is not "
    "proof that the peptide is tumour-specific."
)


@dataclass
class DatabaseScan:
    """Provenance for one reference FASTA used in the scan."""

    path: str
    sha256: str
    protein_count: int
    peptides_found: int

    def as_dict(self) -> dict[str, object]:
        """输出该参考 FASTA 的路径、校验和、蛋白数与命中肽段数。"""
        return {
            "path": self.path,
            "sha256": self.sha256,
            "protein_count": self.protein_count,
            "peptides_found": self.peptides_found,
        }


@dataclass
class SelfFilterResult:
    """Peptide novelty annotations plus per-database provenance."""

    hits: dict[str, list[str]] = field(default_factory=dict)
    databases: list[DatabaseScan] = field(default_factory=list)
    peptides: list[str] = field(default_factory=list)

    @property
    def novel(self) -> list[str]:
        """在所提供的全部参考蛋白组中均未命中，即“新颖”的肽段。"""
        return [peptide for peptide in self.peptides if not self.hits.get(peptide)]

    @property
    def shared(self) -> list[str]:
        """至少在一条参考蛋白中出现的肽段（即被判定为自身/正常来源）。"""
        return [peptide for peptide in self.peptides if self.hits.get(peptide)]

    def annotate(self, peptide: str) -> dict[str, object]:
        """生成单个肽段的自身命中注释字段，供候选行合并使用。"""
        matched = self.hits.get(peptide, [])
        return {
            "self_hit": bool(matched),
            "self_hit_proteins": ";".join(matched),
            "self_hit_count": len(matched),
            "novelty_status": "not_in_supplied_proteome" if not matched else "present_in_supplied_proteome",
        }

    def as_dict(self) -> dict[str, object]:
        """汇总输入数、新颖/共享计数与各数据库溯源信息（含新颖性局限说明）。"""
        return {
            "input_count": len(self.peptides),
            "novel_count": len(self.novel),
            "shared_count": len(self.shared),
            "databases": [item.as_dict() for item in self.databases],
            "limitations": [NOVELTY_NOTE],
        }


def scan_proteomes(peptides: Iterable[str], fasta_paths: Sequence[str | Path]) -> SelfFilterResult:
    """Scan every FASTA and record which peptides occur exactly in each one."""
    peptide_list = unique(normalize_peptide(item) for item in peptides)
    result = SelfFilterResult(peptides=peptide_list)
    # Initialise every peptide so "no hit" is an explicit empty list.
    for peptide in peptide_list:
        result.hits.setdefault(peptide, [])
    for raw_path in fasta_paths:
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"reference proteome not found: {path}")
        proteins = list(read_fasta(path, kind="protein"))
        reference = SelfReference(proteins)
        partial = reference.hits(peptide_list)
        found = 0
        for peptide in peptide_list:
            hits = partial.get(peptide, [])
            if hits:
                found += 1
                result.hits.setdefault(peptide, [])
                for header in hits:
                    label = f"{path.name}:{header}"
                    if label not in result.hits[peptide]:
                        result.hits[peptide].append(label)
        result.databases.append(
            DatabaseScan(path=str(path), sha256=file_sha256(path),
                         protein_count=reference.protein_count, peptides_found=found)
        )
    return result


def annotate_candidates(candidates: Sequence[dict], fasta_paths: Sequence[str | Path]) -> tuple[list[dict], SelfFilterResult]:
    """Return candidate rows annotated with novelty, plus the scan summary."""
    scan = scan_proteomes([str(item["peptide"]) for item in candidates], fasta_paths)
    annotated = [{**item, **scan.annotate(str(item["peptide"]))} for item in candidates]
    return annotated, scan
