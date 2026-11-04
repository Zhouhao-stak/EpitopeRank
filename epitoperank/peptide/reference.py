"""Bundled, provenance-tracked peptide reference tables.

Two kinds of files live in ``epitoperank/peptide/reference``:

* ``hla_class1_alleles.tsv`` / ``hla_class2_alleles.tsv`` — the allele names
  the IEDB lists for its default methods, captured at build time;
* ``known_epitopes.tsv`` — a small, real IEDB assay extract used for demos,
  regression tests and the "has this exact peptide been assayed before?"
  cross-check.

Every file is accompanied by ``manifest.json`` (retrieval date, source URL,
sha256).  ``scripts/fetch_peptide_reference.py`` regenerates the set.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from .hla import CLASS_I_PANEL, CLASS_II_PANEL, describe

REFERENCE_DIRNAME = "reference"


class ReferenceError(RuntimeError):
    """Raised when a bundled table is present but unreadable."""


def reference_dir() -> Path:
    return Path(__file__).resolve().with_name(REFERENCE_DIRNAME)


def manifest() -> dict[str, object]:
    path = reference_dir() / "manifest.json"
    if not path.is_file():
        return {"status": "missing", "files": {}, "note": "run scripts/fetch_peptide_reference.py"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ReferenceError(f"cannot read reference manifest: {error}") from error


def _read(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return [{key: (value or "").strip() for key, value in row.items()}
                    for row in csv.DictReader(handle, delimiter="\t")]
    except (OSError, csv.Error) as error:
        raise ReferenceError(f"cannot read {path.name}: {error}") from error


def load_alleles(mhc_class: int) -> list[dict[str, object]]:
    """Return bundled alleles for one MHC class, with locus/supertype filled in.

    Falls back to the curated convenience panel when the fetched table is not
    present, so a source checkout still works offline.
    """
    name = "hla_class1_alleles.tsv" if mhc_class == 1 else "hla_class2_alleles.tsv"
    rows = _read(reference_dir() / name)
    if not rows:
        fallback = CLASS_I_PANEL if mhc_class == 1 else CLASS_II_PANEL
        rows = [{"allele": allele, "source": "curated_panel"} for allele in fallback]
    result: list[dict[str, object]] = []
    for row in rows:
        allele = row.get("allele") or ""
        if not allele:
            continue
        try:
            info = describe(allele)
        except ValueError:
            continue
        result.append({
            "allele": info.name,
            "locus": info.locus,
            "supertype": info.supertype,
            "mhc_class": info.mhc_class,
            "source": row.get("source") or "iedb",
        })
    return result


def load_known_epitopes() -> list[dict[str, str]]:
    """Return the bundled IEDB assay extract (empty list when not fetched)."""
    return _read(reference_dir() / "known_epitopes.tsv")


def known_epitope_index() -> dict[str, list[dict[str, str]]]:
    index: dict[str, list[dict[str, str]]] = {}
    for row in load_known_epitopes():
        peptide = (row.get("peptide") or "").upper()
        if peptide:
            index.setdefault(peptide, []).append(row)
    return index


@dataclass(frozen=True)
class ReferenceSummary:
    alleles_class1: int
    alleles_class2: int
    known_epitopes: int
    fetched_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "alleles_class1": self.alleles_class1,
            "alleles_class2": self.alleles_class2,
            "known_epitopes": self.known_epitopes,
            "fetched_at": self.fetched_at,
        }


def summary() -> ReferenceSummary:
    data = manifest()
    return ReferenceSummary(
        alleles_class1=len(load_alleles(1)),
        alleles_class2=len(load_alleles(2)),
        known_epitopes=len(load_known_epitopes()),
        fetched_at=str(data.get("retrieved_at") or "bundled-curated"),
    )
