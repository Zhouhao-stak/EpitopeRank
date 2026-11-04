"""CDS tables are found by content, never by a magic filename."""

from __future__ import annotations

import csv

import pytest

from epitoperank.neoantigen import (
    CDS_FIELDS,
    canonical_cds_fields,
    discover_cds_tables,
    inspect_cds_table,
    pick_cds_table,
    run,
)
from epitoperank.splicing.schema import CORE_EVENT_FIELDS

REFERENCE = "ATG" + "GCT" * 20
ALTERED = "ATG" + "GCT" * 6 + "TGG" * 8


def _write_event_table(directory):
    event = dict.fromkeys(CORE_EVENT_FIELDS, "")
    event.update(event_id="SE:1", gene_id="G1", gene_symbol="GENE1", event_type="SE",
                 chromosome="chr1", strand="+", genomic_coordinates="chr1:10-20",
                 coordinate_system="1-based-inclusive", source_tool="rMATS", FDR="0.01",
                 delta_PSI="0.3", p_value="0.001")
    with (directory / "AS_event_master.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CORE_EVENT_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerow(event)


def _write_cds(path, header=CDS_FIELDS, rows=(("SE:1", REFERENCE, ALTERED, 21),),
               delimiter="\t", encoding="utf-8"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.writer(handle, delimiter=delimiter)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def test_arbitrary_filename_is_recognised(tmp_path):
    table = _write_cds(tmp_path / "客户给的序列表_v3.tsv")
    info = inspect_cds_table(table)
    assert info["valid"] and info["has_rows"]
    assert info["missing"] == []


@pytest.mark.parametrize("header", [
    ("Event ID", "Reference CDS", "Altered CDS", "Junction nt"),
    ("事件ID", "参考序列", "变异序列", "连接点"),
    ("event-id", "ref_cds", "mutant_cds", "junction_position"),
])
def test_header_aliases_are_accepted(tmp_path, header):
    table = _write_cds(tmp_path / "table.tsv", header=header)
    assert inspect_cds_table(table)["valid"] is True
    assert canonical_cds_fields(header) == list(CDS_FIELDS)


def test_missing_column_reports_what_is_missing(tmp_path):
    table = _write_cds(tmp_path / "broken.tsv", header=("event_id", "reference_cds", "junction_nt"))
    info = inspect_cds_table(table)
    assert info["valid"] is False
    assert info["missing"] == ["altered_cds"]
    assert "altered_cds" in info["reason"]


def test_csv_and_gbk_exports_are_readable(tmp_path):
    table = _write_cds(tmp_path / "export.csv", header=("事件ID", "参考序列", "变异序列", "连接点"),
                       delimiter=",", encoding="gb18030")
    assert inspect_cds_table(table)["valid"] is True


def test_discovery_ignores_non_cds_files_and_prefers_known_names(tmp_path):
    _write_event_table(tmp_path)
    (tmp_path / "SE.MATS.JC.txt").write_text("ID\tGeneID\n1\tG1\n", encoding="utf-8")
    _write_cds(tmp_path / "whatever_cds.tsv")
    _write_cds(tmp_path / "splice_orfs.tsv")
    names = [item["name"] for item in discover_cds_tables(tmp_path)]
    assert names[0] == "splice_orfs.tsv"
    assert "whatever_cds.tsv" in names
    assert "SE.MATS.JC.txt" not in names
    assert pick_cds_table(discover_cds_tables(tmp_path)).name == "splice_orfs.tsv"


def test_discovery_returns_partial_tables_only_when_asked(tmp_path):
    _write_cds(tmp_path / "half.tsv", header=("event_id", "reference_cds"))
    assert discover_cds_tables(tmp_path) == []
    partial = [item for item in discover_cds_tables(tmp_path, include_partial=True) if not item["valid"]]
    assert partial and "altered_cds" in partial[0]["missing"]


def test_run_accepts_customer_named_table_with_alias_headers(tmp_path):
    _write_event_table(tmp_path)
    table = _write_cds(tmp_path / "上机数据_CDS对照.csv",
                       header=("Event ID", "Reference CDS", "Altered CDS", "Junction nt"),
                       delimiter=",")
    result = run(tmp_path, table, tmp_path / "out")
    assert result["candidate_count"] > 0
    assert result["skipped"] == []


def test_run_reports_missing_columns_clearly(tmp_path):
    """Two sequence columns and no junction column: the roles cannot be settled."""
    _write_event_table(tmp_path)
    table = _write_cds(tmp_path / "bad.tsv", header=("event_id", "seq_a", "seq_b"),
                       rows=(("SE:1", REFERENCE, ALTERED),))
    with pytest.raises(ValueError) as error:
        run(tmp_path, table, tmp_path / "out")
    assert "junction_nt" in str(error.value)
    assert "列映射" in str(error.value)


def test_run_accepts_wild_column_names_by_content(tmp_path):
    """A customer table called 编号 / 位点 / 序列1 / 序列2 must just work."""
    _write_event_table(tmp_path)
    table = _write_cds(tmp_path / "客户表.tsv", header=("编号", "位点", "序列1", "序列2"),
                       rows=(("SE:1", 21, ALTERED, REFERENCE),))
    assert inspect_cds_table(table)["valid"] is True
    result = run(tmp_path, table, tmp_path / "out")
    assert result["candidate_count"] > 0
    assert result["skipped"] == []


def test_column_map_overrides_detection(tmp_path):
    """A human-confirmed mapping always wins over the guess."""
    _write_event_table(tmp_path)
    table = _write_cds(tmp_path / "swap.tsv", header=("a", "b", "c", "d"),
                       rows=(("SE:1", 21, ALTERED, REFERENCE),))
    correct = {"event_id": "a", "junction_nt": "b", "reference_cds": "d", "altered_cds": "c"}
    result = run(tmp_path, table, tmp_path / "out", column_map=correct)
    assert result["column_mapping"] == correct
    assert result["candidate_count"] > 0
    flipped = {"event_id": "a", "junction_nt": "b", "reference_cds": "c", "altered_cds": "d"}
    other = run(tmp_path, table, tmp_path / "out2", column_map=flipped)
    assert other["column_mapping"] == flipped
    assert "column_mapping" in other


def test_run_still_accepts_legacy_splice_orfs_table(tmp_path):
    _write_event_table(tmp_path)
    table = _write_cds(tmp_path / "splice_orfs.tsv")
    assert run(tmp_path, table, tmp_path / "out")["candidate_count"] > 0


def test_rmats_event_tables_are_not_offered_as_partial_cds(tmp_path):
    """A plain rMATS directory must not be reported as "CDS tables missing columns".

    Customers upload the five MATS.JC.txt files next to their CDS table; telling
    them those event tables "look like a CDS table but lack columns" is noise
    that reads like an error in their own data.
    """
    _write_event_table(tmp_path)
    rmats_header = ("ID", "GeneID", "geneSymbol", "chr", "strand", "exonStart_0base",
                    "exonEnd", "upstreamES", "upstreamEE", "downstreamES", "downstreamEE",
                    "ID.1", "IJC_SAMPLE_1", "SJC_SAMPLE_1", "IJC_SAMPLE_2", "SJC_SAMPLE_2",
                    "IncFormLen", "SkipFormLen", "PValue", "FDR", "IncLevel1", "IncLevel2",
                    "IncLevelDifference")
    with (tmp_path / "SE.MATS.JC.txt").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(rmats_header)
        writer.writerow(("SE:1", "G1", "GENE1", "chr1", "+", 10, 20, 5, 9, 21, 30,
                         "SE:1", "3,4", "1,2", "5,6", "0,1", 100, 50, "0.01", "0.02",
                         "0.8,0.7", "0.1,0.2", "0.7"))
    cds = _write_cds(tmp_path / "客户给的_剪接CDS对照表.csv", delimiter=",")

    discovered = discover_cds_tables(tmp_path)
    assert [item["name"] for item in discovered] == [cds.name]

    everything = discover_cds_tables(tmp_path, include_partial=True)
    names = [item["name"] for item in everything]
    assert "SE.MATS.JC.txt" not in names
    assert all(not item.get("rmats") for item in everything)
