"""Each project must publish one browsable folder of deliverables."""

from __future__ import annotations

from pathlib import Path

from splicegaip.results_export import export_bundle, safe_folder_name


def _fake_project(root: Path, project_id: str = "SPN-TEST0001") -> Path:
    directory = root / project_id
    (directory / "figures").mkdir(parents=True)
    (directory / "report.html").write_text("<html>报告</html>", encoding="utf-8")
    (directory / "report.pdf").write_bytes(b"%PDF-1.4")
    (directory / "figures" / "volcano.png").write_bytes(b"\x89PNG")
    (directory / "figures" / "volcano.svg").write_text("<svg/>", encoding="utf-8")
    (directory / "agent_state.json").write_text("{}", encoding="utf-8")
    return directory


def test_export_copies_report_and_figures(tmp_path):
    project_dir = _fake_project(tmp_path / "runtime")
    bundle = export_bundle(
        project_dir,
        "pDC 活化",
        "SPN-TEST0001",
        results_root=tmp_path / "results",
        stats={"sample_count": 6, "event_count": 4771, "significant_count": 24},
    )

    assert bundle is not None
    assert bundle.parent == tmp_path / "results"
    assert (bundle / "report.html").is_file()
    assert (bundle / "report.pdf").is_file()
    assert (bundle / "figures" / "volcano.png").is_file()
    assert (bundle / "figures" / "volcano.svg").is_file()

    manifest = (bundle / "项目说明.txt").read_text(encoding="utf-8")
    assert "pDC 活化" in manifest
    assert "4771" in manifest
    assert "24" in manifest


def test_export_skips_agent_state_and_is_idempotent(tmp_path):
    project_dir = _fake_project(tmp_path / "runtime")
    first = export_bundle(
        project_dir, "项目A", "SPN-TEST0001", results_root=tmp_path / "results"
    )
    assert first is not None
    # agent_state.json is internal bookkeeping, not a deliverable.
    assert not (first / "agent_state.json").exists()

    (project_dir / "figures" / "new.png").write_bytes(b"\x89PNG")
    second = export_bundle(
        project_dir, "项目A", "SPN-TEST0001", results_root=tmp_path / "results"
    )
    assert second == first
    assert (second / "figures" / "new.png").is_file()


def test_export_picks_up_peptide_results_from_input_dir(tmp_path):
    project_dir = _fake_project(tmp_path / "runtime")
    peptide = tmp_path / "input" / "neoantigen_results"
    peptide.mkdir(parents=True)
    (peptide / "splice_peptides.tsv").write_text("peptide\tgene\nMAKIYSPD\tMTCH1\n", encoding="utf-8")

    bundle = export_bundle(
        project_dir,
        "带肽的项目",
        "SPN-TEST0001",
        results_root=tmp_path / "results",
        input_dir=tmp_path / "input",
    )
    assert bundle is not None
    assert (bundle / "neoantigen_results" / "splice_peptides.tsv").is_file()


def test_missing_project_dir_returns_none(tmp_path):
    assert export_bundle(
        tmp_path / "nope", "空", "SPN-X", results_root=tmp_path / "results"
    ) is None


def test_folder_name_is_explorer_safe_and_unique():
    name = safe_folder_name('pDC/活化: "剪接"*测试?', "SPN-ABC12345")
    assert name.endswith("_SPN-ABC12345")
    assert not set(name) & set('<>:"/\\|?*')
    assert safe_folder_name("", "SPN-ABC12345").startswith("未命名项目")
    # Long names are trimmed but the id still disambiguates them.
    long_name = safe_folder_name("很长的项目名" * 30, "SPN-ABC12345")
    assert long_name.endswith("_SPN-ABC12345")
    assert len(long_name) < 90


def test_package_bundle_creates_zip(tmp_path):
    from splicegaip.results_export import package_bundle

    project_dir = _fake_project(tmp_path / "runtime")
    bundle = export_bundle(
        project_dir, "打包测试", "SPN-TEST0001", results_root=tmp_path / "results"
    )
    assert bundle is not None
    archive = package_bundle(bundle)
    assert archive is not None and archive.suffix == ".zip"
    import zipfile

    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    assert "report.html" in names
    assert "figures/volcano.png" in names


def test_upload_without_configuration_reports_clearly(tmp_path, monkeypatch):
    from splicegaip.results_export import upload_bundle

    monkeypatch.delenv("SPLICEGAIP_CLOUD_URL", raising=False)
    result = upload_bundle(tmp_path / "nothing.zip")
    assert result["ok"] is False
    assert "SPLICEGAIP_CLOUD_URL" in result["detail"]


def test_package_bundle_creates_zip(tmp_path):
    from splicegaip.results_export import package_bundle

    project_dir = _fake_project(tmp_path / "runtime")
    bundle = export_bundle(
        project_dir, "打包测试", "SPN-TEST0001", results_root=tmp_path / "results"
    )
    assert bundle is not None
    archive = package_bundle(bundle)
    assert archive is not None and archive.suffix == ".zip"
    import zipfile

    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    assert "report.html" in names
    assert "figures/volcano.png" in names


def test_upload_without_configuration_reports_clearly(tmp_path, monkeypatch):
    from splicegaip.results_export import upload_bundle

    monkeypatch.delenv("SPLICEGAIP_CLOUD_URL", raising=False)
    result = upload_bundle(tmp_path / "nothing.zip")
    assert result["ok"] is False
    assert "SPLICEGAIP_CLOUD_URL" in result["detail"]
