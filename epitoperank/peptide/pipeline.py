"""End-to-end peptide prediction pipeline.

Inputs can be either

* splicing events plus an externally reconstructed CDS table
  (``event_id, reference_cds, altered_cds, junction_nt``) — the same contract
  as the neoantigen module, or
* an existing peptide table / FASTA, when peptides were generated elsewhere.

The pipeline never reconstructs ORFs from coordinates.  It translates only the
supplied frame-correct CDS, keeps peptides that cross the novel junction, and
records every assumption in ``manifest.json``.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from epitoperank.neoantigen import (CDS_FIELDS, canonical_cds_fields, decode_table_text,
                                   junction_peptides, sniff_delimiter, translate)

from . import properties
from .filters import SelfFilterResult, scan_proteomes
from .hla import HlaAllele, parse_panel, split_by_class
from .iedb import DEFAULT_METHODS, IedbClient, IedbError, METHODS
from .scoring import DEFAULT_WEIGHTS, describe as describe_scoring, rank as rank_rows
from .sequences import MHC_I_LENGTHS, file_sha256, normalize_peptide, unique

PEPTIDE_FIELDS = [
    "event_id", "gene_id", "gene_symbol", "event_type", "fdr", "delta_psi",
    "peptide", "length", "start_aa", "junction_aa", "orf_source", "frame_status",
    "molecular_weight_da", "isoelectric_point", "net_charge_ph7", "gravy",
    "aromaticity", "aliphatic_index", "hydrophobic_fraction", "shannon_entropy",
    "low_complexity", "p2", "p_omega", "self_hit", "self_hit_proteins",
    "novelty_status",
]
PREDICTION_FIELDS = [
    "peptide", "allele", "mhc_class", "method", "method_label", "score",
    "percentile_rank", "core", "proteasome_score", "tap_score", "total_score",
    "processing_score", "mhcnp_probability", "source", "request_id", "raw_json",
]
RANKED_FIELDS = [
    "rank", "peptide", "length", "event_id", "gene_symbol", "event_type",
    "fdr", "delta_psi", "best_allele", "percentile_rank", "mhc_class2_allele",
    "mhc_class2_percentile", "processing_total_score", "evidence_tier",
    "composite_score", "components_used", "self_hit",
]

LIMITATIONS = [
    "候选肽来自上游提供的 frame-correct 参考/异常 CDS；平台不从剪接坐标重建 ORF。",
    "MHC 结合预测不等于抗原呈递、不等于免疫原性、不等于临床有效性。",
    "IEDB 输出的是 percentile rank（百分位排名），不是实测亲和力 Kd。",
    "novelty 只在所提供的正常蛋白序列范围内成立，缺失不代表肿瘤特异。",
    "MHC-II 预测使用含侧翼序列的窗口，模型报告的是 9-mer core 的排名。",
    "缺少 HLA 免疫肽组质谱与实验验证时，不能声称肽被呈递或具有免疫原性。",
    "复现率与表达量仅作为排序权重，未设为硬门槛。",
]


@dataclass
class PeptideOptions:
    """Everything that influences a peptide run (serialised into the manifest)."""

    alleles: list[str] = field(default_factory=list)
    mhc_class: str = "both"  # class1 | class2 | both
    predictor: str = "iedb"  # iedb | local | auto | none
    methods: dict[int, str] = field(default_factory=lambda: dict(DEFAULT_METHODS))
    processing: bool = True
    stability: bool = False
    mhcnp: bool = False
    lookup_epitopes: bool = False
    self_fastas: list[str] = field(default_factory=list)
    lengths: tuple[int, ...] = MHC_I_LENGTHS
    class2_window: int = 15
    max_predictions: int = 2000
    max_lookup: int = 25
    cache: bool = True
    cache_dir: str | None = None

    def as_dict(self) -> dict[str, object]:
        """把运行参数序列化为字典，写入 manifest 以便复现。"""
        return {
            "alleles": list(self.alleles),
            "mhc_class": self.mhc_class,
            "predictor": self.predictor,
            "methods": {str(key): value for key, value in self.methods.items()},
            "processing": self.processing,
            "stability": self.stability,
            "mhcnp": self.mhcnp,
            "lookup_epitopes": self.lookup_epitopes,
            "self_fastas": list(self.self_fastas),
            "lengths": list(self.lengths),
            "class2_window": self.class2_window,
            "max_predictions": self.max_predictions,
            "max_lookup": self.max_lookup,
            "cache": self.cache,
        }

    def validate(self) -> None:
        """校验 MHC 类别、预测器、II 类窗口与等位基因名，非法时抛 ValueError。"""
        if self.mhc_class not in {"class1", "class2", "both"}:
            raise ValueError("mhc_class must be class1, class2 or both")
        if self.predictor not in {"iedb", "local", "auto", "none"}:
            raise ValueError("predictor must be iedb, local, auto or none")
        if not 11 <= int(self.class2_window) <= 30:
            raise ValueError("class2_window must be 11-30")
        if self.alleles:
            parse_panel(self.alleles, allow_mixed_classes=self.mhc_class == "both")
        elif self.predictor != "none":
            raise ValueError("provide at least one HLA allele for prediction")


def _now() -> str:
    """当前 UTC 时间（秒级 ISO 字符串），用作运行时间戳。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(value: object) -> object:
    """去除字符串首尾空白，其他类型原样返回。"""
    if isinstance(value, str):
        return value.strip()
    return value


