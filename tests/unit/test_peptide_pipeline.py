"""Tests for peptide ranking, novelty scanning, table loading and the pipeline."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from splicegaip.peptide.filters import annotate_candidates, scan_proteomes
from splicegaip.peptide.pipeline import (
    PeptideOptions,
    _client,
    aggregate,
    dedupe_predictions,
    load_peptide_table,
    run,
)
from splicegaip.peptide.scoring import (
    component_scores,
    composite,
    describe,
    evidence_tier,
    rank,
)
from splicegaip.peptide.sequences import file_sha256
from splicegaip.splicing.schema import CORE_EVENT_FIELDS


def test_client_keeps_default_cache_and_reads_deployment_env(tmp_path, monkeypatch) -> None:
    """Explicit ``cache_dir=None`` used to disable the cache for every API call."""
    monkeypatch.setenv("SPLICEGAIP_PEPTIDE_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("SPLICEGAIP_PEPTIDE_TIMEOUT", "120")
    client = _client(PeptideOptions())
    assert client.cache_dir == tmp_path / "cache"
    assert client.timeout == 120.0
    assert client.cache_read is True

    explicit = _client(PeptideOptions(cache_dir=str(tmp_path / "other")))
    assert explicit.cache_dir == tmp_path / "other"


# ----------------------------------------------------------------------
# Scoring / ranking
# ----------------------------------------------------------------------
def test_rank_orders_low_percentile_first_and_assigns_tiers() -> None:
    rows = [
        {
            "peptide": "LOW", "percentile_rank": 0.04, "processing_total_score": 1.0,
            "expression": 10.0, "delta_psi": 0.4, "self_hit": False,
        },
        {
            "peptide": "HIGH", "percentile_rank": 20.0, "processing_total_score": 1.0,
            "expression": 10.0, "delta_psi": 0.4, "self_hit": False,
        },
        {"peptide": "TIER_B", "percentile_rank": 0.5, "self_hit": False},
        {"peptide": "TIER_C", "percentile_rank": 0.5},
        {"peptide": "TIER_D"},
        {
            "peptide": "NO_NOVELTY", "percentile_rank": 0.5,
            "processing_total_score": 1.0, "expression": 10.0, "self_hit": None,
        },
    ]
    ranked = rank(rows)
    by_peptide = {row["peptide"]: row for row in ranked}

    assert by_peptide["LOW"]["rank"] == 1
    assert by_peptide["LOW"]["rank"] < by_peptide["HIGH"]["rank"]
    assert by_peptide["LOW"]["evidence_tier"] == "A"
    assert by_peptide["TIER_B"]["evidence_tier"] == "B"
    assert by_peptide["TIER_C"]["evidence_tier"] == "C"
    assert by_peptide["TIER_D"]["evidence_tier"] == "D"
    # Processing + expression do not upgrade a missing-novelty row past C.
    assert by_peptide["NO_NOVELTY"]["evidence_tier"] == "C"
    assert "novelty" not in by_peptide["NO_NOVELTY"]["components"]
    assert "novelty" in by_peptide["NO_NOVELTY"]["components_missing"]
    assert by_peptide["TIER_D"]["composite_score"] == 0.0
    assert set(by_peptide["LOW"]["components_used"]) == {
        "binding", "processing", "expression", "effect", "novelty",
    }


def test_component_scores_ignore_missing_self_hit_and_handle_bounds() -> None:
    assert "novelty" not in component_scores({"peptide": "X", "percentile_rank": 1.0})
    assert component_scores({"self_hit": True})["novelty"] == 0.0
    assert component_scores({"self_hit": False})["novelty"] == 1.0
    # Expression is capped at 1 and negatives are ignored.
    assert component_scores({"expression": 1e6})["expression"] == 1.0
    assert "expression" not in component_scores({"expression": -5})
    assert "binding" not in component_scores({"percentile_rank": None})
    assert evidence_tier(component_scores({"percentile_rank": 0.5})) == "C"
    assert evidence_tier({}) == "D"
    assert describe()["weights"]["binding"] == pytest.approx(0.40)


def test_composite_renormalises_over_available_components() -> None:
    result = composite({"peptide": "X", "percentile_rank": 0.5})
    assert 0.0 <= result["composite_score"] <= 1.0
    assert result["components_used"] == ["binding"]
    assert result["evidence_tier"] == "C"


# ----------------------------------------------------------------------
# Novelty / self-proteome filter
# ----------------------------------------------------------------------
def test_scan_proteomes_finds_present_and_absent_peptides(tmp_path) -> None:
    fasta = tmp_path / "normal_proteome.fasta"
    fasta.write_text(
        ">sp|P1|TEST1\nMAAAASLYNTVATLAAA\n"
        ">sp|P2|TEST2\nMGGGGGGGGGG\n",
        encoding="utf-8",
    )

    scan = scan_proteomes(["SLYNTVATL", "AAAAAAAA"], [fasta])

    assert scan.peptides == ["SLYNTVATL", "AAAAAAAA"]
    assert scan.shared == ["SLYNTVATL"]
    assert scan.novel == ["AAAAAAAA"]
    assert scan.hits["SLYNTVATL"] == ["normal_proteome.fasta:sp|P1|TEST1"]
    # Every input peptide has an explicit (possibly empty) hit list.
    assert scan.hits["AAAAAAAA"] == []

    database = scan.databases[0]
    assert database.protein_count == 2
    assert database.peptides_found == 1
    assert database.sha256 == file_sha256(fasta)

    summary = scan.as_dict()
    assert summary["input_count"] == 2
    assert summary["novel_count"] == 1
    assert summary["shared_count"] == 1
    assert summary["limitations"]

    annotation = scan.annotate("SLYNTVATL")
    assert annotation["self_hit"] is True
    assert annotation["self_hit_count"] == 1
    assert annotation["novelty_status"] == "present_in_supplied_proteome"
    assert scan.annotate("AAAAAAAA")["novelty_status"] == "not_in_supplied_proteome"


def test_annotate_candidates_merges_novelty(tmp_path) -> None:
    fasta = tmp_path / "self.fasta"
    fasta.write_text(">p1\nMAAAASLYNTVATLAAA\n", encoding="utf-8")
    annotated, scan = annotate_candidates(
        [{"peptide": "SLYNTVATL", "event_id": "SE:1"},
         {"peptide": "AAAAAAAA", "event_id": "SE:2"}],
        [fasta],
    )
    assert annotated[0]["self_hit"] is True
    assert annotated[1]["self_hit"] is False
    assert annotated[0]["event_id"] == "SE:1"
    assert scan.shared == ["SLYNTVATL"]


def test_scan_proteomes_rejects_missing_file(tmp_path) -> None:
    with pytest.raises(ValueError, match="not found"):
        scan_proteomes(["SLYNTVATL"], [tmp_path / "missing.fasta"])


# ----------------------------------------------------------------------
# Peptide table input
# ----------------------------------------------------------------------
def test_load_peptide_table_normalises_case_and_keeps_metadata(tmp_path) -> None:
    table = tmp_path / "peptides.tsv"
    table.write_text(
        "peptide\tsample\tvalue\n"
        " slyntvatl \tS1\t3\n"
        "GILGFVFTL\tS2\t4\n",
        encoding="utf-8",
    )

    rows = load_peptide_table(table)

    assert [row["peptide"] for row in rows] == ["SLYNTVATL", "GILGFVFTL"]
    assert rows[0]["sample"] == "S1"
    assert rows[0]["value"] == "3"


def test_load_peptide_table_requires_peptide_column(tmp_path) -> None:
    table = tmp_path / "bad.tsv"
    table.write_text("sequence\tvalue\nSLYNTVATL\t1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="peptide"):
        load_peptide_table(table)


def test_load_peptide_table_reads_fasta(tmp_path) -> None:
    fasta = tmp_path / "peptides.fasta"
    fasta.write_text(">candidate_1\nSLYNTVATL\n", encoding="utf-8")
    rows = load_peptide_table(fasta)
    assert rows == [{"peptide": "SLYNTVATL", "record_id": "candidate_1"}]


# ----------------------------------------------------------------------
# End-to-end offline pipeline
# ----------------------------------------------------------------------
def _write_event_table(directory: Path) -> None:
    event = dict.fromkeys(CORE_EVENT_FIELDS, "")
    event.update(
        event_id="SE:1", gene_id="G1", gene_symbol="GENE1", event_type="SE",
        chromosome="chr1", strand="+", genomic_coordinates="chr1:10-20",
        coordinate_system="1-based-inclusive", source_tool="rMATS",
        mean_PSI_group1="0.8", mean_PSI_group2="0.4", delta_PSI="0.4",
        p_value="0.001", FDR="0.01",
    )
    with (directory / "AS_event_master.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CORE_EVENT_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerow(event)


def _write_cds_table(directory: Path) -> Path:
    # Reference: M + 20 alanines. Altered: M + 6 alanines + 8 tryptophans.
    reference = "ATG" + "GCT" * 20
    altered = "ATG" + "GCT" * 6 + "TGG" * 8
    path = directory / "splice_orfs.tsv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow([
            "event_id", "reference_cds", "altered_cds", "junction_nt",
            "orf_source", "frame_status", "premature_stop",
        ])
        writer.writerow(["SE:1", reference, altered, "21", "test_fixture", "in_frame", "no"])
    return path


def test_pipeline_run_end_to_end_without_prediction(tmp_path) -> None:
    _write_event_table(tmp_path)
    cds_table = _write_cds_table(tmp_path)
    output = tmp_path / "out"

    options = PeptideOptions(alleles=[], mhc_class="class1", predictor="none")
    result = run(output_dir=output, input_dir=tmp_path, cds_table=cds_table,
                 options=options)

    assert result["candidate_count"] > 0
    assert result["prediction_count"] == 0
    assert result["ranked_count"] == result["candidate_count"]
    assert result["tiers"] == {"D": result["ranked_count"]}

    for name in ("splice_peptides.tsv", "ranked_candidates.tsv",
                 "manifest.json", "summary.md", "mhc_predictions.tsv"):
        assert (output / name).is_file(), name

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["options"]["predictor"] == "none"
    assert manifest["options"]["mhc_class"] == "class1"
    assert manifest["options"]["alleles"] == []
    assert manifest["candidate_count"] == result["candidate_count"]
    assert manifest["inputs"]["mode"] == "cds_table"
    assert manifest["inputs"]["cds_table_sha256"] == file_sha256(cds_table)
    assert manifest["limitations"]

    with (output / "ranked_candidates.tsv").open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle, delimiter="\t"))
    assert "altered_protein" not in header
    assert "class2_context" not in header
    assert header[0] == "rank"
    assert "evidence_tier" in header
    assert "composite_score" in header


def test_dedupe_predictions_keeps_best_binding_and_processing() -> None:
    rows = [
        {"peptide": "AAAACCCC", "allele": "A", "method": "netmhcpan_el", "percentile_rank": 2.0},
        {"peptide": "AAAACCCC", "allele": "A", "method": "netmhcpan_el", "percentile_rank": 0.5},
        {"peptide": "AAAACCCC", "allele": "A", "method": "processing", "total_score": -2.0},
        {"peptide": "AAAACCCC", "allele": "A", "method": "processing", "total_score": 1.5},
    ]
    deduped = dedupe_predictions(rows)
    by_method = {row["method"]: row for row in deduped}
    assert len(deduped) == 2
    assert by_method["netmhcpan_el"]["percentile_rank"] == 0.5
    assert by_method["processing"]["total_score"] == 1.5


def test_aggregate_falls_back_to_class2_and_picks_best_processing() -> None:
    predictions = [
        {"peptide": "AAAACCCC", "allele": "A", "method": "mhci", "mhc_class": 1,
         "percentile_rank": 1.2, "method_label": "class I"},
        {"peptide": "AAAACCCC", "allele": "DR1", "method": "mhcii", "mhc_class": 2,
         "percentile_rank": 0.2, "method_label": "class II"},
        {"peptide": "AAAACCCC", "allele": "A", "method": "processing", "total_score": 1.5},
    ]
    row = aggregate([{"peptide": "AAAACCCC", "length": 8}], predictions)[0]
    assert row["percentile_rank"] == 1.2
    assert row["mhc_class2_percentile"] == 0.2
    assert row["processing_total_score"] == 1.5

    class2_only = aggregate([{"peptide": "AAAACCCC", "length": 8}], predictions[1:2])[0]
    assert class2_only["percentile_rank"] == 0.2
    assert class2_only["best_allele"] == "DR1"


def test_peptide_table_mode_accepts_mhc_ii_lengths(tmp_path) -> None:
    table = tmp_path / "peptides.tsv"
    table.write_text("peptide\nGSDTLLGDGSLYNTV\n", encoding="utf-8")
    result = run(output_dir=tmp_path / "out", peptides=table,
                 options=PeptideOptions(alleles=[], mhc_class="class2", predictor="none"))
    assert result["candidate_count"] == 1
    assert result["manifest"]["skipped_count"] == 0


def test_max_predictions_is_enforced(tmp_path) -> None:
    options = PeptideOptions(alleles=["HLA-A*02:01"], predictor="iedb", max_predictions=1)
    with pytest.raises(ValueError, match="max_predictions"):
        run(output_dir=tmp_path / "out",
            peptides=["SLYNTVATL", "GILGFVFTL"], options=options)
