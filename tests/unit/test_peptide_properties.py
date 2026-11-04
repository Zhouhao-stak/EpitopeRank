"""Tests for offline peptide properties."""

from __future__ import annotations

import pytest

from splicegaip.peptide.properties import (
    RESIDUE_MASS,
    aliphatic_index,
    aromaticity,
    describe,
    describe_many,
    gravy,
    hydrophobic_fraction,
    isoelectric_point,
    ligand_anchors,
    molecular_weight,
    net_charge,
    shannon_entropy,
)
from splicegaip.peptide.sequences import SequenceError


def test_molecular_weight_of_known_nonamer() -> None:
    # Sum of average residue masses + water, rounded to 2 decimals.
    assert molecular_weight("SLYNTVATL") == 981.11
    assert molecular_weight("A") == pytest.approx(89.09, abs=0.01)
    assert molecular_weight("ACDEFGHIKLMNPQRSTVWY") == pytest.approx(
        sum(RESIDUE_MASS.values()) + 18.01524, abs=0.01
    )


def test_net_charge_and_pi_signs_for_basic_and_acidic_peptides() -> None:
    assert net_charge("RRRRRRRR") > 0
    assert net_charge("DDDDDDDD") < 0
    assert net_charge("RRRRRRRR") == pytest.approx(7.976, abs=0.001)
    assert net_charge("DDDDDDDD") == pytest.approx(-8.018, abs=0.001)

    assert isoelectric_point("RRRRRRRR") > 7.0
    assert isoelectric_point("DDDDDDDD") < 7.0
    assert isoelectric_point("RRRRRRRR") == pytest.approx(13.35, abs=0.01)
    assert isoelectric_point("DDDDDDDD") == pytest.approx(2.95, abs=0.01)


def test_gravy_sign_tracks_hydropathy() -> None:
    assert gravy("LLL") > 0
    assert gravy("KKK") < 0
    assert gravy("LLL") == pytest.approx(3.8, abs=0.001)
    assert gravy("KKK") == pytest.approx(-3.9, abs=0.001)
    assert gravy("SLYNTVATL") == pytest.approx(0.733, abs=0.001)


def test_aromaticity_counts_only_fwy() -> None:
    assert aromaticity("FWY") == 1.0
    assert aromaticity("FWYF") == 1.0
    assert aromaticity("AAAA") == 0.0
    assert aromaticity("SLYNTVATL") == pytest.approx(0.111, abs=0.001)


def test_aliphatic_index_of_pure_alanine() -> None:
    assert aliphatic_index("A") == 100.0
    assert aliphatic_index("A" * 8) == 100.0
    assert aliphatic_index("LLL") == pytest.approx(390.0, abs=0.01)


def test_hydrophobic_fraction_and_entropy() -> None:
    assert hydrophobic_fraction("AVILMFWY") == 1.0
    assert hydrophobic_fraction("DDDD") == 0.0
    assert shannon_entropy("AAAAAAAA") == pytest.approx(0.0, abs=1e-9)
    assert shannon_entropy("ACDEFGHIKL") == pytest.approx(3.3219, abs=0.01)


def test_describe_flags_low_complexity() -> None:
    assert describe("AAAAAAAA")["low_complexity"] is True
    assert describe("SLYNTVATL")["low_complexity"] is False


def test_anchor_fields_for_mhc_i_and_ii() -> None:
    first = describe("SLYNTVATL")
    assert first["p2"] == "L"
    assert first["p_omega"] == "L"
    assert first["mhc_class"] == 1

    second = describe("SLYNTVATLYCVHQR", mhc_class=2)
    assert second["p1"] == "S"
    assert second["mhc_class"] == 2
    assert "p2" not in second


def test_ligand_anchors_handles_short_peptide() -> None:
    assert ligand_anchors("A") == {"p2": "", "p_omega": "A"}


def test_describe_rejects_invalid_peptide() -> None:
    with pytest.raises(SequenceError):
        describe("SLYNTVA*L")


def test_describe_many_and_deterministic_values() -> None:
    rows = describe_many(["SLYNTVATL", "GILGFVFTL"])
    assert [row["peptide"] for row in rows] == ["SLYNTVATL", "GILGFVFTL"]
    assert rows[0]["molecular_weight_da"] == 981.11
    assert rows[1]["length"] == 9