def _float_or_none(value: object) -> float | None:
    """把输入转为浮点数，无法转换或为 NaN 时返回 None。"""
    try:
        result = float(str(value))
    except (TypeError, ValueError):
        return None
    return result if result == result else None


# ----------------------------------------------------------------------
# Candidate collection
# ----------------------------------------------------------------------
def _event_metadata(event: object) -> dict[str, object]:
    """从剪接事件对象上提取 event_id、基因、事件类型、FDR 与 ΔPSI 等字段。"""
    return {
        "event_id": getattr(event, "event_id", "") or "",
        "gene_id": getattr(event, "gene_id", "") or "",
        "gene_symbol": getattr(event, "gene_symbol", "") or "",
        "event_type": getattr(event, "event_type", "") or "",
        "fdr": getattr(event, "fdr", None),
        "delta_psi": getattr(event, "delta_psi", None),
    }


# 中文备注：肽预测：辅助处理上下文（参数：protein、start、length、window）
def _context(protein: str, start: int, length: int, window: int) -> str:
    """Centre a class-II window on the peptide, clamped to the protein."""
    if len(protein) <= window:
        return protein
    midpoint = start + length // 2
    left = max(0, midpoint - window // 2)
    right = min(len(protein), left + window)
    left = max(0, right - window)
    return protein[left:right]


# 中文备注：肽预测：辅助处理候选CDS（参数：input_dir、cds_table、lengths、class2_window）
def candidates_from_cds(input_dir: str | Path, cds_table: str | Path, *,
                        lengths: Sequence[int] = MHC_I_LENGTHS,
                        class2_window: int = 15) -> dict[str, object]:
    """Translate supplied CDS pairs and keep junction-crossing peptides."""
    from epitoperank.data.loader import load_dataset

    dataset = load_dataset(input_dir)
    events: dict[str, object] = {}
    duplicated: set[str] = set()
    for event in dataset.events:
        if event.event_id in events:
            duplicated.add(event.event_id)
        events[event.event_id] = event

    candidates: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    table = Path(cds_table)
    text = decode_table_text(table)
    first_line = text.splitlines()[0] if text.strip() else ""
    reader = csv.reader(io.StringIO(text), delimiter=sniff_delimiter(first_line))
    header = next(reader, [])
    columns = canonical_cds_fields(header)
    missing = [name for name in CDS_FIELDS if name not in columns]
    if missing:
        shown = "、".join(str(item).strip() for item in header[:12]) or "（空表头）"
        raise ValueError("CDS table is missing required column(s): " + ", ".join(missing) + f"; header: {shown}")
    position: dict[str, int] = {}
    for offset, name in enumerate(columns):
        position.setdefault(name, offset)

    def cell(row: list[str], name: str) -> str:
        """按列名安全读取当前行的单元格文本，越界时返回空串。"""
        index = position[name]
        return (row[index] if index < len(row) else "").strip()

    for line, row in enumerate(reader, start=2):
        if not any(str(item).strip() for item in row):
            continue
        event_id = cell(row, "event_id")
        if event_id in duplicated:
            skipped.append({"line": line, "event_id": event_id,
                            "reason": "event_id is ambiguous in the event table"})
            continue
        event = events.get(event_id)
        if event is None:
            skipped.append({"line": line, "event_id": event_id, "reason": "event_id not found"})
            continue
        try:
            peptides = junction_peptides(
                cell(row, "reference_cds"), cell(row, "altered_cds"),
                int(cell(row, "junction_nt") or ""),
                lengths=tuple(int(item) for item in lengths),
            )
            protein = translate(cell(row, "altered_cds"))
        except (ValueError, TypeError) as error:
            skipped.append({"line": line, "event_id": event_id, "reason": str(error)})
            continue
        extra = {name: cell(row, name) if name in position else "" for name in ("orf_source", "frame_status")}
        for item in peptides:
            start = int(item["start_aa"]) - 1
            candidates.append({
                **_event_metadata(event),
                "peptide": item["peptide"],
                "length": item["length"],
                "start_aa": item["start_aa"],
                "junction_aa": item["junction_aa"],
                "orf_source": extra["orf_source"].strip() or "supplied_cds",
                "frame_status": extra["frame_status"].strip(),
                "class2_context": _context(protein, start, int(item["length"]), class2_window),
                "altered_protein": protein,
            })
    return {
        "candidates": candidates,
        "skipped": skipped,
        "events": len(dataset.events),
        "input_rows": len(candidates) + len(skipped),
    }


# 中文备注：肽预测：加载肽段表（参数：path）
def load_peptide_table(path: str | Path) -> list[dict[str, object]]:
    """Read a peptide table (TSV/CSV) or a peptide FASTA.

    A table must contain a ``peptide`` column; all other columns are carried
    through as candidate metadata (``event_id``, ``gene_symbol``, ``expression``…).
    """
    path = Path(path)
    if path.suffix.lower() in {".fa", ".fasta", ".faa"}:
        from .sequences import read_fasta

        return [{"peptide": sequence, "record_id": name}
                for name, sequence in read_fasta(path, kind="peptide")]
    delimiter = "," if path.suffix.lower() == ".csv" else "\t"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError(f"peptide table {path.name} has no header")
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        lower = {name.lower(): name for name in reader.fieldnames}
        if "peptide" not in lower:
            raise ValueError("peptide table requires a 'peptide' column")
        rows: list[dict[str, object]] = []
        for row in reader:
            peptide = (row.get(lower["peptide"]) or "").strip()
            if not peptide:
                continue
            item: dict[str, object] = {key: _clean(value) for key, value in row.items()}
            item["peptide"] = normalize_peptide(peptide)
            rows.append(item)
    if not rows:
        raise ValueError(f"peptide table {path.name} contains no peptides")
    return rows


# ----------------------------------------------------------------------
# Prediction
# ----------------------------------------------------------------------
# 中文备注：肽预测：辅助处理客户端（参数：options）
def _client(options: PeptideOptions) -> IedbClient:
    """Build the IEDB client, keeping the default on-disk cache enabled.

    Passing ``cache_dir=None`` explicitly would disable caching entirely
    (dataclass default factories only apply when the field is omitted), which
    turns every API call into a fresh multi-second IEDB request.
    """
    kwargs: dict[str, object] = {
        "cache_read": options.cache,
        "cache_write": options.cache,
    }
    if options.cache_dir:
        kwargs["cache_dir"] = Path(options.cache_dir)
    return IedbClient(**kwargs)  # type: ignore[arg-type]


# 中文备注：肽预测：辅助处理class2contexts（参数：candidates）
def _class2_contexts(candidates: Sequence[dict]) -> tuple[list[str], int]:
    """Collect MHC-II windows long enough for the model (11-30 aa)."""
    contexts = unique([str(item["class2_context"]) for item in candidates
                       if len(str(item.get("class2_context") or "")) >= 11])
    skipped = sum(1 for item in candidates
                  if item.get("class2_context")
                  and len(str(item["class2_context"])) < 11)
    return contexts, skipped


def _run_iedb(candidates: Sequence[dict], alleles: Sequence[HlaAllele],
              options: PeptideOptions, *, class2_length: int | str | None = None) -> dict[str, object]:
    """经 IEDB 联网预测 I/II 类结合（可选加工、稳定性、MHC-NP）。

    ``class2_length`` 覆盖默认的 ``options.class2_window``：CDS/CLI 模式提交的是
    预先截好的窗口，必须用固定长度；裸肽列表（API）传入 ``"asis"``，让 IEDB
    按每条肽的原长返回，否则长肽会被切成 15-mer 窗口而在结果过滤阶段全部丢失。

    每个阶段独立捕获 :class:`IedbError` 并记入 ``errors``，单阶段失败不会
    中断其余阶段；返回预测记录、错误列表与调用记录。
    """
    client = _client(options)
    grouped = split_by_class(list(alleles))
    predictions: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    methods_used: dict[int, str] = {}

    class1 = [str(item["peptide"]) for item in candidates if 8 <= int(item["length"]) <= 11]
    class1 = unique(class1)
    class1_alleles = [item.name for item in grouped[1]]
    class2_alleles = [item.name for item in grouped[2]]

    def attempt(label: str, func, *args, **kwargs) -> None:
        """执行一个预测阶段，把 IedbError 记入 errors 而不中断整体流程。"""
        try:
            predictions.extend(func(*args, **kwargs))
        except IedbError as error:
            errors.append({"stage": label, "error": str(error)[:500]})

    if options.mhc_class in {"class1", "both"} and class1_alleles and class1:
        method = options.methods.get(1, DEFAULT_METHODS[1])
        methods_used[1] = method
        attempt("mhc_i_binding", client.predict_mhci, class1, class1_alleles,
                lengths=options.lengths, method=method)
        if options.processing:
            attempt("mhc_i_processing", client.predict_processing, class1,
                    class1_alleles, lengths=options.lengths)
        if options.stability:
            attempt("mhc_i_stability", client.predict_stability, class1, class1_alleles)
        if options.mhcnp:
            attempt("mhc_np", client.predict_mhcnp, class1, class1_alleles,
                    lengths=options.lengths)

    contexts, short_contexts = _class2_contexts(candidates)
    if options.mhc_class in {"class2", "both"} and class2_alleles and contexts:
        method = options.methods.get(2, DEFAULT_METHODS[2])
        methods_used[2] = method
        attempt("mhc_ii_binding", client.predict_mhcii, contexts, class2_alleles,
                length=class2_length if class2_length is not None else options.class2_window,
                method=method)
    if short_contexts and options.mhc_class in {"class2", "both"}:
        errors.append({"stage": "mhc_ii_binding",
                       "error": f"{short_contexts} 条候选的 MHC-II 上下文短于 11 aa，未提交 II 类预测"})

    return {"predictions": predictions, "errors": errors,
            "methods": methods_used, "calls": list(client.calls)}


def _run_local(candidates: Sequence[dict], alleles: Sequence[HlaAllele]) -> dict[str, object]:
    """用本地 MHCflurry 离线预测 I 类结合，不联网；异常记入 errors。

    仅处理 8-11 aa 的 I 类肽段，II 类不支持时结果中不会出现相应记录。
    """
    from . import local_models

    grouped = split_by_class(list(alleles))
    peptides = unique([str(item["peptide"]) for item in candidates if 8 <= int(item["length"]) <= 11])
    predictions: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    if grouped[1] and peptides:
        try:
            predictions.extend(local_models.predict_mhci(peptides, [item.name for item in grouped[1]]))
        except Exception as error:  # noqa: BLE001 - surfaced to the manifest
            errors.append({"stage": "mhcflurry", "error": str(error)[:500]})
    return {"predictions": predictions, "errors": errors,
            "methods": {1: "mhcflurry_affinity"} if predictions else {}, "calls": []}


# ----------------------------------------------------------------------
# Aggregation
# ----------------------------------------------------------------------
# 中文备注：肽预测：辅助处理best（参数：rows、key、maximize）
def _best(rows: Iterable[dict], key: str, *, maximize: bool = False) -> dict | None:
    """Pick the best row by a numeric key (lower is better unless ``maximize``)."""
    best = None
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        if best is None:
            best = row
            continue
        current = float(best[key])
        candidate = float(value)
        if (candidate > current) if maximize else (candidate < current):
            best = row
    return best


# 中文备注：肽预测：去重predictions（参数：predictions）
def dedupe_predictions(predictions: Sequence[dict]) -> list[dict]:
    """Keep one row per (peptide, allele, method), preferring the best score.

    IEDB returns every window of every submitted sequence, so a short peptide
    can appear several times (different start offsets).  Binding rows keep the
    lowest percentile rank; processing rows keep the highest total score.
    """
    best: dict[tuple[str, str, str], dict] = {}
    for row in predictions:
        key = (str(row.get("peptide", "")), str(row.get("allele", "")),
               str(row.get("method", "")))
        held = best.get(key)
        if held is None:
            best[key] = row
            continue
        if str(row.get("method", "")) == "processing":
            new_value = row.get("total_score")
            old_value = held.get("total_score")
            if new_value is not None and (old_value is None or float(new_value) > float(old_value)):
                best[key] = row
            continue
        new_rank = row.get("percentile_rank")
        old_rank = held.get("percentile_rank")
        if new_rank is not None and (old_rank is None or float(new_rank) < float(old_rank)):
            best[key] = row
    return list(best.values())


# 中文备注：肽预测：聚合aggregate（参数：candidates、predictions）
def aggregate(candidates: Sequence[dict], predictions: Sequence[dict]) -> list[dict[str, object]]:
    """Collapse long-form predictions into one row per peptide."""
    by_peptide: dict[str, list[dict]] = {}
    for row in predictions:
        by_peptide.setdefault(str(row["peptide"]), []).append(row)

    rows: list[dict[str, object]] = []
    for candidate in candidates:
        peptide = str(candidate["peptide"])
        rows_for = by_peptide.get(peptide, [])
        binding = [row for row in rows_for if row.get("mhc_class") == 1
                   and row.get("percentile_rank") is not None]
        class2 = [row for row in rows_for if row.get("mhc_class") == 2
                  and row.get("percentile_rank") is not None]
        processing = [row for row in rows_for if row.get("method") == "processing"]
        best = _best(binding, "percentile_rank")
        best_class2 = _best(class2, "percentile_rank")
        # A higher processing total score means a better-processed peptide.
        best_processing = _best(processing, "total_score", maximize=True)
        ranked_by = best or best_class2
        merged = dict(candidate)
        merged.update({
            "best_allele": ranked_by["allele"] if ranked_by else "",
            "percentile_rank": ranked_by["percentile_rank"] if ranked_by else None,
            "mhc_method": ranked_by.get("method_label", "") if ranked_by else "",
            "mhc_class2_allele": best_class2["allele"] if best_class2 else "",
            "mhc_class2_percentile": best_class2["percentile_rank"] if best_class2 else None,
            "processing_total_score": best_processing.get("total_score") if best_processing else None,
            "processing_allele": best_processing["allele"] if best_processing else "",
        })
        rows.append(merged)
    return rows


def annotate_properties(rows: Sequence[dict]) -> list[dict[str, object]]:
    """为每条候选合并本地理化特征（分子量、pI、GRAVY 等），纯离线计算。"""
    annotated = []
    for row in rows:
        info = properties.describe(str(row["peptide"]))
        annotated.append({**row, **{key: value for key, value in info.items() if key != "peptide"}})
    return annotated


# ----------------------------------------------------------------------
# Output helpers
# ----------------------------------------------------------------------
def _write_tsv(path: Path, rows: Sequence[dict], preferred: Sequence[str],
               *, allow_extra: bool = False) -> None:
    """按首选列顺序写出 UTF-8 制表符表格；可选追加未列出的标量字段。"""
    keys: list[str] = list(preferred)
    if allow_extra:
        for row in rows:
            for key in row:
                if key not in keys and not isinstance(row.get(key), (dict, list)):
                    keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _format(row.get(key)) for key in keys})


