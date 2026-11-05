"""rMATS 文件自动识别（兼容性）测试。

真实数据几乎从不使用 rMATS 官方的 ``SE.MATS.JC.txt`` 命名：上游流水线会加
比较组前缀、改用 JCEC 计数、转小写、压成 gz，甚至把结果放进子目录。
本模块把这些真实形态都固化成用例，防止以后又退回“文件名硬编码匹配”。
"""

from __future__ import annotations

import gzip

import pytest

from epitoperank.data.loader import load_dataset
from epitoperank.splicing.parsers.rmats import (
    count_mode_from_filename,
    discover_rmats_tables,
    event_type_from_filename,
    event_type_from_header,
    infer_event_type,
    is_rmats_directory,
    parse_rmats_directory,
)

# 五类事件的真实表头（取自 rMATS 4.x 输出，A3SS 与 A5SS 逐列相同）。
_HEADERS = {
    "SE": (
        "ID\tGeneID\tgeneSymbol\tchr\tstrand\texonStart_0base\texonEnd\tupstreamES\t"
        "upstreamEE\tdownstreamES\tdownstreamEE\tID\tIJC_SAMPLE_1\tSJC_SAMPLE_1\t"
        "IJC_SAMPLE_2\tSJC_SAMPLE_2\tIncFormLen\tSkipFormLen\tPValue\tFDR\tIncLevel1\t"
        "IncLevel2\tIncLevelDifference"
    ),
    "MXE": (
        "ID\tGeneID\tgeneSymbol\tchr\tstrand\t1stExonStart_0base\t1stExonEnd\t"
        "2ndExonStart_0base\t2ndExonEnd\tupstreamES\tupstreamEE\tdownstreamES\t"
        "downstreamEE\tID\tIJC_SAMPLE_1\tSJC_SAMPLE_1\tIJC_SAMPLE_2\tSJC_SAMPLE_2\t"
        "IncFormLen\tSkipFormLen\tPValue\tFDR\tIncLevel1\tIncLevel2\tIncLevelDifference"
    ),
    "RI": (
        "ID\tGeneID\tgeneSymbol\tchr\tstrand\triExonStart_0base\triExonEnd\tupstreamES\t"
        "upstreamEE\tdownstreamES\tdownstreamEE\tID\tIJC_SAMPLE_1\tSJC_SAMPLE_1\t"
        "IJC_SAMPLE_2\tSJC_SAMPLE_2\tIncFormLen\tSkipFormLen\tPValue\tFDR\tIncLevel1\t"
        "IncLevel2\tIncLevelDifference"
    ),
    "A3SS": (
        "ID\tGeneID\tgeneSymbol\tchr\tstrand\tlongExonStart_0base\tlongExonEnd\tshortES\t"
        "shortEE\tflankingES\tflankingEE\tID\tIJC_SAMPLE_1\tSJC_SAMPLE_1\tIJC_SAMPLE_2\t"
        "SJC_SAMPLE_2\tIncFormLen\tSkipFormLen\tPValue\tFDR\tIncLevel1\tIncLevel2\t"
        "IncLevelDifference"
    ),
}
_HEADERS["A5SS"] = _HEADERS["A3SS"]

_DATA_ROW = {
    "SE": (
        "1\tENSG00000000001\tGENEA\tchr1\t+\t1000\t1100\t900\t950\t1200\t1250\t1\t"
        "10,12\t3,4\t5,6\t2,3\t50\t100\t0.01\t0.05\t0.8,0.75\t0.3,0.35\t-0.45"
    ),
    "MXE": (
        "1\tENSG00000000002\tGENEB\tchr2\t+\t2000\t2100\t2300\t2400\t1900\t1950\t"
        "2500\t2550\t1\t10,12\t3,4\t5,6\t2,3\t50\t100\t0.01\t0.05\t0.8,0.75\t0.3,0.35\t-0.45"
    ),
    "RI": (
        "1\tENSG00000000003\tGENEC\tchr3\t+\t3000\t3100\t2900\t2950\t3200\t3250\t1\t"
        "10,12\t3,4\t5,6\t2,3\t50\t100\t0.01\t0.05\t0.8,0.75\t0.3,0.35\t-0.45"
    ),
    "A3SS": (
        "1\tENSG00000000004\tGENED\tchr4\t+\t4000\t4100\t4050\t4150\t3900\t3950\t"
        "4200\t4250\t1\t10,12\t3,4\t5,6\t2,3\t50\t100\t0.01\t0.05\t0.8,0.75\t0.3,0.35\t-0.45"
    ),
}
_DATA_ROW["A5SS"] = _DATA_ROW["A3SS"]


