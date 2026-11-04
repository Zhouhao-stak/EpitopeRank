from pathlib import Path

import pytest

from epitoperank.data.bgi_report import apply, preview
from epitoperank.data.loader import load_dataset


def test_bgi_report_merges_samples_without_inventing_significance(tmp_path: Path) -> None:
    for sample, psi in (("OC_001", "0.2"), ("OC_002", "0.7")):
        folder = tmp_path / "nested" / sample
        folder.mkdir(parents=True)
        (folder / f"{sample}.SE.xls").write_text(
            "gene_id\tgene_symbol\tas_chr\tas_strand\tas_exonstart_0base\tas_exonend\tas_inclevel1_" + sample + "\n"
            f"G1\tGene1\tchr1\t+\t10\t20\t{psi}\n",
            encoding="utf-8",
        )
    found = preview(tmp_path)
    assert found is not None
    assert found["files_count"] == 2
    assert all(not value for value in found["mapping"]["sample_groups"].values())
    with pytest.raises(ValueError, match="biological group"):
        apply(tmp_path, {"sample_groups": {"OC_001": "control"}})
    result = apply(tmp_path, {"sample_groups": {"OC_001": "control", "OC_002": "case"}})
    dataset = load_dataset(result["path"])
    assert len(dataset.events) == 1
    event = dataset.events[0]
    assert event.psi_by_sample == {"OC_001": 0.2, "OC_002": 0.7}
    assert event.p_value is None and event.fdr is None
    assert abs(event.delta_psi) == pytest.approx(0.5)


def test_bgi_report_recognizes_flat_browser_upload(tmp_path: Path) -> None:
    for sample in ("OC_001", "OC_002"):
        (tmp_path / f"{sample}.SE.xls").write_text(
            f"gene_id\tas_chr\tas_strand\tas_exonstart_0base\tas_exonend\tas_inclevel1_{sample}\n"
            "G1\tchr1\t+\t10\t20\t0.4\n", encoding="utf-8",
        )
    result = preview(tmp_path)
    assert result is not None
    assert result["files_count"] == 2