def _format(value: object) -> object:
    """把单元格值格式化为写入 TSV 的文本（布尔转 yes/no、浮点保留 6 位有效数字）。"""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (list, tuple)):
        return ";".join(str(_format(item)) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else value


def _prediction_rows(predictions: Sequence[dict]) -> list[dict[str, object]]:
    """把预测记录中的原始行转成 JSON 字符串（截断到 2000 字符）以便落表。"""
    rows = []
    for row in predictions:
        item = {key: value for key, value in row.items() if key != "raw"}
        item["raw_json"] = json.dumps(row.get("raw", {}), ensure_ascii=False)[:2000]
        rows.append(item)
    return rows


def _summary_markdown(manifest: dict, ranked: Sequence[dict]) -> str:
    """生成 summary.md 的 Markdown 文本：运行信息、前 10 名表格与局限性。"""
    lines = [
        "# 候选肽预测摘要",
        "",
        f"- 生成时间：{manifest['created_at']}",
        f"- 输入候选肽：{manifest['candidate_count']} 条",
        f"- 预测方式：{manifest['prediction_summary']['method_labels'] or '未执行'}",
        f"- 证据分层：{json.dumps(manifest['prediction_summary']['tiers'], ensure_ascii=False)}",
        "",
        "## 排名前 10 的候选肽",
        "",
        "| rank | peptide | length | gene | allele | percentile | tier | score |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in ranked[:10]:
        lines.append(
            "| {rank} | {peptide} | {length} | {gene} | {allele} | {pct} | {tier} | {score} |".format(
                rank=row.get("rank", ""), peptide=row.get("peptide", ""),
                length=row.get("length", ""),
                gene=row.get("gene_symbol") or row.get("gene_id") or "",
                allele=row.get("best_allele") or "",
                pct=("" if row.get("percentile_rank") is None else row["percentile_rank"]),
                tier=row.get("evidence_tier", ""), score=row.get("composite_score", ""),
            )
        )
    lines += ["", "## 局限性", ""]
    lines += [f"- {item}" for item in manifest["limitations"]]
    lines += ["", "> 本表用于候选排序，不能证明抗原呈递、免疫原性或临床有效性。", ""]
    return "\n".join(lines)


# ----------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------
# 中文备注：肽预测：执行run（参数：output_dir、input_dir、cds_table、peptides）
def run(*, output_dir: str | Path,
        input_dir: str | Path | None = None,
        cds_table: str | Path | None = None,
        peptides: str | Path | Sequence[str] | None = None,
        options: PeptideOptions | None = None,
        client: IedbClient | None = None) -> dict[str, object]:
    """Run candidate generation, prediction, filtering, ranking and output."""
    options = options or PeptideOptions()
    options.validate()
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)

    skipped: list[dict[str, object]] = []
    inputs: dict[str, object] = {}
    if peptides is not None and cds_table is not None:
        raise ValueError("provide either peptides or a CDS table, not both")

    if cds_table is not None:
        if input_dir is None:
            raise ValueError("input_dir is required together with cds_table")
        result = candidates_from_cds(input_dir, cds_table, lengths=options.lengths,
                                     class2_window=options.class2_window)
        candidates = result["candidates"]
        skipped = list(result["skipped"])
        inputs = {
            "mode": "cds_table",
            "input_dir": str(Path(input_dir).resolve()),
            "cds_table": str(Path(cds_table).resolve()),
            "cds_table_sha256": file_sha256(cds_table),
            "event_count": result["events"],
        }
    elif peptides is not None:
        if isinstance(peptides, (str, Path)):
            rows = load_peptide_table(peptides)
            inputs = {"mode": "peptide_table", "peptide_table": str(Path(peptides).resolve()),
                      "peptide_table_sha256": file_sha256(peptides)}
        else:
            rows = [{"peptide": normalize_peptide(item)} for item in peptides]
            inputs = {"mode": "peptide_list", "count": len(rows)}
        candidates = []
        for row in rows:
            peptide = normalize_peptide(str(row["peptide"]))
            length = len(peptide)
            # Peptide-table mode accepts any IEDB-compatible length (8-30 aa):
            # MHC-II peptides are naturally 13-25 aa and must not be dropped
            # by the class-I default length tuple.
            if not 8 <= length <= 30:
                skipped.append({"peptide": peptide,
                                "reason": f"length {length} outside the supported 8-30 aa range"})
                continue
            context = str(row.get("class2_context") or "")
            candidates.append({
                **row,
                "peptide": peptide,
                "length": length,
                "start_aa": row.get("start_aa") or 1,
                "junction_aa": row.get("junction_aa") or "",
                "class2_context": context or peptide,
                "orf_source": row.get("orf_source") or "external",
            })
    else:
        raise ValueError("provide peptides or a CDS table")

    # Deduplicate identical peptide/event pairs while preserving order.
    seen: set[tuple[str, str]] = set()
    unique_candidates = []
    for candidate in candidates:
        key = (str(candidate["peptide"]), str(candidate.get("event_id", "")))
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)
    candidates = unique_candidates

    novelty: dict[str, object] = {"input_count": len(candidates), "novel_count": 0,
                                  "shared_count": 0, "databases": [], "limitations": []}
    if options.self_fastas:
        scan: SelfFilterResult = scan_proteomes([str(item["peptide"]) for item in candidates],
                                                options.self_fastas)
        candidates = [{**item, **scan.annotate(str(item["peptide"]))} for item in candidates]
        novelty = {**scan.as_dict(), "peptides": None}
    else:
        candidates = [{**item, **{"self_hit": None, "self_hit_proteins": "",
                                  "self_hit_count": None,
                                  "novelty_status": "not_evaluated"}} for item in candidates]
        novelty["limitations"] = ["未提供正常蛋白 FASTA，未执行 self/novelty 过滤。"]

    candidates = annotate_properties(candidates)

    alleles = parse_panel(options.alleles, allow_mixed_classes=True) if options.alleles else []
    if alleles and options.predictor != "none":
        grouped_for_limit = split_by_class(alleles)
        class1_peptides = {str(item["peptide"]) for item in candidates
                           if 8 <= int(item["length"]) <= 11}
        class2_contexts = {str(item["class2_context"]) for item in candidates
                           if len(str(item.get("class2_context") or "")) >= 11}
        estimated = (len(class1_peptides) * len(grouped_for_limit[1])
                     + len(class2_contexts) * len(grouped_for_limit[2]))
        if options.processing:
            estimated += len(class1_peptides) * len(grouped_for_limit[1])
        if estimated > options.max_predictions:
            raise ValueError(
                f"estimation of {estimated} peptide-HLA predictions exceeds "
                f"max_predictions={options.max_predictions}; narrow the input, "
                "the allele panel, or raise the cap explicitly"
            )
    prediction_result: dict[str, object] = {"predictions": [], "errors": [],
                                            "methods": {}, "calls": []}
    if options.predictor != "none" and alleles:
        if options.predictor == "local":
            prediction_result = _run_local(candidates, alleles)
        elif options.predictor == "auto":
            prediction_result = _run_local(candidates, alleles)
            if not prediction_result["predictions"]:
                prediction_result = (_run_iedb(candidates, alleles, options) if client is None
                                     else _run_iedb_with(client, candidates, alleles, options))
        else:
            prediction_result = (_run_iedb(candidates, alleles, options) if client is None
                                 else _run_iedb_with(client, candidates, alleles, options))
    predictions = dedupe_predictions(prediction_result["predictions"])

    aggregated = aggregate(candidates, predictions)
    ranked = rank_rows(aggregated, weights=DEFAULT_WEIGHTS)

    epitopes: list[dict[str, object]] = []
    if options.lookup_epitopes and predictions and alleles:
        lookup_client = client or _client(options)
        try:
            found = lookup_client.lookup_epitopes(
                [str(item["peptide"]) for item in ranked[:options.max_lookup]])
            for peptide, hits in found.items():
                for hit in hits:
                    epitopes.append({"candidate_peptide": peptide, **hit})
        except IedbError as error:
            prediction_result["errors"].append({"stage": "epitope_lookup", "error": str(error)[:500]})

    tiers: dict[str, int] = {}
    for row in ranked:
        tiers[str(row["evidence_tier"])] = tiers.get(str(row["evidence_tier"]), 0) + 1

    manifest = {
        "created_at": _now(),
        "inputs": inputs,
        "options": options.as_dict(),
        "candidate_count": len(candidates),
        "skipped": skipped[:200],
        "skipped_count": len(skipped),
        "novelty": {key: value for key, value in novelty.items() if key != "peptides"},
        "prediction_summary": {
            "method_labels": sorted({row.get("method_label", "") for row in predictions
                                     if row.get("method_label")}),
            "prediction_count": len(predictions),
            "error_count": len(prediction_result["errors"]),
            "errors": prediction_result["errors"][:50],
            "tiers": tiers,
            "request_ids": sorted({row.get("request_id", "") for row in predictions
                                   if row.get("request_id")}),
            "alleles": [item.as_dict() for item in alleles],
        },
        "references": None,
        "scoring": describe_scoring(),
        "limitations": list(LIMITATIONS),
    }
    try:
        from . import reference

        manifest["references"] = reference.summary().as_dict()
    except Exception:  # noqa: BLE001 - reference bundle is optional
        manifest["references"] = None

    _write_tsv(target / "splice_peptides.tsv", candidates, PEPTIDE_FIELDS)
    _write_tsv(target / "mhc_predictions.tsv", _prediction_rows(predictions), PREDICTION_FIELDS)
    _write_tsv(target / "ranked_candidates.tsv", ranked, RANKED_FIELDS)
    if epitopes:
        _write_tsv(target / "epitope_matches.tsv", epitopes,
                   ["candidate_peptide", "mhc_class", "mhc_restriction",
                    "qualitative_measure", "assay", "source_organism", "antigen", "pubmed_id"])
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    (target / "summary.md").write_text(_summary_markdown(manifest, ranked), encoding="utf-8")
    return {
        "output_dir": str(target),
        "candidate_count": len(candidates),
        "prediction_count": len(predictions),
        "ranked_count": len(ranked),
        "tiers": tiers,
        "errors": prediction_result["errors"],
        "files": [path.name for path in sorted(target.iterdir()) if path.is_file()],
        "manifest": manifest,
    }