def _write_table(directory, filename, event_type, *, gz=False):
    """按事件类型写出一张合法的 rMATS 表，返回写入路径。"""
    text = _HEADERS[event_type] + "\n" + _DATA_ROW[event_type] + "\n"
    path = directory / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if gz:
        with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
            handle.write(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


class TestFilenameInference:
    """文件名推断：真实流水线里的各种命名都要认得。"""

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("SE.MATS.JC.txt", "SE"),
            ("SE.MATS.JCEC.txt", "SE"),
            ("UPF1_KD_vs_ctrl_SE.MATS.JCEC.txt", "SE"),
            ("comparison_S1_vs_S2_SE.MATS.JC.txt", "SE"),
            ("upf1-se-mats-jc.txt", "SE"),
            ("A3SS.MATS.JC.txt", "A3SS"),
            ("A5SS.MATS.JCEC.txt", "A5SS"),
            ("2_MXE.MATS.JC.txt", "MXE"),
            ("ri.mats.jc.txt", "RI"),
            ("sample.RI.MATS.JCEC.txt.gz", "RI"),
        ],
    )
    def test_recognizes_common_naming(self, name, expected):
        """带前缀、大小写混用、JCEC、gz 双扩展名都应识别出正确类型。"""
        assert event_type_from_filename(name) == expected

    @pytest.mark.parametrize(
        "name",
        ["SERBP1_knockdown.txt", "summary_stats.tsv", "A3SS_A5SS_both.txt", "notes.txt"],
    )
    def test_rejects_ambiguous_or_unrelated_names(self, name):
        """基因名里的 SE 不算线索；同时出现两类的名字判为有歧义。"""
        assert event_type_from_filename(name) is None

    def test_count_mode(self):
        """JC 与 JCEC 两种计数模式要能区分，冲突时不给结论。"""
        assert count_mode_from_filename("SE.MATS.JC.txt") == "JC"
        assert count_mode_from_filename("SE.MATS.JCEC.txt") == "JCEC"
        assert count_mode_from_filename("SE.MATS.txt") == ""


class TestHeaderInference:
    """表头推断：光看列就能判定类型，与文件名无关。"""

    @pytest.mark.parametrize("event_type", ["SE", "MXE", "RI"])
    def test_distinct_headers_detected(self, event_type):
        """这三类表头互不相同，可直接由内容判定。"""
        header = _HEADERS[event_type].split("\t")
        assert event_type_from_header(header) == event_type

    def test_a3ss_a5ss_share_signature(self):
        """A3SS 与 A5SS 表头逐列相同，只能定位到家族，必须靠文件名细分。"""
        assert event_type_from_header(_HEADERS["A3SS"].split("\t")) == "A3SS/A5SS"


