"""Regression tests for bare-peptide API predictions (no CDS context).

The web page submits arbitrary 11-30 aa peptides for MHC-II. Those must be sent
to IEDB with ``length="asis"``; using the CDS window length makes IEDB return
sliding 15-mer windows, which the exact-peptide filter then drops silently.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from epitoperank.peptide import pipeline
from epitoperank.peptide.hla import parse_panel
from epitoperank.peptide.pipeline import PeptideOptions, _run_iedb_with, predict_peptides


class FakeIedbClient:
    """最小 IEDB 替身：只记录调用参数并返回一条可去重的预测记录。"""

    def __init__(self) -> None:
        self.mhci_calls: list[dict[str, Any]] = []
        self.mhcii_calls: list[dict[str, Any]] = []
        self.calls: list[Any] = []

    def predict_mhci(self, peptides, alleles, *, lengths, method):  # noqa: ANN001
        self.mhci_calls.append({"peptides": list(peptides), "method": method})
        return [self._row(peptides[0], alleles[0], 1, method)]

    def predict_mhcii(self, peptides, alleles, *, length, method):  # noqa: ANN001
        self.mhcii_calls.append({"peptides": list(peptides), "length": length,
                                 "method": method})
        return [self._row(peptides[0], alleles[0], 2, method)]

    def predict_processing(self, peptides, alleles, *, lengths):  # noqa: ANN001
        return []

    def predict_stability(self, peptides, alleles):  # noqa: ANN001
        return []

    def predict_mhcnp(self, peptides, alleles, *, lengths):  # noqa: ANN001
        return []

    @staticmethod
    def _row(peptide: str, allele: str, mhc_class: int, method: str) -> dict[str, Any]:
        return {"peptide": peptide, "allele": allele, "mhc_class": mhc_class,
                "method": method, "percentile_rank": 0.04,
                "request_id": "fake", "source": "IEDB"}


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeIedbClient()
    monkeypatch.setattr(pipeline, "_client", lambda options: client)
    return client


def test_bare_class2_uses_asis_length(fake_client) -> None:
    result = predict_peptides(
        ["ENPVVHFFKNIVTPRTPP"], ["HLA-DRB1*15:01"],
        mhc_class="class2", predictor="iedb", processing=False,
    )
    assert fake_client.mhcii_calls[0]["length"] == "asis"
    assert len(result["predictions"]) == 1
    assert result["predictions"][0]["percentile_rank"] == 0.04
    assert result["errors"] == []


@pytest.mark.parametrize("length", [11, 15, 18, 25, 30])
def test_bare_class2_accepts_every_documented_length(fake_client, length) -> None:
    peptide = "A" * (length - 1) + "K"
    result = predict_peptides(
        [peptide], ["HLA-DRB1*15:01"],
        mhc_class="class2", predictor="iedb", processing=False,
    )
    assert fake_client.mhcii_calls[-1]["peptides"] == [peptide]
    assert fake_client.mhcii_calls[-1]["length"] == "asis"
    assert len(result["predictions"]) == 1


def test_cds_mode_still_uses_fixed_class2_window(fake_client) -> None:
    """CDS/CLI 的 15-mer 上下文是有意设计，不能被裸肽修复改坏。"""
    options = PeptideOptions(alleles=["HLA-DRB1*15:01"], mhc_class="class2",
                             processing=False, class2_window=15)
    candidates = [{"peptide": "A" * 9, "length": 9,
                   "class2_context": "A" * 15}]
    _run_iedb_with(fake_client, candidates,
                   parse_panel(options.alleles, allow_mixed_classes=True), options)
    assert fake_client.mhcii_calls[0]["length"] == 15
    assert fake_client.mhcii_calls[0]["peptides"] == ["A" * 15]


def test_class1_long_peptide_reports_instead_of_silent_drop(fake_client) -> None:
    result = predict_peptides(
        ["NLVPMVATVAAA"], ["HLA-A*02:01"],
        mhc_class="class1", predictor="iedb", processing=False,
    )
    assert result["predictions"] == []
    assert any("长于 11 aa" in str(item["error"]) for item in result["errors"])


def test_class2_without_class2_allele_reports(fake_client) -> None:
    result = predict_peptides(
        ["ENPVVHFFKNIVTPRTPP"], ["HLA-A*02:01"],
        mhc_class="class2", predictor="iedb", processing=False,
    )
    assert result["predictions"] == []
    assert any("MHC-II 型别" in str(item["error"]) for item in result["errors"])


def test_auto_falls_back_to_iedb_when_local_missing(fake_client, monkeypatch) -> None:
    from epitoperank.peptide import local_models

    monkeypatch.setattr(local_models, "available", lambda: False)
    result = predict_peptides(
        ["NLVPMVATV"], ["HLA-A*02:01"],
        mhc_class="class1", predictor="auto", processing=False,
    )
    assert fake_client.mhci_calls
    assert len(result["predictions"]) == 1


def test_local_missing_raises_clear_error(monkeypatch) -> None:
    from epitoperank.peptide import local_models

    monkeypatch.setattr(local_models, "available", lambda: False)
    with pytest.raises(ValueError, match="MHCflurry 未安装"):
        predict_peptides(["NLVPMVATV"], ["HLA-A*02:01"], predictor="local")


def test_api_local_missing_returns_422_with_chinese_hint() -> None:
    from epitoperank.api.app import create_app

    response = TestClient(create_app()).post("/api/peptide/predict", json={
        "peptides": ["NLVPMVATV"], "alleles": ["HLA-A*02:01"],
        "predictor": "local", "processing": False,
    })
    assert response.status_code == 422
    assert "MHCflurry" in str(response.json()["detail"])