def _run_iedb_with(client: IedbClient, candidates: Sequence[dict],
                   alleles: Sequence[HlaAllele], options: PeptideOptions, *,
                   class2_length: int | str | None = None) -> dict[str, object]:
    """Same as :func:`_run_iedb` but reusing an injected client (tests/API).

    ``class2_length`` 语义同 :func:`_run_iedb`；默认沿用 CDS 窗口长度。
    """
    grouped = split_by_class(list(alleles))
    predictions: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    methods_used: dict[int, str] = {}
    class1 = unique([str(item["peptide"]) for item in candidates if 8 <= int(item["length"]) <= 11])
    class1_alleles = [item.name for item in grouped[1]]
    class2_alleles = [item.name for item in grouped[2]]
    contexts, short_contexts = _class2_contexts(candidates)

    def attempt(label: str, func, *args, **kwargs) -> None:
        """执行一个预测阶段，把 IedbError 记入 errors 而不中断整体流程。"""
        try:
            predictions.extend(func(*args, **kwargs))
        except IedbError as error:
            errors.append({"stage": label, "error": str(error)[:500]})

    if options.mhc_class in {"class1", "both"} and class1_alleles and class1:
        method = options.methods.get(1, DEFAULT_METHODS[1])
        methods_used[1] = method
        attempt("mhc_i_binding", client.predict_mhci, class1, class1_alleles,
                lengths=options.lengths, method=method)
        if options.processing:
            attempt("mhc_i_processing", client.predict_processing, class1,
                    class1_alleles, lengths=options.lengths)
    if options.mhc_class in {"class2", "both"} and class2_alleles and contexts:
        method = options.methods.get(2, DEFAULT_METHODS[2])
        methods_used[2] = method
        attempt("mhc_ii_binding", client.predict_mhcii, contexts, class2_alleles,
                length=class2_length if class2_length is not None else options.class2_window,
                method=method)
    if short_contexts and options.mhc_class in {"class2", "both"}:
        errors.append({"stage": "mhc_ii_binding",
                       "error": f"{short_contexts} 条候选的 MHC-II 上下文短于 11 aa，未提交 II 类预测"})
    return {"predictions": predictions, "errors": errors, "methods": methods_used,
            "calls": list(client.calls)}


