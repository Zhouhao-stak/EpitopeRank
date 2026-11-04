"""Integration tests for the peptide prediction API."""

from __future__ import annotations

import csv

import pytest
from fastapi.testclient import TestClient

from epitoperank.api.app import create_app
from epitoperank.splicing.schema import CORE_EVENT_FIELDS


@pytest.fixture
def client(monkeypatch):
    # Allow temporary directories outside the runtime root for ingestion.
    monkeypatch.setenv("EPITOPERANK_INGEST_ALLOW_EXTERNAL", "1")
    return TestClient(create_app())


def _write_demo(directory):
    event = dict.fromkeys(CORE_EVENT_FIELDS, "")
    event.update(
        event_id="SE:1", gene_id="G1", gene_symbol="GENE1", event_type="SE",
        chromosome="chr1", strand="+", genomic_coordinates="chr1:10-20",
        coordinate_system="1-based-inclusive", source_tool="rMATS", FDR="0.01",
        delta_PSI="0.3", p_value="0.001",
    )
    with (directory / "AS_event_master.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CORE_EVENT_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerow(event)
    reference = "ATG" + "GCT" * 20
    altered = "ATG" + "GCT" * 6 + "TGG" * 8
    with (directory / "splice_orfs.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["event_id", "reference_cds", "altered_cds", "junction_nt"])
        writer.writerow(["SE:1", reference, altered, 21])
    return directory


def test_peptide_capabilities(client):
    response = client.get("/api/peptide/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["mhc_classes"] == [1, 2]
    assert "methods" in data and data["methods"]
    assert data["reference"]["alleles_class1"] > 0


def test_peptide_reference_search(client):
    response = client.get("/api/peptide/reference", params={"mhc_class": 1, "search": "A*02", "limit": 3})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= len(data["items"]) >= 1
    assert len(data["items"]) <= 3
    assert all("HLA-A*02" in item["allele"] for item in data["items"])
    assert "manifest" in data


def test_peptide_reference_rejects_bad_class(client):
    assert client.get("/api/peptide/reference", params={"mhc_class": 3}).status_code == 422


def test_peptide_predict_offline(client):
    response = client.post("/api/peptide/predict", json={
        "peptides": ["SLYNTVATL", "GILGFVFTL"],
        "alleles": ["HLA-A*02:01"],
        "mhc_class": "class1",
        "predictor": "none",
        "processing": False,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["candidate_count"] == 2
    assert data["prediction_count"] == 0
    assert data["predictions"] == []
    assert data["errors"] == []


@pytest.mark.parametrize("payload", [
    {"peptides": [], "alleles": ["HLA-A*02:01"]},
    {"peptides": ["TOO"], "alleles": ["HLA-A*02:01"]},
    {"peptides": ["SLYNTVATL"], "alleles": []},
    {"peptides": ["SLYNTVATL"], "alleles": ["HLA-A*02:99"], "mhc_class": "class9"},
])
def test_peptide_predict_rejects_invalid(client, payload):
    assert client.post("/api/peptide/predict", json=payload).status_code == 422


def test_peptide_run_and_download(client, tmp_path):
    _write_demo(tmp_path)
    response = client.post("/api/peptide/run", json={
        "input_dir": str(tmp_path),
        "cds_table": "splice_orfs.tsv",
        "alleles": ["HLA-A*02:01"],
        "mhc_class": "class1",
        "predictor": "none",
        "processing": False,
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["candidate_count"] > 0
    assert data["prediction_count"] == 0
    assert set(data["tiers"]) == {"D"}
    for name in ("splice_peptides.tsv", "mhc_predictions.tsv",
                 "ranked_candidates.tsv", "manifest.json", "summary.md"):
        assert name in data["files"], name
    file_response = client.get("/api/peptide/file",
                               params={"input_dir": str(tmp_path), "name": "manifest.json"})
    assert file_response.status_code == 200
    assert file_response.json()["options"]["predictor"] == "none"


def test_peptide_run_rejects_path_traversal(client, tmp_path):
    _write_demo(tmp_path)
    response = client.post("/api/peptide/run", json={
        "input_dir": str(tmp_path),
        "cds_table": "../escape.tsv",
        "alleles": ["HLA-A*02:01"],
        "predictor": "none",
    })
    assert response.status_code == 400


def test_peptide_file_rejects_unknown_name(client, tmp_path):
    (tmp_path / "peptide_results").mkdir()
    response = client.get("/api/peptide/file",
                          params={"input_dir": str(tmp_path), "name": "../app.py"})
    assert response.status_code == 400