class TestDiscovery:
    """目录级发现：混合命名、干扰文件、子目录、gz。"""

    def test_mixed_naming_all_found(self, tmp_path):
        """五种各不相同（且都不规范）的命名应被一次性全部找出。"""
        _write_table(tmp_path, "UPF1 KD vs ctrl_SE.MATS.JCEC.txt", "SE")
        _write_table(tmp_path, "UPF1_KD_vs_ctrl_A3SS.MATS.JCEC.txt", "A3SS")
        _write_table(tmp_path, "A5SS.MATS.JCEC.txt", "A5SS")
        _write_table(tmp_path, "compare_1_MXE.MATS.JCEC.txt", "MXE")
        _write_table(tmp_path, "ri.mats.jc.txt", "RI")
        found = discover_rmats_tables(tmp_path)
        assert set(found) == {"SE", "A3SS", "A5SS", "MXE", "RI"}
        assert found["RI"].path.name == "ri.mats.jc.txt"

    def test_ignores_non_rmats_files(self, tmp_path):
        """日志与普通文本即使名字里带 SE/MXE 也不能被当成数据表。"""
        _write_table(tmp_path, "SE.MATS.JC.txt", "SE")
        (tmp_path / "run.log").write_text("SE MXE RI analysis log\n", encoding="utf-8")
        (tmp_path / "notes_SE.txt").write_text("mentions SE and MXE\n", encoding="utf-8")
        found = discover_rmats_tables(tmp_path)
        assert set(found) == {"SE"}

    def test_prefers_jc_over_jcec(self, tmp_path):
        """同一事件既有 JC 又有 JCEC 时优先 JC（与 rMATS 官方推荐一致）。"""
        _write_table(tmp_path, "SE.MATS.JCEC.txt", "SE")
        _write_table(tmp_path, "SE.MATS.JC.txt", "SE")
        found = discover_rmats_tables(tmp_path)
        assert found["SE"].count_mode == "JC"

    def test_finds_tables_in_subdirectory(self, tmp_path):
        """结果放在 rmats/ 子目录里也要能找到。"""
        _write_table(tmp_path / "rmats", "SE.MATS.JC.txt", "SE")
        assert is_rmats_directory(tmp_path) is True
        found = discover_rmats_tables(tmp_path)
        assert found["SE"].path.parent.name == "rmats"

    def test_reads_gzip_table(self, tmp_path):
        """压缩存放的表格无需用户先解压。"""
        _write_table(tmp_path, "SE.MATS.JC.txt.gz", "SE", gz=True)
        found = discover_rmats_tables(tmp_path)
        assert set(found) == {"SE"}
        events = parse_rmats_directory(tmp_path, ["s1"], ["s2"])
        assert len(events) == 1
        assert events[0].gene_symbol == "GENEA"


class TestCompatibilityEndToEnd:
    """端到端：不改名、直接 load_dataset 也要拿到完整事件。"""

    def test_load_dataset_with_prefixed_names(self, tmp_path):
        """用带比较组前缀的 JCEC 命名建目录，load_dataset 应正常返回五类事件。"""
        _write_table(tmp_path, "UPF1_KD_vs_ctrl_SE.MATS.JCEC.txt", "SE")
        _write_table(tmp_path, "UPF1_KD_vs_ctrl_A3SS.MATS.JCEC.txt", "A3SS")
        _write_table(tmp_path, "UPF1_KD_vs_ctrl_A5SS.MATS.JCEC.txt", "A5SS")
        _write_table(tmp_path, "UPF1_KD_vs_ctrl_MXE.MATS.JCEC.txt", "MXE")
        _write_table(tmp_path, "UPF1_KD_vs_ctrl_RI.MATS.JCEC.txt", "RI")
        dataset = load_dataset(tmp_path)
        assert len(dataset.events) == 5
        assert dataset.source_format == "rMATS"
        assert {event.event_type for event in dataset.events} == {"SE", "A3SS", "A5SS", "MXE", "RI"}

    def test_single_file_input_infers_type(self, tmp_path):
        """直接把单个文件（而非目录）传给平台时，类型也要能自动判定。"""
        path = _write_table(tmp_path, "whatever_MXE.MATS.JCEC.txt", "MXE")
        assert infer_event_type(path) == "MXE"
        dataset = load_dataset(path)
        assert len(dataset.events) == 1
        assert dataset.events[0].event_type == "MXE"

    def test_uppercase_gene_columns(self, tmp_path):
        """部分封装会把 geneSymbol 写成 GeneSymbol，列名大小写不敏感。"""
        header = _HEADERS["SE"].replace("geneSymbol", "GeneSymbol").replace("chr\t", "Chr\t")
        row = _DATA_ROW["SE"]
        path = tmp_path / "SE.MATS.JC.txt"
        path.write_text(header + "\n" + row + "\n", encoding="utf-8")
        dataset = load_dataset(path)
        assert len(dataset.events) == 1
        assert dataset.events[0].gene_symbol == "GENEA"
        assert dataset.events[0].chromosome == "chr1"
