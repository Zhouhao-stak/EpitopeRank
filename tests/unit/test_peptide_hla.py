"""Tests for HLA allele parsing, validation and panels."""

from __future__ import annotations

import pytest

from epitoperank.peptide.hla import (
    CLASS_I_PANEL,
    CLASS_II_PANEL,
    HlaError,
    describe,
    locus,
    mhc_class,
    normalize_allele,
    panel,
    parse_panel,
    split_by_class,
)


def test_normalize_allele_accepts_common_shorthands() -> None:
    assert normalize_allele("a*02:01") == "HLA-A*02:01"
    assert normalize_allele("HLA-A*02:1") == "HLA-A*02:01"
    assert normalize_allele("DRB1*15:01") == "HLA-DRB1*15:01"
    assert normalize_allele("HLA-DPA1*01:03/DPB1*04:01") == "HLA-DPA1*01:03/DPB1*04:01"
    assert normalize_allele(" dpa1*01:03/dpb1*04:01 ") == "HLA-DPA1*01:03/DPB1*04:01"


def test_normalize_allele_rejects_incomplete_or_garbage() -> None:
    with pytest.raises(HlaError):
        normalize_allele("HLA-A*02")  # one field only
    with pytest.raises(HlaError):
        normalize_allele("not-an-allele")  # no '*'
    with pytest.raises(HlaError):
        normalize_allele("HLA-Z*01:01")  # unsupported locus
    with pytest.raises(HlaError):
        normalize_allele("")
    with pytest.raises(HlaError):
        normalize_allele(None)  # type: ignore[arg-type]


def test_normalize_allele_non_strict_returns_candidate() -> None:
    # strict=False is used by user-facing form validation.
    assert normalize_allele("HLA-Z*01:01", strict=False) == "HLA-Z*01:01"


def test_mhc_class_and_locus() -> None:
    assert mhc_class("HLA-A*02:01") == 1
    assert mhc_class("HLA-B*07:02") == 1
    assert mhc_class("HLA-DRB1*15:01") == 2
    assert mhc_class("HLA-DPA1*01:03/DPB1*04:01") == 2
    assert locus("HLA-A*02:01") == "A"
    assert locus("HLA-DRB1*15:01") == "DRB1"
    assert locus("HLA-DPA1*01:03/DPB1*04:01") == "DPA1"


def test_describe_reports_supertype() -> None:
    allele = describe("HLA-A*02:01")
    assert allele.name == "HLA-A*02:01"
    assert allele.locus == "A"
    assert allele.mhc_class == 1
    assert allele.supertype == "A02"
    assert describe("HLA-A*02:03").supertype == "A02"
    # Unknown alleles are not guessed.
    assert describe("HLA-A*66:01").supertype is None
    assert describe("HLA-A*02:01").as_dict()["allele"] == "HLA-A*02:01"


def test_parse_panel_deduplicates_and_validates() -> None:
    alleles = parse_panel(["HLA-A*02:01", "A*02:01", "HLA-A*02:01"])
    assert [item.name for item in alleles] == ["HLA-A*02:01"]

    with pytest.raises(HlaError, match="separately"):
        parse_panel(["HLA-A*02:01", "HLA-DRB1*15:01"])

    mixed = parse_panel(["HLA-A*02:01", "HLA-DRB1*15:01"], allow_mixed_classes=True)
    assert [item.mhc_class for item in mixed] == [1, 2]

    # A comma/semicolon separated string is accepted as convenience.
    assert len(parse_panel("HLA-A*02:01, HLA-B*07:02")) == 2

    with pytest.raises(HlaError):
        parse_panel([])
    with pytest.raises(HlaError):
        parse_panel({"not": "a list"})  # type: ignore[arg-type]


def test_split_by_class() -> None:
    grouped = split_by_class(parse_panel(
        ["HLA-A*02:01", "HLA-B*07:02", "HLA-DRB1*15:01"], allow_mixed_classes=True
    ))
    assert [item.name for item in grouped[1]] == ["HLA-A*02:01", "HLA-B*07:02"]
    assert [item.name for item in grouped[2]] == ["HLA-DRB1*15:01"]


def test_panels() -> None:
    class1 = panel("class1_common")
    assert class1
    assert class1 == list(CLASS_I_PANEL)
    assert all(name.startswith("HLA-") for name in class1)

    class2 = panel("class2-common")
    assert class2 == list(CLASS_II_PANEL)

    with pytest.raises(HlaError, match="unknown HLA panel"):
        panel("class3_rare")


def test_hla_error_is_value_error() -> None:
    assert issubclass(HlaError, ValueError)
