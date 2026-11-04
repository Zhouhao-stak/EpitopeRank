"""The peptide API must accept any CDS table name a customer happens to use."""

from __future__ import annotations

import csv

import pytest
from fastapi.testclient import TestClient

from epitoperank.api.app import create_app
from epitoperank.splicing.schema import CORE_EVENT_FIELDS

REFERENCE = "ATG" + "GCT" * 20
ALTERED = "ATG" + "GCT" * 6 + "TGG" * 8


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("EPITOPERANK_INGEST_ALLOW_EXTERNAL", "1")
    return TestClient(create_app())


def _write_input(directory, cds_name="客户_CDS对照表.csv", header=("事件ID", "参考序列", "变异序列", "连接点")):
    event = dict.fromkeys(CORE_EVENT_FIELDS, "")
    event.update(event_id="SE:1", gene_id="G1", gene_symbol="GENE1", event_type="SE",
                 chromosome="chr1", strand="+", genomic_coordinates="chr1:10-20",
                 coordinate_system="1-based-inclusive", source_tool="rMATS", FDR="0.01",
                 delta_PSI="0.3", p_value="0.001")
    with (directory / "AS_event_master.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CORE_EVENT_FIELDS, delimiter="\t")
        writer.writeheader(); writer.writerow(event)
    with (directory / cds_name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(header); writer.writerow(["SE:1", REFERENCE, ALTERED, 21])
    return directory


def test_run_detects_customer_named_table_without_being_told(client, tmp_path):
    _write_input(tmp_path)
    response = client.post("/api/neoantigen/run", json={"input_dir": str(tmp_path), "alleles": []})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["candidate_count"] > 0
    assert data["cds_table_name"] == "客户_CDS对照表.csv"
    assert data["cds_table_auto_selected"] is True


def test_run_accepts_an_explicit_choice(client, tmp_path):
    _write_input(tmp_path)
    response = client.post("/api/neoantigen/run", json={
        "input_dir": str(tmp_path), "cds_table": "客户_CDS对照表.csv", "alleles": []})
    assert response.status_code == 200, response.text
    assert response.json()["cds_table_auto_selected"] is False


def test_run_prefers_the_classic_name_when_several_tables_exist(client, tmp_path):
    _write_input(tmp_path, cds_name="splice_orfs.tsv", header=("event_id", "reference_cds", "altered_cds", "junction_nt"))
    _write_input(tmp_path, cds_name="another_cds.tsv")
    response = client.post("/api/neoantigen/run", json={"input_dir": str(tmp_path), "alleles": []})
    assert response.status_code == 200, response.text
    assert response.json()["cds_table_name"] == "splice_orfs.tsv"


def test_run_explains_what_is_missing(client, tmp_path):
    _write_input(tmp_path, cds_name="notes.tsv", header=("gene", "value"))
    response = client.post("/api/neoantigen/run", json={"input_dir": str(tmp_path), "alleles": []})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "event_id" in detail and "reference_cds" in detail
    assert "文件名不限" in detail


def test_run_rejects_bad_columns_with_a_readable_reason(client, tmp_path):
    _write_input(tmp_path, cds_name="broken.tsv", header=("event_id", "reference_cds", "junction_nt"))
    response = client.post("/api/neoantigen/run", json={
        "input_dir": str(tmp_path), "cds_table": "broken.tsv", "alleles": []})
    assert response.status_code == 422
    assert "altered_cds" in response.json()["detail"]


def test_cds_upload_requires_a_real_project(client, tmp_path):
    response = client.post("/api/neoantigen/cds-upload",
                           data={"project_id": "SPN-NOT-A-PROJECT"},
                           files={"file": ("cds.tsv", b"event_id\treference_cds\taltered_cds\tjunction_nt\n", "text/plain")})
    assert response.status_code == 404
