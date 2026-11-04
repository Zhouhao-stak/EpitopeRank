"""Column mapping: wild headers must be guessed, confirmed, and remembered."""

from __future__ import annotations

import csv

import pytest
from fastapi.testclient import TestClient

from splicegaip.api.app import create_app
from splicegaip.splicing.schema import CORE_EVENT_FIELDS

REFERENCE = "ATG" + "GCT" * 20
ALTERED = "ATG" + "GCT" * 6 + "TGG" * 8


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SPLICEGAIP_INGEST_ALLOW_EXTERNAL", "1")
    return TestClient(create_app())


def _project(monkeypatch, directory):
    import splicegaip.api.app as api_module

    monkeypatch.setattr(api_module, "project_status",
                        lambda *_: {"project": {"source_dir": str(directory), "name": "P"}})


def _write_wild_table(directory, name="实验导出.csv"):
    """Headers carry no hints at all and the two sequence columns are swapped."""
    event = dict.fromkeys(CORE_EVENT_FIELDS, "")
    event.update(event_id="SE:1", gene_id="G1", gene_symbol="GENE1", event_type="SE",
                 chromosome="chr1", strand="+", genomic_coordinates="chr1:10-20",
                 coordinate_system="1-based-inclusive", source_tool="rMATS", FDR="0.01",
                 delta_PSI="0.3", p_value="0.001")
    with (directory / "AS_event_master.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CORE_EVENT_FIELDS, delimiter="\t")
        writer.writeheader(); writer.writerow(event)
    with (directory / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["编号", "位点", "序列1", "序列2"])
        # 序列1 holds the altered CDS on purpose: detection must un-swap it.
        writer.writerow(["SE:1", 21, ALTERED, REFERENCE])
    return directory


def test_wild_headers_are_guessed_and_need_confirmation(client, monkeypatch, tmp_path):
    _write_wild_table(tmp_path)
    _project(monkeypatch, tmp_path)
    body = client.get("/api/neoantigen/readiness/P").json()
    assert body["cds_status"] == "available"
    assert body["cds_needs_confirmation"] is True
    detail = body["cds_details"]["实验导出.csv"]
    assert detail["map"] == {"event_id": "编号", "junction_nt": "位点",
                             "reference_cds": "序列2", "altered_cds": "序列1"}
    assert detail["preview"], "the dialog needs sample values to show the customer"


def test_confirmed_mapping_is_remembered_and_stops_the_prompt(client, monkeypatch, tmp_path):
    _write_wild_table(tmp_path)
    _project(monkeypatch, tmp_path)
    mapping = {"event_id": "编号", "junction_nt": "位点",
               "reference_cds": "序列2", "altered_cds": "序列1"}
    saved = client.post("/api/neoantigen/column-map", json={
        "project_id": "P", "file": "实验导出.csv", "map": mapping})
    assert saved.status_code == 200, saved.text
    assert saved.json()["verified_rows"] == 1
    after = client.get("/api/neoantigen/readiness/P").json()
    assert after["cds_needs_confirmation"] is False
    assert after["cds_details"]["实验导出.csv"]["source"] == "saved"
    again = client.post("/api/neoantigen/run", json={"project_id": "P", "alleles": []})
    assert again.status_code == 200, again.text
    assert again.json()["column_mapping"] == mapping
    assert again.json()["candidate_count"] > 0


def test_mapping_rejects_the_same_column_for_two_roles(client, monkeypatch, tmp_path):
    _write_wild_table(tmp_path)
    _project(monkeypatch, tmp_path)
    response = client.post("/api/neoantigen/column-map", json={
        "project_id": "P", "file": "实验导出.csv",
        "map": {"event_id": "编号", "junction_nt": "位点",
                "reference_cds": "序列1", "altered_cds": "序列1"}})
    assert response.status_code == 422
    assert "两个字段角色" in response.json()["detail"]


def test_mapping_rejects_an_unknown_column(client, monkeypatch, tmp_path):
    _write_wild_table(tmp_path)
    _project(monkeypatch, tmp_path)
    response = client.post("/api/neoantigen/column-map", json={
        "project_id": "P", "file": "实验导出.csv",
        "map": {"event_id": "编号", "junction_nt": "位点",
                "reference_cds": "不存在", "altered_cds": "序列1"}})
    assert response.status_code == 422
    assert "不存在" in response.json()["detail"]


def test_many_peptide_allele_pairs_are_predicted_in_batches(monkeypatch, tmp_path):
    """592 pairs used to be refused at 200; they must now be batched instead."""
    import splicegaip.neoantigen as neo

    calls: list[tuple[int, str]] = []

    class FakeClient:
        def predict_mhci(self, peptides, alleles, *, method="netmhcpan_el"):
            calls.append((len(peptides), alleles[0]))
            return [{"peptide": peptide, "allele": alleles[0], "score": 0.5,
                     "percentile_rank": 1.0, "raw": {}} for peptide in peptides]

    monkeypatch.setattr("splicegaip.peptide.iedb.IedbClient", FakeClient)
    peptides = [f"PEPTIDE{index:02d}" for index in range(296)]
    scores, errors = neo._predict_batched([(peptide, allele) for peptide in peptides
                                           for allele in ("HLA-A*02:01", "HLA-B*07:02")])
    assert len(scores) == 592
    assert errors == []
    # One client call per allele; the client itself splits into 100-peptide requests.
    assert calls == [(296, "HLA-A*02:01"), (296, "HLA-B*07:02")]
