"""Offline tests for the IEDB client using a fake opener (no network)."""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.parse import parse_qs

import pytest

from epitoperank.peptide.iedb import (
    IedbClient,
    IedbResponseError,
)


class FakeResponse:
    """Minimal context-manager response for ``urllib`` style openers."""

    status = 200

    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self, size: int | None = None) -> bytes:
        return self._body if size is None else self._body[:size]

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


def make_post_opener(table: str, calls: list) -> callable:
    def opener(request, timeout=None):
        calls.append(request)
        return FakeResponse(table.encode("utf-8"))

    return opener


def make_client(table: str, calls: list, *, cache_dir=None) -> IedbClient:
    return IedbClient(
        timeout=5.0,
        retries=0,
        min_interval=0,
        cache_dir=cache_dir,
        opener=make_post_opener(table, calls),
    )


def test_predict_mhci_sends_expected_payload_and_filters_rows() -> None:
    table = (
        "allele\tseq_num\tstart\tend\tlength\tpeptide\tcore\tscore\tpercentile_rank\n"
        "HLA-A*02:01\t1\t1\t9\t9\tSLYNTVATL\tSLYNTVATL\t0.828\t0.06\n"
        "HLA-A*02:01\t2\t1\t10\t10\tGILGFVFTLY\tGILGFVFTLY\t0.7\t0.5\n"
        "HLA-A*02:01\t3\t1\t9\t9\tAAAAAAAAA\tAAAAAAAAA\t0.01\t50\n"
    )
    calls: list = []
    client = make_client(table, calls)

    records = client.predict_mhci(["SLYNTVATL", "GILGFVFTLY"], ["HLA-A*02:01"])

    assert len(calls) == 1
    params = parse_qs(calls[0].data.decode("utf-8"))
    assert params["method"] == ["netmhcpan_el-4.1"]
    # One allele repeated once per requested length, paired with '9,10'.
    assert params["allele"] == ["HLA-A*02:01,HLA-A*02:01"]
    assert params["length"] == ["9,10"]
    assert params["sequence_text"][0] == ">p1\nSLYNTVATL\n>p2\nGILGFVFTLY"

    assert {row["peptide"] for row in records} == {"SLYNTVATL", "GILGFVFTLY"}
    by_peptide = {row["peptide"]: row for row in records}
    assert by_peptide["SLYNTVATL"]["percentile_rank"] == pytest.approx(0.06)
    assert by_peptide["SLYNTVATL"]["score"] == pytest.approx(0.828)
    assert by_peptide["SLYNTVATL"]["mhc_class"] == 1
    assert by_peptide["SLYNTVATL"]["method"] == "netmhcpan_el"
    assert by_peptide["SLYNTVATL"]["source"] == "IEDB"
    assert len(by_peptide["SLYNTVATL"]["request_id"]) == 32


def test_predict_mhcii_parses_rank_into_percentile() -> None:
    table = (
        "allele\tseq_num\tstart\tend\tlength\tcore_peptide\tpeptide\tscore\trank\n"
        "HLA-DRB1*01:01\t1\t1\t15\t15\tLLGDGSLYN\tGILGFVFTLYCVHQR\t0.0045\t57.0\n"
    )
    calls: list = []
    client = make_client(table, calls)

    records = client.predict_mhcii(["GILGFVFTLYCVHQR"], ["HLA-DRB1*01:01"])

    assert len(records) == 1
    assert records[0]["percentile_rank"] == pytest.approx(57.0)
    assert records[0]["core"] == "LLGDGSLYN"
    assert records[0]["mhc_class"] == 2
    assert records[0]["method"] == "netmhciipan_el"
    params = parse_qs(calls[0].data.decode("utf-8"))
    assert params["method"] == ["netmhciipan_el-4.1"]
    assert params["length"] == ["15"]


