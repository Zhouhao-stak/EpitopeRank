# -*- coding: utf-8 -*-
"""从 rMATS 事件坐标重建 CDS 对照表（ORF 重建）。

背景
----
``epitoperank/peptide/pipeline.py`` 明确「从不重建 ORF」，肽预测依赖外部提供的
``event_id / reference_cds / altered_cds / junction_nt`` 四列表。本模块把这一步
收进平台内部：读原始 rMATS 表 → 参考转录本结构 → 组装参考/异常 CDS → 落表。

参考源
------
* ``ensembl``（默认，联网）：Ensembl REST 取转录本、CDS 区段与基因组序列，
  结果落磁盘缓存；无需下载 GB 级基因组。基因组版本由 REST 返回的
  ``assembly_name`` 记录到 manifest。
* ``local``（离线，可复现）：本地 GTF + FASTA（自动建立 .fai 索引）。

支持的事件
----------
* **SE**：参考 CDS = 含盒式外显子的转录本 CDS；异常 CDS = 删去该外显子；
  ``junction_nt`` = 连接点前的 CDS 核苷酸数。
* **RI**：参考 CDS = 正常 CDS；异常 CDS = 在外显子边界插入保留内含子序列。
* A3SS / A5SS / MXE 因需要更复杂的转录本选择，本版本明确记为
  ``unsupported_event_type`` 并跳过，不做猜测。

科学边界：坐标必须与参考基因组版本一致；只保证所提供转录本的读码框，
不证明该转录本就是样本里实际表达的异构体。产出仍属探索性候选。
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from epitoperank.splicing.parsers.rmats import discover_rmats_tables

COMPLEMENT = str.maketrans("ACGTNacgtn", "TGCANtgcan")
STOP_CODONS = ("TAA", "TAG", "TGA")
CODON_TABLE = dict(zip(
    (a + b + c for a in "TCAG" for b in "TCAG" for c in "TCAG"),
    "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG",
))
ENSEMBL = "https://rest.ensembl.org"
CDS_FIELDS = ("event_id", "reference_cds", "altered_cds", "junction_nt")


def _revcomp(seq: str) -> str:
    """返回 DNA 序列的反向互补（未知碱基保留为 N）。"""
    return seq.translate(COMPLEMENT)[::-1]


def _clean_seq(seq: str) -> str:
    """把序列统一成大写 A/C/G/T/N，去掉空白与数字。"""
    return re.sub(r"[^ACGTNacgtn]", "", seq).upper()


def _cache_path(cache_dir: Path, url: str) -> Path:
    """按 URL 生成稳定的缓存文件名。"""
    return cache_dir / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".txt")


def _http(url: str, *, timeout: float = 40.0, cache_dir: Path | None = None,
          retries: int = 3) -> str:
    """直连（绕过本机代理）取文本，带磁盘缓存与重试。"""
    cached = _cache_path(cache_dir, url) if cache_dir else None
    if cached and cached.is_file():
        return cached.read_text(encoding="utf-8")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    opener.addheaders = [("Content-Type", "application/json"),
                         ("User-Agent", "EpitopeRank-ORFBuilder/1.0")]
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with opener.open(url, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", "replace")
            if cached:
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_text(text, encoding="utf-8")
            time.sleep(0.15)
            return text
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"参考数据请求失败: {url} ({last})")


# ---------------------------------------------------------------------------
# 参考源
# ---------------------------------------------------------------------------
class ReferenceProvider:
    """转录本结构与基因组序列的最小接口。"""

    def transcripts(self, chrom: str, start: int, end: int, strand: int,
                    gene_id: str) -> list[dict[str, Any]]:
        """返回覆盖事件的蛋白编码转录本列表（含 id/start/end/strand/gene_id）。"""
        raise NotImplementedError

    def cds_segments(self, transcript: dict[str, Any]) -> list[dict[str, Any]]:
        """返回一个转录本的全部 CDS 区段：start/end/phase/strand，1-based 闭区间。"""
        raise NotImplementedError

    def sequence(self, chrom: str, start: int, end: int) -> str:
        """返回参考基因组正链的 1-based 闭区间序列。"""
        raise NotImplementedError

    def assembly(self) -> str:
        """返回基因组版本声明，写进 manifest。"""
        raise NotImplementedError


class EnsemblReference(ReferenceProvider):
    """Ensembl REST 在线参考源（GRCh38 / human）。结果缓存到磁盘。"""

    def __init__(self, species: str = "human", cache_dir: Path | None = None,
                 timeout: float = 20.0) -> None:
        self.species = species
        self.timeout = timeout
        self.cache_dir = cache_dir
        self._assembly = ""
        self._overlap_cache: dict[str, list[dict[str, Any]]] = {}
        self._cds_by_parent: dict[str, list[dict[str, Any]]] = {}

    def _get(self, url: str) -> str:
        return _http(url, timeout=self.timeout, cache_dir=self.cache_dir)

    def _query(self, region: str, features: Iterable[str]) -> list[dict[str, Any]]:
        query = ";".join(f"feature={f}" for f in features)
        url = (f"{ENSEMBL}/overlap/region/{self.species}/{region}"
               f"?{query};content-type=application/json")
        raw = self._get(url)
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        if not self._assembly and data:
            self._assembly = str(data[0].get("assembly_name") or "")
        return [x for x in data if isinstance(x, dict)]

    @staticmethod
    def _as_segment(row: dict[str, Any]) -> dict[str, Any] | None:
        if row.get("feature_type") != "cds":
            return None
        try:
            phase = int(row.get("phase") or 0)
        except (TypeError, ValueError):
            phase = 0
        return {"start": int(row["start"]), "end": int(row["end"]),
                "phase": phase, "strand": int(row.get("strand") or 1),
                "parent": str(row.get("Parent") or "")}

    def transcripts(self, chrom: str, start: int, end: int, strand: int,
                    gene_id: str) -> list[dict[str, Any]]:
        region = f"{chrom}:{max(1, start - 1500)}-{end + 1500}"
        # 一次请求同时拿转录本与 CDS：REST 返回的是「与区间重叠的转录本」的
        # 全部 CDS 区段，因此可顺带缓存，避免每个转录本再发一次请求。
        rows = self._query(region, ("transcript", "cds"))
        cds = [seg for row in rows if (seg := self._as_segment(row))]
        for seg in cds:
            self._cds_by_parent.setdefault(seg["parent"], []).append(seg)
        out = []
        for row in rows:
            if row.get("feature_type") != "transcript":
                continue
            if row.get("biotype") != "protein_coding":
                continue
            if int(row.get("strand") or 0) != strand:
                continue
            parent = str(row.get("Parent") or "")
            if gene_id and parent and parent.split(".")[0] != gene_id.split(".")[0]:
                continue
            tid = str(row.get("id") or "")
            # 该转录本是否存在与事件外显子重叠的 CDS（= 外显子是否编码）
            hits = self._cds_by_parent.get(tid, [])
            coding = any(min(s["end"], end) - max(s["start"], start) + 1 >= 12
                         for s in hits)
            out.append({
                "id": tid, "start": int(row["start"]), "end": int(row["end"]),
                "strand": int(row["strand"]), "gene_id": parent,
                "chrom": chrom, "coding": coding,
            })
        # 优先选「该外显子确实落在 CDS 内」且跨度较短的转录本
        out.sort(key=lambda t: (not t["coding"], t["end"] - t["start"]))
        return out[:12]

    def cds_segments(self, transcript: dict[str, Any]) -> list[dict[str, Any]]:
        tid = transcript["id"]
        if tid not in self._overlap_cache:
            if tid in self._cds_by_parent:
                # 区域查询里已经是解析后的段（含 parent 键），不能再按 REST 行解析
                parsed = [s for s in self._cds_by_parent[tid] if s["parent"] == tid]
            else:
                url = (f"{ENSEMBL}/overlap/id/{urllib.parse.quote(tid)}"
                       f"?feature=cds;content-type=application/json")
                rows = [x for x in json.loads(self._get(url)) if isinstance(x, dict)]
                parsed = [seg for row in rows if (seg := self._as_segment(row))]
                parsed = [s for s in parsed if s["parent"] == tid]
            self._overlap_cache[tid] = parsed
        segs = [{k: v for k, v in s.items() if k != "parent"}
                for s in self._overlap_cache[tid]]
        segs.sort(key=lambda s: s["start"], reverse=transcript["strand"] < 0)
        return segs

    def sequence(self, chrom: str, start: int, end: int) -> str:
        if end - start > 300_000:
            raise ValueError("单次请求的基因组区间过大（>300kb）")
        url = (f"{ENSEMBL}/sequence/region/{self.species}/"
               f"{chrom}:{start}-{end}:1?content-type=text/plain")
        return _clean_seq(self._get(url))

    def assembly(self) -> str:
        return self._assembly or "Ensembl REST (GRCh38)"


class LocalReference(ReferenceProvider):
    """本地 GTF + FASTA 参考源；FASTA 需带 .fai（无则自动建立）。"""

    def __init__(self, gtf: Path, fasta: Path) -> None:
        self.gtf = Path(gtf)
        self.fasta = Path(fasta)
        if not self.gtf.is_file() or not self.fasta.is_file():
            raise FileNotFoundError("本地参考需要同时提供 GTF 与 FASTA 文件")
        self._cds: dict[str, list[dict[str, Any]]] = {}
        self._meta: dict[str, dict[str, Any]] = {}
        self._fai: dict[str, tuple[int, int, int, int]] = {}
        self._load_gtf()
        self._load_fai()

    @staticmethod
    def _attr(text: str, key: str) -> str:
        match = re.search(rf'{key}\s+"([^"]+)"', text)
        return match.group(1) if match else ""

    def _opener(self, path: Path):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace") \
            if path.suffix == ".gz" else path.open("r", encoding="utf-8", errors="replace")

    def _load_gtf(self) -> None:
        with self._opener(self.gtf) as fh:
            for line in fh:
                if not line or line.startswith("#"):
                    continue
                cols = line.rstrip("\n").split("\t")
                if len(cols) < 9 or cols[2] != "CDS":
                    continue
                tid = self._attr(cols[8], "transcript_id")
                if not tid:
                    continue
                try:
                    start, end = int(cols[3]), int(cols[4])
                    strand = 1 if cols[6] == "+" else -1
                    phase = 0 if cols[7] == "." else int(cols[7])
                except (ValueError, IndexError):
                    continue
                self._cds.setdefault(tid, []).append(
                    {"start": start, "end": end, "phase": phase, "strand": strand})
                self._meta[tid] = {
                    "id": tid, "start": start, "end": end, "strand": strand,
                    "gene_id": self._attr(cols[8], "gene_id"), "chrom": cols[0],
                }
        for tid, segs in self._cds.items():
            segs.sort(key=lambda s: s["start"], reverse=self._meta[tid]["strand"] < 0)
            meta = self._meta[tid]
            meta["start"] = min(s["start"] for s in segs)
            meta["end"] = max(s["end"] for s in segs)
            meta["chrom"] = self._meta[tid].get("chrom", "")

    def _load_fai(self) -> None:
        index = Path(str(self.fasta) + ".fai")
        if not index.is_file():
            self._build_fai(index)
        with index.open("r", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 5:
                    self._fai[parts[0]] = (int(parts[1]), int(parts[2]),
                                           int(parts[3]), int(parts[4]))

    def _build_fai(self, index: Path) -> None:
        """流式扫描 FASTA 生成 .fai（name, length, offset, linebases, linewidth）。"""
        records = []
        with self.fasta.open("rb") as fh:
            name, offset, length, line_bases, line_width = "", 0, 0, 0, 0
            pos = 0
            for raw in fh:
                if raw.startswith(b">"):
                    if name:
                        records.append((name, length, offset, line_bases, line_width))
                    name = raw[1:].split()[0].decode("ascii", "replace")
                    offset = pos + len(raw)
                    length = 0
                    line_bases = line_width = 0
                else:
                    chunk = raw.strip()
                    if not line_bases:
                        line_bases = len(chunk)
                        line_width = len(raw)
                    length += len(chunk)
                pos += len(raw)
            if name:
                records.append((name, length, offset, line_bases, line_width))
        index.write_text("".join(
            f"{n}\t{l}\t{o}\t{b}\t{w}\n" for n, l, o, b, w in records),
            encoding="utf-8")

    def transcripts(self, chrom: str, start: int, end: int, strand: int,
                    gene_id: str) -> list[dict[str, Any]]:
        out = []
        for tid, meta in self._meta.items():
            if meta["strand"] != strand or meta["chrom"].lstrip("chr") != chrom.lstrip("chr"):
                continue
            if meta["end"] < start or meta["start"] > end:
                continue
            if gene_id and meta["gene_id"] and gene_id not in (meta["gene_id"], ""):
                # 允许版本后缀差异（ENSG00000140105 vs ENSG00000140105.13）
                if meta["gene_id"].split(".")[0] != gene_id.split(".")[0]:
                    continue
            segs = self._cds.get(tid, [])
            coding = any(min(s["end"], end) - max(s["start"], start) + 1 >= 12
                         for s in segs)
            out.append({**meta, "coding": coding})
        out.sort(key=lambda t: (not t["coding"], t["end"] - t["start"]))
        return out[:12]

    def cds_segments(self, transcript: dict[str, Any]) -> list[dict[str, Any]]:
        return list(self._cds.get(transcript["id"], []))

    def sequence(self, chrom: str, start: int, end: int) -> str:
        key = next((k for k in self._fai if k.lstrip("chr") == chrom.lstrip("chr")), None)
        if key is None:
            raise ValueError(f"FASTA 中找不到染色体 {chrom}")
        _, offset, line_bases, line_width = self._fai[key]
        first = offset + (start - 1) // line_bases * line_width + (start - 1) % line_bases
        last = offset + (end - 1) // line_bases * line_width + (end - 1) % line_bases
        with self.fasta.open("rb") as fh:
            fh.seek(first)
            raw = fh.read(max(0, last - first + 1))
        return _clean_seq(raw.decode("ascii", "replace"))

    def assembly(self) -> str:
        return f"local: {self.gtf.name} + {self.fasta.name}"


# ---------------------------------------------------------------------------
# CDS 组装
# ---------------------------------------------------------------------------
@dataclass
class AssembledCDS:
    """一个转录本组装出来的 CDS 及其分段边界。"""

    sequence: str
    segments: list[dict[str, Any]] = field(default_factory=list)

    def segment_offset(self, index: int) -> int:
        """第 index 个 CDS 区段起点在拼接 CDS 中的 0-based 偏移。"""
        return sum(s["length"] for s in self.segments[:index])


def assemble_cds(provider: ReferenceProvider, transcript: dict[str, Any]) -> AssembledCDS:
    """按转录本方向拼接所有 CDS 区段，处理相位与反向互补。"""
    segs = provider.cds_segments(transcript)
    if not segs:
        return AssembledCDS("", [])
    chrom = transcript["chrom"]
    span_start = min(s["start"] for s in segs)
    span_end = max(s["end"] for s in segs)
    genome = provider.sequence(chrom, span_start, span_end)
    strand = transcript["strand"]
    pieces, meta = [], []
    for seg in segs:
        left = seg["start"] - span_start
        right = seg["end"] - span_start + 1
        piece = genome[left:right]
        if len(piece) != seg["end"] - seg["start"] + 1:
            raise ValueError("参考序列长度与 CDS 区段不符")
        if strand < 0:
            piece = _revcomp(piece)
        pieces.append(piece)
        meta.append({**seg, "length": len(piece),
                     "genomic_start": seg["start"], "genomic_end": seg["end"]})
    # GTF phase：首个 CDS 区段 5' 端需去掉 phase 个碱基才能落在完整密码子上
    first_phase = int(meta[0].get("phase") or 0) % 3
    if first_phase:
        pieces[0] = pieces[0][first_phase:]
        meta[0] = {**meta[0], "length": len(pieces[0])}
    seq = "".join(pieces)
    # 从第一个 ATG 开始，保证是蛋白编码起点；同步修正各区段在拼接 CDS 中的长度
    atg = seq.find("ATG")
    if atg > 0:
        seq = seq[atg:]
        left = atg
        for item in meta:
            cut = min(left, item["length"])
            item["length"] -= cut
            left -= cut
            if left <= 0:
                break
    return AssembledCDS(seq, meta)


def _protein(seq: str) -> str:
    """翻译到首个终止密码子（与 neoantigen.translate 语义一致）。"""
    if len(seq) % 3 or set(seq) - set("ACGT"):
        return ""
    aa = "".join(CODON_TABLE[seq[i:i + 3]] for i in range(0, len(seq), 3))
    return aa.split("*", 1)[0]


def _peptide_possible(ref: str, alt: str, junction: int) -> bool:
    """连接点两侧能否产生至少一条 8–11mer 且不存在于参考 ORF 的肽。"""
    if not (1 <= junction < len(alt)):
        return False
    reference, altered = _protein(ref), _protein(alt)
    left_aa = (junction - 1) // 3
    right_aa = junction // 3
    if right_aa >= len(altered):
        return False
    for length in (8, 9, 10, 11):
        lo = max(0, right_aa - length + 1)
        hi = min(left_aa, len(altered) - length)
        for start in range(lo, hi + 1):
            peptide = altered[start:start + length]
            if len(peptide) == length and peptide not in reference:
                return True
    return False


def _trim_codons(seq: str) -> str:
    """去掉末尾不完整密码子，保证 translate() 不会因长度报错。"""
    return seq[:len(seq) // 3 * 3]


def _match_segment(segments: list[dict[str, Any]], start: int, end: int,
                   min_overlap: int = 12) -> int:
    """找出与给定基因组区间重叠最多的 CDS 区段下标，找不到返回 -1。"""
    best, best_hit = -1, 0
    for i, seg in enumerate(segments):
        hit = min(seg["genomic_end"], end) - max(seg["genomic_start"], start) + 1
        if hit > best_hit:
            best, best_hit = i, hit
    return best if best_hit >= min_overlap else -1


def _read_rows(path: Path) -> list[dict[str, str]]:
    """读 rMATS 表（支持 .gz），列名统一小写。"""
    opener = gzip.open(path, "rt", encoding="utf-8-sig", errors="replace") \
        if path.suffix == ".gz" else path.open("r", encoding="utf-8-sig", errors="replace")
    with opener as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        rows = []
        for row in reader:
            rows.append({str(k).strip().lower(): str(v or "").strip()
                         for k, v in row.items() if k is not None})
        return rows


def _num(row: dict[str, str], *keys: str) -> float:
    for key in keys:
        try:
            return float(row.get(key, ""))
        except (TypeError, ValueError):
            continue
    return float("nan")


def _select_events(input_dir: Path, *, event_ids: list[str] | None,
                   fdr_max: float, min_abs_dpsi: float, max_events: int) -> list[dict[str, Any]]:
    """从原始 rMATS 表筛选显著事件，返回带完整坐标信息的记录。"""
    tables = discover_rmats_tables(input_dir, max_depth=2)
    wanted = set(event_ids or [])
    found: list[dict[str, Any]] = []
    for event_type, table in tables.items():
        for row in _read_rows(table.path):
            raw_id = row.get("id", "")
            eid = f"{event_type}:{raw_id}"
            if wanted and eid not in wanted:
                continue
            fdr, dpsi = _num(row, "fdr"), _num(row, "incleveldifference")
            if fdr == fdr and fdr > fdr_max:
                continue
            if dpsi == dpsi and abs(dpsi) < min_abs_dpsi:
                continue
            if dpsi != dpsi or fdr != fdr:
                continue
            found.append({
                "event_id": eid, "event_type": event_type,
                "gene_id": row.get("geneid", ""), "gene_symbol": row.get("genesymbol", ""),
                "chrom": row.get("chr", ""), "strand": row.get("strand", ""),
                "fdr": fdr, "delta_psi": dpsi, "row": row,
                "support": _num(row, "ijc_sample_1", "ijc_sample_2") or 0.0,
            })
    found.sort(key=lambda e: (abs(e["delta_psi"]), e["support"]), reverse=True)
    return found[:max_events]


def _build_one(event: dict[str, Any], provider: ReferenceProvider) -> dict[str, Any]:
    """为单个事件重建 CDS 对，返回结果字典（含 reason 时表示跳过）。"""
    etype = event["event_type"]
    if etype not in {"SE", "RI"}:
        return {"reason": "unsupported_event_type"}
    row, strand = event["row"], (1 if event["strand"] == "+" else -1)
    chrom = event["chrom"].replace("chr", "")
    try:
        if etype == "SE":
            exon_start = int(float(row["exonstart_0base"])) + 1
            exon_end = int(float(row["exonend"]))
        else:
            exon_start = int(float(row["riexonstart_0base"])) + 1
            exon_end = int(float(row["riexonend"]))
    except (KeyError, ValueError):
        return {"reason": "missing_coordinates"}
    transcripts = provider.transcripts(chrom, exon_start, exon_end, strand, event["gene_id"])
    if not transcripts:
        return {"reason": "no_coding_transcript"}
    if etype == "SE" and not any(t.get("coding") for t in transcripts):
        # 盒式外显子落在 UTR：坐标能重建转录本结构，但不改变蛋白序列
        return {"reason": "exon_not_coding"}
    # 控制单个事件的外部请求量：只试前若干个最相关的转录本，
    # 并跳过跨度过大的转录本（一次序列请求最多 300kb）。
    candidates = [t for t in transcripts if t["end"] - t["start"] <= 200_000][:4]
    for transcript in candidates:
        try:
            assembled = assemble_cds(provider, transcript)
        except (ValueError, KeyError, RuntimeError):
            continue
        if not assembled.sequence.startswith("ATG"):
            continue
        if etype == "SE":
            idx = _match_segment(assembled.segments, exon_start, exon_end)
            if idx < 0:
                continue
            seg = assembled.segments[idx]
            offset = assembled.segment_offset(idx)
            ref = assembled.sequence
            alt = ref[:offset] + ref[offset + seg["length"]:]
            junction = offset
            if seg["length"] % 3:  # 盒式外显子非整码子 → 移码，仍记录
                frame = "frameshift"
            else:
                frame = "in_frame"
        else:
            # RI：保留内含子 = upstreamEE+1 .. downstreamES-1，插在两个 CDS 区段之间
            try:
                intron_start = int(float(row["upstreamee"])) + 1
                intron_end = int(float(row["downstreames"])) - 1
            except (KeyError, ValueError):
                return {"reason": "missing_coordinates"}
            if intron_end <= intron_start or intron_end - intron_start > 20_000:
                return {"reason": "invalid_intron_length"}
            segs = assembled.segments
            idx = next((i for i, s in enumerate(segs)
                        if s["genomic_end"] < intron_start
                        and i + 1 < len(segs)
                        and segs[i + 1]["genomic_start"] > intron_end), -1)
            if idx < 0:
                continue
            offset = assembled.segment_offset(idx) + segs[idx]["length"]
            intron = provider.sequence(chrom, intron_start, intron_end)
            if strand < 0:
                intron = _revcomp(intron)
            ref = assembled.sequence
            alt = ref[:offset] + intron + ref[offset:]
            junction = offset
            frame = "frameshift" if len(intron) % 3 else "in_frame"
        # translate() 要求整码子；截掉末尾不完整密码子不改变上游读码框
        ref, alt = _trim_codons(ref), _trim_codons(alt)
        if not _peptide_possible(ref, alt, junction):
            continue
        return {
            "event_id": event["event_id"], "reference_cds": ref,
            "altered_cds": alt, "junction_nt": junction,
            "transcript_id": transcript["id"], "frame_status": frame,
            "gene_symbol": event["gene_symbol"], "delta_psi": event["delta_psi"],
            "fdr": event["fdr"],
        }
    return {"reason": "no_reconstructable_orf"}


def build_orf_table(input_dir: Path, output: Path, *, provider: ReferenceProvider,
                    event_ids: list[str] | None = None, fdr_max: float = 0.05,
                    min_abs_dpsi: float = 0.1, max_events: int = 25,
                    time_budget: float = 180.0) -> dict[str, Any]:
    """从 rMATS 表重建 CDS 对照表，并返回可审计的构建摘要。

    :param input_dir: 含 rMATS 事件表的项目数据目录。
    :param output: 输出的 CDS 表路径（通常项目目录下的 ``splice_orfs.tsv``）。
    :param provider: 参考源实例。
    :param event_ids: 只处理指定事件 ID；为空时按 |ΔPSI| 取前 ``max_events`` 个。
    :param fdr_max: FDR 上限。
    :param min_abs_dpsi: |ΔPSI| 下限。
    :param max_events: 最多处理多少个事件（控制外部请求量）。
    """
    input_dir, output = Path(input_dir), Path(output)
    events = _select_events(input_dir, event_ids=event_ids, fdr_max=fdr_max,
                            min_abs_dpsi=min_abs_dpsi, max_events=max_events)
    rows, skipped = [], []
    started = time.monotonic()
    for index, event in enumerate(events):
        if time.monotonic() - started > time_budget:
            skipped.extend({"event_id": e["event_id"], "reason": "time_budget_exceeded"}
                           for e in events[index:])
            break
        try:
            result = _build_one(event, provider)
        except Exception as exc:  # noqa: BLE001 - 单事件失败不影响整批
            skipped.append({"event_id": event["event_id"], "reason": f"error: {exc}"})
            continue
        if "reason" in result:
            skipped.append({"event_id": event["event_id"], "reason": result["reason"]})
            continue
        rows.append(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(CDS_FIELDS)
        for row in rows:
            writer.writerow([row[k] for k in CDS_FIELDS])
    manifest = {
        "input_dir": str(input_dir), "output": str(output),
        "reference": provider.assembly(),
        "genome_build": provider.assembly(),
        "event_count": len(events), "written": len(rows), "skipped": skipped,
        "filters": {"fdr_max": fdr_max, "min_abs_dpsi": min_abs_dpsi,
                    "max_events": max_events, "time_budget": time_budget,
                    "event_ids": event_ids or []},
        "supported_event_types": ["SE", "RI"],
        "limitations": [
            "只重建所选参考转录本的读码框，不证明该转录本在样本中实际表达。",
            "事件坐标必须与参考基因组版本一致；版本不匹配时结果无效。",
            "A3SS/A5SS/MXE 本版本不重建，直接跳过并记录原因。",
            "输出为探索性候选 CDS，仍需表达证据、正常组织过滤与实验验证。",
        ],
        "provenance": [
            {"event_id": r["event_id"], "gene_symbol": r.get("gene_symbol", ""),
             "transcript_id": r.get("transcript_id", ""),
             "frame_status": r.get("frame_status", ""),
             "junction_nt": r["junction_nt"],
             "reference_cds_length": len(r["reference_cds"]),
             "altered_cds_length": len(r["altered_cds"])} for r in rows
        ],
    }
    Path(str(output) + ".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
