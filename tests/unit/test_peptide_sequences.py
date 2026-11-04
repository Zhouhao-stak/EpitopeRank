"""Tests for peptide sequence primitives (normalisation, FASTA, self-scan)."""

from __future__ import annotations

import pytest

from splicegaip.peptide.sequences import (
    AA_ALPHABET,
    SequenceError,
    SelfReference,
    normalize_peptide,
    peptide_digest,
    read_fasta,
    unique,
    validate_peptide,
)


def test_normalize_peptide_strips_whitespace_and_uppercases() -> None:
    assert normalize_peptide("  sl ynt vatl \t") == "SLYNTVATL"
    assert normalize_peptide("acdefghik") == "ACDEFGHIK"


def test_normalize_peptide_rejects_invalid_residue() -> None:
    with pytest.raises(SequenceError, match="unsupported residue"):
        normalize_peptide("SLYNTVAZL")
    # Ambiguous IUPAC codes are accepted only on request.
    assert normalize_peptide("SLYNTVAXL", allow_ambiguous=True) == "SLYNTVAXL"
    # Every standard residue round-trips.
    assert normalize_peptide("".join(sorted(AA_ALPHABET))) == "".join(sorted(AA_ALPHABET))


def test_normalize_peptide_rejects_empty_and_non_string() -> None:
    for value in ("", "   ", "\t\n"):
        with pytest.raises(SequenceError, match="empty"):
            normalize_peptide(value)
    with pytest.raises(SequenceError, match="string"):
        normalize_peptide(None)  # type: ignore[arg-type]


def test_validate_peptide_accepts_mhc_i_lengths_only() -> None:
    for length in (8, 9, 10, 11):
        peptide = "A" * length
        assert validate_peptide(peptide) == peptide
    with pytest.raises(SequenceError, match="length 7"):
        validate_peptide("A" * 7)
    with pytest.raises(SequenceError, match="length 12"):
        validate_peptide("A" * 12)
    # Custom length sets are honoured.
    assert validate_peptide("A" * 15, lengths=(15,)) == "A" * 15


def test_unique_preserves_first_seen_order() -> None:
    assert unique(["B", "A", "B", "C", "A"]) == ["B", "A", "C"]


def test_peptide_digest_is_stable_and_short() -> None:
    assert peptide_digest("SLYNTVATL") == peptide_digest("SLYNTVATL")
    assert len(peptide_digest("SLYNTVATL")) == 16
    assert peptide_digest("SLYNTVATL") != peptide_digest("GILGFVFTL")


def test_read_fasta_protein_strips_stop_and_accepts_ambiguous(tmp_path) -> None:
    path = tmp_path / "proteins.fasta"
    path.write_text("; a comment\n>sp|P1|TEST\nACD*EF\n>sp|P2|TEST\nMXBZU\n", encoding="utf-8")
    records = list(read_fasta(path))
    assert records == [("sp|P1|TEST", "ACDEF"), ("sp|P2|TEST", "MXBZU")]


def test_read_fasta_peptide_mode_rejects_ambiguous(tmp_path) -> None:
    path = tmp_path / "peptides.fasta"
    path.write_text(">p1\nSLYNTVATL\n", encoding="utf-8")
    assert list(read_fasta(path, kind="peptide")) == [("p1", "SLYNTVATL")]
    path.write_text(">p1\nACDX\n", encoding="utf-8")
    with pytest.raises(SequenceError, match="non-standard residues"):
        list(read_fasta(path, kind="peptide"))


def test_read_fasta_rejects_duplicate_header(tmp_path) -> None:
    path = tmp_path / "dup.fasta"
    path.write_text(">p1\nACDE\n>p1\nFGHI\n", encoding="utf-8")
    with pytest.raises(SequenceError, match="duplicate FASTA header"):
        list(read_fasta(path))


def test_read_fasta_rejects_empty_record(tmp_path) -> None:
    path = tmp_path / "empty.fasta"
    path.write_text(">p1\n>p2\nACDE\n", encoding="utf-8")
    with pytest.raises(SequenceError, match="empty FASTA sequence"):
        list(read_fasta(path))


def test_read_fasta_rejects_sequence_before_header(tmp_path) -> None:
    path = tmp_path / "bad.fasta"
    path.write_text("ACDE\n>p1\nFGHI\n", encoding="utf-8")
    with pytest.raises(SequenceError, match="before first FASTA header"):
        list(read_fasta(path))


def test_read_fasta_rejects_file_without_records(tmp_path) -> None:
    path = tmp_path / "none.fasta"
    path.write_text("", encoding="utf-8")
    with pytest.raises(SequenceError, match="no FASTA records"):
        list(read_fasta(path))


def test_self_reference_maps_hits_to_the_right_header() -> None:
    reference = SelfReference([
        ("p1", "GGGGGGGGGG"),
        ("p2", "MAAAASLYNTVATLAAA"),
    ])
    hits = reference.hits(["SLYNTVATL", "AAAAAAAA"])
    assert hits["SLYNTVATL"] == ["p2"]
    assert hits["AAAAAAAA"] == []
    assert reference.contains("SLYNTVATL") is True
    assert reference.contains("GGGGGGGG") is True
    assert reference.contains("WWWWWWWW") is False


def test_self_reference_does_not_match_across_protein_boundary() -> None:
    reference = SelfReference([("p1", "AAA"), ("p2", "CCC")])
    # 'AAC' would exist if the separator were absent; '*' prevents it.
    assert reference.hits(["AAC"]) == {"AAC": []}


def test_self_reference_caps_hits_per_peptide() -> None:
    proteins = [(f"p{index}", "M" + "A" * 8 + "M") for index in range(30)]
    reference = SelfReference(proteins)
    hits = reference.hits(["AAAAAAAA"])["AAAAAAAA"]
    assert len(hits) == SelfReference.MAX_HITS_PER_PEPTIDE == 25
    assert hits[0] == "p0"
    assert len(set(hits)) == 25


def test_self_reference_from_fasta(tmp_path) -> None:
    path = tmp_path / "ref.fasta"
    path.write_text(">p1\nMAAAASLYNTVATLAAA\n", encoding="utf-8")
    reference = SelfReference.from_fasta(path)
    assert reference.protein_count == 1
    assert reference.hits(["SLYNTVATL"]) == {"SLYNTVATL": ["p1"]}


def test_self_reference_rejects_empty_proteome() -> None:
    with pytest.raises(SequenceError, match="empty"):
        SelfReference([])
