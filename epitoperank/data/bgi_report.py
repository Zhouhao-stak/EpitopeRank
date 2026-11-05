"""Adapter for BGI RNAref per-sample rMATS text exports (.xls).

These exports contain PSI observations, not differential tests. No p-value or
FDR is inferred from the single-sample NA columns.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from epitoperank.splicing.schema import CORE_EVENT_FIELDS, QUALITY_EVENT_FIELDS

NAME = re.compile(r"^(?P<sample>.+)\.(?P<kind>SE|MXE|A3SS|A5SS|RI)\.xls$")
KINDS = {"SE", "MXE", "A3SS", "A5SS", "RI"}


def discover(directory: Path) -> list[tuple[Path, str, str]]:
    """扫描目录下的 BGI rMATS 逐样本导出文件（<样本>.<类型>.xls），校验关键表头后返回 (路径, 样本名, 事件类型) 列表。"""
    found = []
    for path in directory.rglob("*.xls"):
        match = NAME.fullmatch(path.name)
        # Browser uploads flatten selected files into one staging directory.
        # Direct report folders keep one directory per sample.
        if not match or (path.parent != directory and path.parent.name != match["sample"]):
            continue
        try:
            with path.open(encoding="utf-8-sig") as handle:
                headers = next(csv.reader(handle, delimiter="\t"))
        except (OSError, UnicodeError, StopIteration):
            continue
        if {"gene_id", "as_chr", "as_strand", f"as_inclevel1_{match['sample']}"} <= set(headers):
            found.append((path, match["sample"], match["kind"]))
    return sorted(found, key=lambda item: (item[1], item[2]))


def preview(directory: Path, *, enhancer: Any = None) -> dict[str, Any] | None:
    """导入前预览 BGI 逐样本目录：汇总样本与事件类型分布，生成映射、质量提示与前端展示字段；未发现文件时返回 None。"""
    files = discover(directory)
    if not files:
        return None
    samples = sorted({sample for _, sample, _ in files})
    counts = Counter(kind for _, _, kind in files)
    llm = {"attempted": False, "used": False, "errors": []}
    note = "检测到逐样本 rMATS PSI；缺少组间检验和生物学分组。"
    if enhancer is not None and getattr(enhancer, "has", lambda _: False)("ingest"):
        llm["attempted"] = True
        try:
            path, sample, kind = files[0]
            with path.open(encoding="utf-8-sig") as handle:
                rows = list(csv.reader(handle, delimiter="\t"))[:4]
            answer = enhancer.json(
                system="Identify this table type from headers and three example rows. Return JSON with one short 'note' in Chinese. Never infer biological groups, p-values, FDR, or differential significance.",
                user=json.dumps({"filename": path.name, "kind": kind, "headers": rows[0], "example_rows": rows[1:]}, ensure_ascii=False),
                feature="ingest", max_tokens=160, temperature=0.0, timeout=30,
            )
            if isinstance(answer, Mapping) and isinstance(answer.get("note"), str):
                note = answer["note"][:300]
                llm["used"] = True
        except Exception as exc:  # advisory only
            llm["errors"].append({"error": str(exc)[:200]})
    return {
        "status": "bgi_single_sample", "native": False, "sample_ids": samples,
        "mapping": {"adapter": "bgi_single_sample", "sample_groups": {s: "" for s in samples}},
        "mapping_source": "llm+heuristic" if llm["used"] else "heuristic",
        "group_suggestion_source": "none", "llm": llm,
        "preview": {"valid_events": "待转换", "sample_count": len(samples), "fdr_coverage": 0,
                    "delta_coverage": 0, "sample_psi_columns": len(samples), "event_types": dict(counts)},
        "issues": [{"severity": "warning", "code": "single_sample_only", "message": note,
                    "message_en": "Per-sample PSI only; no differential test or biological groups."}],
        "files_count": len(files),
        "privacy": "模型只接收一个代表文件的列名和最多三行样例。",
        "privacy_en": "The model receives headers and at most three rows from one representative file.",
        "agent_trace": [{"step": "profile", "status": "ok", "detail": f"识别 {len(files)} 个逐样本剪接表。",
                         "detail_en": f"Found {len(files)} per-sample splicing tables."}],
    }


def _psi(value: str) -> float | None:
    """把 PSI 单元格解析为浮点数，仅接受 [0, 1] 区间，非法值返回 None。"""
    try:
        number = float(value)
        return number if 0 <= number <= 1 else None
    except (TypeError, ValueError):
        return None


def apply(directory: Path, mapping: Mapping[str, Any], output_dir: Path | None = None) -> dict[str, Any]:
    """按样本分组把 BGI 逐样本 rMATS 表合并为标准格式（事件主表、样本元数据、映射 JSON），返回输出目录与事件统计。"""
    files = discover(directory)
    if not files:
        raise ValueError("No BGI per-sample rMATS tables found")
    samples = sorted({sample for _, sample, _ in files})
    groups = mapping.get("sample_groups")
    if not isinstance(groups, Mapping) or set(groups) != set(samples):
        raise ValueError("Provide a biological group for every observed sample")
    groups = {sample: str(groups[sample]).strip() for sample in samples}
    labels = sorted(set(groups.values()))
    if len(labels) != 2 or not all(groups.values()) or any(len(label) > 80 for label in labels):
        raise ValueError("Assign every sample to exactly two non-empty biological groups")
    target = output_dir or directory / "standardized"
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as scratch:
        db = sqlite3.connect(str(Path(scratch) / "events.sqlite"))
        db.execute("CREATE TABLE events (id TEXT PRIMARY KEY, gene_id TEXT, symbol TEXT, kind TEXT, chrom TEXT, strand TEXT, coords TEXT)")
        db.execute("CREATE TABLE psi (id TEXT, sample TEXT, value REAL, PRIMARY KEY(id,sample))")
        observed = 0
        for path, sample, kind in files:
            with path.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle, delimiter="\t"):
                    value = _psi(row.get(f"as_inclevel1_{sample}", ""))
                    if value is None:
                        continue
                    coords = [(key, row[key]) for key in row if key.startswith("as_") and ("start" in key or "end" in key or key.endswith("es") or key.endswith("ee"))]
                    if not coords or not row.get("as_chr"):
                        continue
                    identity = [kind, row.get("gene_id", ""), row["as_chr"], row.get("as_strand", ""), coords]
                    event_id = kind + ":" + hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]
                    coord_text = row["as_chr"] + ":" + ",".join(f"{key}={val}" for key, val in coords)
                    db.execute("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?)", (event_id, row.get("gene_id", ""), row.get("gene_symbol", ""), kind, row["as_chr"], row.get("as_strand", ""), coord_text))
                    db.execute("INSERT OR REPLACE INTO psi VALUES (?,?,?)", (event_id, sample, value))
                    observed += 1
            db.commit()
        fields = list(CORE_EVENT_FIELDS) + list(QUALITY_EVENT_FIELDS) + ["PSI_" + sample for sample in samples]
        event_path = target / "AS_event_master.tsv"
        with event_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
            writer.writeheader()
            cursor = db.execute("SELECT e.*, p.sample, p.value FROM events e JOIN psi p ON e.id=p.id ORDER BY e.id")
            current = None
            row_out: dict[str, Any] = {}
            values: dict[str, float] = {}
            event_count = 0
            def flush() -> None:
                """把当前事件累积的各样本 PSI 汇总成一行写入主表，含两组均值、ΔPSI 与缺失率。"""
                nonlocal event_count
                if current is None:
                    return
                for sample, value in values.items():
                    row_out["PSI_" + sample] = value
                means = {label: [v for s, v in values.items() if groups[s] == label] for label in labels}
                first = sum(means[labels[0]]) / len(means[labels[0]]) if means[labels[0]] else None
                second = sum(means[labels[1]]) / len(means[labels[1]]) if means[labels[1]] else None
                row_out.update(mean_PSI_group1=first, mean_PSI_group2=second,
                               delta_PSI=second - first if first is not None and second is not None else None,
                               valid_sample_count=len(values), psi_missing_rate=1-len(values)/len(samples))
                writer.writerow(row_out)
                event_count += 1
            for event_id, gene_id, symbol, kind, chrom, strand, coords, sample, value in cursor:
                if event_id != current:
                    flush()
                    current = event_id
                    values = {}
                    row_out = {"event_id": event_id, "gene_id": gene_id, "gene_symbol": symbol,
                               "event_type": kind, "chromosome": chrom, "strand": strand,
                               "genomic_coordinates": coords, "coordinate_system": "rMATS: start 0-based, end 1-based",
                               "source_tool": "BGI rMATS 4.1.2 single-sample"}
                values[sample] = value
            flush()
        with (target / "sample_metadata.tsv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(["sample_id", "group", "condition"])
            writer.writerows((sample, groups[sample], groups[sample]) for sample in samples)
        (target / "ingestion_mapping.json").write_text(json.dumps({"adapter": "bgi_single_sample", "source": str(directory), "groups": groups,
            "limitations": ["PSI comes from independent single-sample runs", "No differential p-values or FDR", "Group mean delta PSI is descriptive only"]}, ensure_ascii=False, indent=2), encoding="utf-8")
        db.close()
    return {"path": str(target), "preview": {"valid_events": event_count, "sample_count": len(samples),
            "observed_psi": observed, "groups": dict(Counter(groups.values())), "fdr_coverage": 0},
            "issues": [{"severity": "warning", "code": "exploratory_only", "message": "已计算描述性组均值与 ΔPSI；没有组间 p 值或 FDR，不能报告差异显著事件。"}]}
