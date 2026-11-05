"""Offline physicochemical properties of candidate peptides.

These numbers are *descriptive*, not predictive of immunogenicity.  They are
computed locally so every report can show a reproducible feature set even
when the network (and therefore IEDB) is unavailable.

References
----------
* Kyte & Doolittle (1982) hydropathy scale.
* Ikai (1980) aliphatic index.
* Lobry & Gautier (1994) aromaticity.
* EMBOSS ``iep`` pKa set (Bjellqvist-style terminal values).
"""

from __future__ import annotations

from math import log2
from statistics import fmean

from .sequences import normalize_peptide

#: Average residue masses in Da (IUPAC/ExPASy).
RESIDUE_MASS: dict[str, float] = {
    "A": 71.0788, "R": 156.1875, "N": 114.1038, "D": 115.0886,
    "C": 103.1388, "E": 129.1155, "Q": 128.1307, "G": 57.0519,
    "H": 137.1411, "I": 113.1594, "L": 113.1594, "K": 128.1741,
    "M": 131.1926, "F": 147.1766, "P": 97.1167, "S": 87.0782,
    "T": 101.1051, "W": 186.2132, "Y": 163.1760, "V": 99.1326,
}
WATER_MASS = 18.01524

#: Kyte-Doolittle hydropathy.
HYDROPATHY: dict[str, float] = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5,
    "Q": -3.5, "E": -3.5, "G": -0.4, "H": -3.2, "I": 4.5,
    "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8, "P": -1.6,
    "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}

#: Side-chain pKa values plus the terminal groups.
PKA: dict[str, float] = {
    "Cterm": 3.6, "Nterm": 8.6, "D": 3.9, "E": 4.1,
    "C": 8.5, "Y": 10.1, "H": 6.5, "K": 10.8, "R": 12.5,
}
_POSITIVE = ("K", "R", "H")
_NEGATIVE = ("D", "E", "C", "Y")
_HYDROPHOBIC = frozenset("AVILMFWY")


def molecular_weight(peptide: str) -> float:
    """Average (not monoisotopic) molecular mass in Da, including water."""
    return round(sum(RESIDUE_MASS[aa] for aa in peptide) + WATER_MASS, 2)


def net_charge(peptide: str, ph: float = 7.0) -> float:
    """Net charge at ``ph`` using the Henderson-Hasselbalch equation."""
    charge = 0.0
    if peptide:
        charge += 1.0 / (1.0 + 10 ** (ph - PKA["Nterm"]))
        charge -= 1.0 / (1.0 + 10 ** (PKA["Cterm"] - ph))
    for aa in peptide:
        if aa in _POSITIVE:
            charge += 1.0 / (1.0 + 10 ** (ph - PKA[aa]))
        elif aa in _NEGATIVE:
            charge -= 1.0 / (1.0 + 10 ** (PKA[aa] - ph))
    return round(charge, 3)


def isoelectric_point(peptide: str, *, iterations: int = 64) -> float:
    """Bisection root of the net-charge curve on pH 0-14."""
    low, high = 0.0, 14.0
    for _ in range(iterations):
        middle = (low + high) / 2
        if net_charge_raw(peptide, middle) > 0:
            low = middle
        else:
            high = middle
    return round((low + high) / 2, 2)


def net_charge_raw(peptide: str, ph: float) -> float:
    """Unrounded net charge, used by :func:`isoelectric_point`."""
    charge = 1.0 / (1.0 + 10 ** (ph - PKA["Nterm"]))
    charge -= 1.0 / (1.0 + 10 ** (PKA["Cterm"] - ph))
    for aa in peptide:
        if aa in _POSITIVE:
            charge += 1.0 / (1.0 + 10 ** (ph - PKA[aa]))
        elif aa in _NEGATIVE:
            charge -= 1.0 / (1.0 + 10 ** (PKA[aa] - ph))
    return charge


def gravy(peptide: str) -> float:
    """Grand average of hydropathy (Kyte-Doolittle)."""
    if not peptide:
        return 0.0
    return round(fmean(HYDROPATHY[aa] for aa in peptide), 3)


def aromaticity(peptide: str) -> float:
    """Fraction of F/W/Y residues."""
    if not peptide:
        return 0.0
    return round(sum(aa in "FWY" for aa in peptide) / len(peptide), 3)


def aliphatic_index(peptide: str) -> float:
    """Ikai aliphatic index (mole-percent scaled)."""
    if not peptide:
        return 0.0
    counts = {aa: peptide.count(aa) / len(peptide) * 100 for aa in "AVIL"}
    return round(counts["A"] + 2.9 * counts["V"] + 3.9 * (counts["I"] + counts["L"]), 2)


def hydrophobic_fraction(peptide: str) -> float:
    """Fraction of strongly hydrophobic residues (A/V/I/L/M/F/W/Y)."""
    if not peptide:
        return 0.0
    return round(sum(aa in _HYDROPHOBIC for aa in peptide) / len(peptide), 3)


def shannon_entropy(peptide: str) -> float:
    """Per-position Shannon entropy in bits; low values flag low complexity."""
    if not peptide:
        return 0.0
    counts: dict[str, int] = {}
    for aa in peptide:
        counts[aa] = counts.get(aa, 0) + 1
    total = len(peptide)
    return round(-sum(count / total * log2(count / total) for count in counts.values()), 3)


def ligand_anchors(peptide: str, *, mhc_class: int = 1) -> dict[str, str]:
    """Report the residues usually called anchor positions.

    For MHC-I these are P2 and the C-terminal position (PΩ); for MHC-II the
    P1 position of the 9-mer core is the conventional anchor.  This is a
    descriptive feature, not a binding prediction.
    """
    if mhc_class == 1:
        return {"p2": peptide[1] if len(peptide) > 1 else "",
                "p_omega": peptide[-1] if peptide else ""}
    return {"p1": peptide[0] if peptide else ""}


def describe(peptide: str, *, mhc_class: int = 1) -> dict[str, object]:
    """All local features for one peptide."""
    peptide = normalize_peptide(peptide)
    return {
        "peptide": peptide,
        "length": len(peptide),
        "mhc_class": int(mhc_class),
        "molecular_weight_da": molecular_weight(peptide),
        "isoelectric_point": isoelectric_point(peptide),
        "net_charge_ph7": net_charge(peptide, 7.0),
        "gravy": gravy(peptide),
        "aromaticity": aromaticity(peptide),
        "aliphatic_index": aliphatic_index(peptide),
        "hydrophobic_fraction": hydrophobic_fraction(peptide),
        "shannon_entropy": shannon_entropy(peptide),
        "low_complexity": shannon_entropy(peptide) < 2.5,
        **ligand_anchors(peptide, mhc_class=mhc_class),
    }


def describe_many(peptides: list[str], *, mhc_class: int = 1) -> list[dict[str, object]]:
    """批量计算多个肽段的全套本地理化特征，纯本地计算、不联网。"""
    return [describe(peptide, mhc_class=mhc_class) for peptide in peptides]