def test_predict_processing_sends_one_request_per_length() -> None:
    table = (
        "allele\tseq_num\tstart\tend\tlength\tpeptide\tproteasome_score\ttap_score"
        "\tmhc_score\tprocessing_score\ttotal_score\tic50_score\n"
        "HLA-A*02:01\t1\t1\t9\t9\tSLYNTVATL\t1.5450\t0.5087\t-2.2849\t2.0537\t-0.2312\t192.7\n"
        "HLA-A*02:01\t2\t1\t10\t10\tGILGFVFTLY\t1.2\t0.4\t-1.5\t1.9\t0.85\t50.0\n"
    )
    calls: list = []
    client = make_client(table, calls)

    records = client.predict_processing(["SLYNTVATL", "GILGFVFTLY"], ["HLA-A*02:01"])

    assert len(calls) == 2
    lengths = [parse_qs(call.data.decode("utf-8"))["length"][0] for call in calls]
    assert lengths == ["9", "10"]
    assert all(
        parse_qs(call.data.decode("utf-8"))["method"] == ["recommended"] for call in calls
    )

    assert len(records) == 2
    by_peptide = {row["peptide"]: row for row in records}
    assert by_peptide["SLYNTVATL"]["proteasome_score"] == pytest.approx(1.545)
    assert by_peptide["SLYNTVATL"]["tap_score"] == pytest.approx(0.5087)
    assert by_peptide["SLYNTVATL"]["total_score"] == pytest.approx(-0.2312)
    assert by_peptide["SLYNTVATL"]["processing_score"] == pytest.approx(2.0537)
    assert by_peptide["GILGFVFTLY"]["total_score"] == pytest.approx(0.85)


def test_predict_mhcnp_parses_probability() -> None:
    table = (
        "allele\tseq_num\tstart\tend\tlength\tpeptide\tprob_score\n"
        "HLA-A*02:01\t1\t1\t9\t9\tSLYNTVATL\t0.0788\n"
    )
    calls: list = []
    client = make_client(table, calls)

    records = client.predict_mhcnp(["SLYNTVATL"], ["HLA-A*02:01"])

    assert len(records) == 1
    assert records[0]["mhcnp_probability"] == pytest.approx(0.0788)
    assert records[0]["method"] == "mhcnp"
    params = parse_qs(calls[0].data.decode("utf-8"))
    assert params["method"] == ["mhcnp"]


def test_header_only_table_returns_empty_list() -> None:
    table = (
        "allele\tseq_num\tstart\tend\tlength\tpeptide\tcore\tscore\tpercentile_rank\n"
    )
    calls: list = []
    client = make_client(table, calls)

    assert client.predict_mhci(["SLYNTVATL"], ["HLA-A*02:01"]) == []


def test_error_body_raises_response_error() -> None:
    table = "Input length should be between 11-30.\n"
    calls: list = []
    client = make_client(table, calls)

    with pytest.raises(IedbResponseError, match="did not return a table"):
        client.predict_mhcii(["SLYNTVATL"], ["HLA-DRB1*01:01"])


def test_disk_cache_prevents_second_network_call(tmp_path) -> None:
    table = (
        "allele\tseq_num\tstart\tend\tlength\tpeptide\tcore\tscore\tpercentile_rank\n"
        "HLA-A*02:01\t1\t1\t9\t9\tSLYNTVATL\tSLYNTVATL\t0.828\t0.06\n"
    )
    calls: list = []
    client = make_client(table, calls, cache_dir=tmp_path)

    first = client.predict_mhci(["SLYNTVATL"], ["HLA-A*02:01"])
    second = client.predict_mhci(["SLYNTVATL"], ["HLA-A*02:01"])

    assert len(calls) == 1
    assert first == second
    assert client.calls[0]["cached"] is False
    assert client.calls[1]["cached"] is True


def test_lookup_epitopes_parses_json_and_survives_failure() -> None:
    payload = [
        {
            "mhc_class": "I",
            "mhc_restriction": "HLA-A*02:01",
            "qualitative_measure": "Positive",
            "assay_description": "multimer/tetramer<br/>binding",
            "source_organism_name": "Human immunodeficiency virus 1",
            "structure_description": "SLYNTVATL",
            "pubmed_id": "9502585",
        }
    ]
    get_calls: list = []

    def opener(request, timeout=None):
        assert getattr(request, "data", None) is None  # GET, not POST
        get_calls.append(request)
        return FakeResponse(json.dumps(payload).encode("utf-8"))

    client = IedbClient(timeout=5.0, retries=0, min_interval=0, cache_dir=None, opener=opener)
    found = client.lookup_epitopes(["SLYNTVATL"], limit=2)

    assert len(get_calls) == 1
    assert "SLYNTVATL" in found
    assert found["SLYNTVATL"][0]["mhc_restriction"] == "HLA-A*02:01"
    assert found["SLYNTVATL"][0]["assay"] == "multimer/tetramer binding"
    assert found["SLYNTVATL"][0]["pubmed_id"] == "9502585"

    def failing_opener(request, timeout=None):
        raise URLError("network down")

    offline = IedbClient(timeout=5.0, retries=0, min_interval=0, cache_dir=None,
                         opener=failing_opener)
    assert offline.lookup_epitopes(["SLYNTVATL"]) == {"SLYNTVATL": []}