def predict_peptides(peptides: Sequence[str], alleles: Sequence[str], *,
                     mhc_class: str = "class1", predictor: str = "iedb",
                     processing: bool | None = None) -> dict[str, object]:
    """Predict a bare peptide list without writing files (API convenience).

    与 CDS/CLI 模式不同，这里的每条序列就是用户提交的肽本身，MHC-II 必须用
    ``length="asis"`` 提交：否则 IEDB 会把长肽切成固定长度窗口，返回的 peptide
    不再等于提交序列，在 :meth:`IedbClient._binding_records` 的精确序列过滤中
    被全部丢弃，表现为「预测完成，0 条」且无任何错误。长度/型别不匹配的输入
    一律写入 ``errors``，不再静默返回空结果。
    """
    options = PeptideOptions(
        alleles=list(alleles),
        mhc_class=mhc_class,
        predictor=predictor,
        processing=True if processing is None else processing,
        lookup_epitopes=False,
    )
    options.validate()
    cleaned = [normalize_peptide(item) for item in peptides]
    candidates = [{"peptide": peptide, "length": len(peptide),
                   "class2_context": peptide} for peptide in cleaned]
    parsed = parse_panel(options.alleles, allow_mixed_classes=True)
    grouped = split_by_class(list(parsed))

    if predictor == "none":
        result: dict[str, object] = {"predictions": [], "errors": [], "methods": {}, "calls": []}
    elif predictor == "local":
        from . import local_models

        if not local_models.available():
            raise ValueError(
                "本地预测器 MHCflurry 未安装，无法完成预测。请改用「IEDB（在线）」或 auto，"
                "或在本机执行 pip install mhcflurry 后重试。"
            )
        result = _run_local(candidates, parsed)
    elif predictor == "auto":
        from . import local_models

        # auto 按界面文案执行：本地模型可用且只做 I 类时优先离线，失败再回退 IEDB。
        if options.mhc_class == "class1" and local_models.available():
            local_result = _run_local(candidates, parsed)
            result = (local_result if not local_result["errors"]
                      else _run_iedb(candidates, parsed, options, class2_length="asis"))
        else:
            result = _run_iedb(candidates, parsed, options, class2_length="asis")
    else:
        result = _run_iedb(candidates, parsed, options, class2_length="asis")

    notes: list[dict[str, object]] = []
    if options.mhc_class == "class1":
        too_long = [item for item in cleaned if len(item) > 11]
        if too_long:
            notes.append({"stage": "input_length", "error": (
                f"{len(too_long)} 条肽长于 11 aa（MHC-I 只支持 8–11 aa），未提交结合预测；"
                "长肽请把「MHC 类别」改成 class2 或 both。例：" + "、".join(too_long[:3])
            )})
    if options.mhc_class in {"class2", "both"} and not grouped[2] and any(
            len(item) >= 11 for item in cleaned):
        notes.append({"stage": "alleles", "error": (
            "未检测到 MHC-II 型别（如 HLA-DRB1*15:01），长肽无法做 II 类预测；"
            "请填写 HLA-II 等位基因，或改选 class1 并只提交 8–11 aa 的肽。"
        )})

    predictions = dedupe_predictions(result["predictions"])
    for row in predictions:
        if isinstance(row.get("raw"), dict):
            row["raw"] = {key: row["raw"][key] for key in list(row["raw"])[:12]}
    return {
        "predictions": predictions,
        "errors": list(result["errors"]) + notes,
        "methods": {str(key): METHODS[value].label if value in METHODS else value
                    for key, value in result["methods"].items()},
    }
