"""新增能力的单元测试：ORF 重建、结合分级、外网工具、MCP 扩展与模型规划。

全部使用假参考源 / 假模型 / 假 opener，不依赖网络与真实基因组。
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from epitoperank.agent.decision import DecisionEngine
from epitoperank.mcp.client import MCPClient
from epitoperank.neoantigen import junction_peptides
from epitoperank.peptide.binding_tiers import (
    classify, rank_predictions, tier_summary, write_ranked)
from epitoperank.splicing.orf_builder import (
    ReferenceProvider, _peptide_possible, _revcomp, _trim_codons,
    assemble_cds, build_orf_table)
from epitoperank import web_fetch


# ---------------------------------------------------------------------------
# ORF 重建
# ---------------------------------------------------------------------------
SEG1 = "ATG" + "GCT" * 9          # 30 nt: M + 9*A
CASSETTE = "TGG" * 10             # 30 nt: 10*W
SEG3 = "AAG" * 20                 # 60 nt: 20*K
GENOME = SEG1 + "C" * 30 + CASSETTE + "C" * 30 + SEG3 + "C" * 20


class FakeProvider(ReferenceProvider):
    """三个 CDS 区段的微型参考基因组，中间那段是可跳过的盒式外显子。"""

    def transcripts(self, chrom, start, end, strand, gene_id):
        return [{"id": "TX1", "start": 1, "end": 180, "strand": 1,
                 "gene_id": gene_id, "chrom": chrom, "coding": True}]

    def cds_segments(self, transcript):
        return [
            {"start": 1, "end": 30, "phase": 0, "strand": 1},
            {"start": 61, "end": 90, "phase": 0, "strand": 1},
            {"start": 121, "end": 180, "phase": 0, "strand": 1},
        ]

    def sequence(self, chrom, start, end):
        return GENOME[start - 1:end]

    def assembly(self):
        return "fake-genome-v1"


def test_revcomp_and_codon_trim() -> None:
    assert _revcomp("ATGC") == "GCAT"
    assert _trim_codons("ATGGCCT") == "ATGGCCT"[:6]


def test_assemble_cds_keeps_frame_and_offsets() -> None:
    provider = FakeProvider()
    cds = assemble_cds(provider, provider.transcripts("1", 61, 90, 1, "G1")[0])
    assert cds.sequence.startswith("ATG")
    assert len(cds.sequence) == 120
    assert cds.segment_offset(1) == 30
    assert _peptide_possible(cds.sequence, cds.sequence[:30] + cds.sequence[60:], 30)


def _write_rmats_table(directory: Path) -> None:
    header = [
        "ID", "GeneID", "geneSymbol", "chr", "strand",
        "exonStart_0base", "exonEnd", "upstreamES", "upstreamEE",
        "downstreamES", "downstreamEE", "IJC_SAMPLE_1", "SJC_SAMPLE_1",
        "IJC_SAMPLE_2", "SJC_SAMPLE_2", "IncFormLen", "SkipFormLen",
        "PValue", "FDR", "IncLevel1", "IncLevel2", "IncLevelDifference",
    ]
    row = ["1", "ENSG_FAKE", "GENE1", "1", "+", "60", "90", "1", "30",
           "121", "180", "10", "1", "1", "10", "100", "100",
           "0.0001", "0.001", "0.1,0.1", "0.9,0.9", "0.8"]
    with (directory / "SE.MATS.JC.txt").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerow(row)


def test_build_orf_table_produces_peptide_ready_cds(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _write_rmats_table(source)
    output = source / "splice_orfs.tsv"
    manifest = build_orf_table(source, output, provider=FakeProvider(), max_events=3)
    assert manifest["written"] == 1
    assert manifest["genome_build"] == "fake-genome-v1"
    assert (source / "splice_orfs.tsv.manifest.json").is_file()
    with output.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    assert rows[0]["event_id"] == "SE:1"
    assert rows[0]["junction_nt"] == "30"
    assert junction_peptides(rows[0]["reference_cds"],
                             rows[0]["altered_cds"], 30)


# ---------------------------------------------------------------------------
# 结合分级
# ---------------------------------------------------------------------------
def test_binding_tiers_classify_and_rank() -> None:
    assert classify("0.01")[0] == "strong"
    assert classify("1.2")[0] == "weak"
    assert classify("8")[0] == "none"
    assert classify("n/a")[0] == "unknown"
    scores = [
        {"peptide": "P1", "allele": "HLA-A*02:01", "percentile_rank": "1.2", "score": "0.2"},
        {"peptide": "P2", "allele": "HLA-A*02:01", "percentile_rank": "0.1", "score": "0.9"},
        {"peptide": "P3", "allele": "HLA-B*07:02", "percentile_rank": "9", "score": "0.01"},
    ]
    candidates = [{"peptide": "P2", "event_id": "SE:2", "gene_symbol": "G2",
                   "fdr": "0.001", "delta_psi": "0.5"}]
    rows = rank_predictions(scores, candidates)
    assert rows[0]["peptide"] == "P2" and rows[0]["binding_tier"] == "strong"
    assert rows[0]["event_id"] == "SE:2"
    summary = tier_summary(rows)
    assert (summary["strong_count"], summary["weak_count"], summary["total"]) == (1, 1, 3)


def test_write_ranked_roundtrip(tmp_path: Path) -> None:
    rows = rank_predictions(
        [{"peptide": "P", "allele": "A", "percentile_rank": "0.2", "score": "0.8"}], [])
    path = write_ranked(tmp_path / "ranked_candidates.tsv", rows)
    with path.open(encoding="utf-8") as fh:
        saved = list(csv.DictReader(fh, delimiter="\t"))
    assert saved[0]["binding_tier"] == "strong"
    assert saved[0]["rank"] == "1"


# ---------------------------------------------------------------------------
# 外网工具与 MCP
# ---------------------------------------------------------------------------
def test_web_fetch_rejects_non_whitelisted_domain() -> None:
    result = web_fetch.fetch_url("https://evil.example.com/data")
    assert result["ok"] is False
    assert "not allowed" in result["error"]


def test_web_fetch_reads_whitelisted_url(monkeypatch) -> None:
    class FakeResponse:
        status = 200
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            return b'{"hello": "world"}'

    class FakeOpener:
        addheaders = []

        def open(self, url, timeout=None):
            return FakeResponse()

    monkeypatch.setattr(web_fetch.urllib.request, "build_opener", lambda *a: FakeOpener())
    result = web_fetch.fetch_url("https://rest.ensembl.org/info/ping")
    assert result["ok"] is True
    assert json.loads(result["text"]) == {"hello": "world"}


def test_mcp_add_and_remove_external_server(tmp_path: Path) -> None:
    client = MCPClient(config_dir=tmp_path)
    client.add_server(name="remote-tools", url="https://example.org/mcp", transport="http")
    assert "remote-tools" in client.servers
    saved = json.loads((tmp_path / "servers.json").read_text(encoding="utf-8"))
    assert saved["servers"][0]["url"] == "https://example.org/mcp"
    assert client.remove_server("remote-tools") is True
    assert not any(s["name"] == "remote-tools" for s in json.loads(
        (tmp_path / "servers.json").read_text(encoding="utf-8"))["servers"])
    with pytest.raises(ValueError):
        client.add_server(name="x", url="ftp://bad")


# ---------------------------------------------------------------------------
# 自主规划
# ---------------------------------------------------------------------------
class _FakeState:
    facts = {"filtered": True, "ranked": True}
    issues: list = []
    params: dict = {}
    action_counts: dict = {}
    steps: list = []

    def count_of(self, action):
        return 0


def test_model_planning_uses_full_registry(monkeypatch) -> None:
    captured = {}

    class FakeEnhancer:
        def __init__(self, settings):
            pass

        def complete(self, **kwargs):
            captured["prompt"] = kwargs["user"]
            return json.dumps({"action": "web_fetch",
                               "args": {"url": "https://rest.ensembl.org/x"},
                               "rationale": "fetch reference data"})

    monkeypatch.setattr("epitoperank.llm.enrich.LLMEnhancer", FakeEnhancer)
    settings = SimpleNamespace(
        llm=SimpleNamespace(usable=True),
        agent=SimpleNamespace(autonomous_planning=True, plan_budget=8,
                              allow_network=True, allow_file_write=True))
    engine = DecisionEngine(_FakeState(), settings, llm_advisory=False)
    decision = engine._model_plan(["reported"])
    assert decision is not None
    assert decision.source == "llm" and decision.action == "web_fetch"
    assert decision.args == {"url": "https://rest.ensembl.org/x"}
    # 报告类动作在证据不足时不得出现在给模型的候选里
    assert '"generate_report"' not in captured["prompt"]
    assert "rebuild_orf_table" in captured["prompt"]


def test_model_planning_can_be_switched_off(monkeypatch) -> None:
    settings = SimpleNamespace(
        llm=SimpleNamespace(usable=True),
        agent=SimpleNamespace(autonomous_planning=False, plan_budget=8,
                              allow_network=True, allow_file_write=True))
    engine = DecisionEngine(_FakeState(), settings, llm_advisory=False)
    assert engine._model_plan(["reported"]) is None
