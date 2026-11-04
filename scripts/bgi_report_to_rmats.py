#!/usr/bin/env python3
"""Rebuild group-vs-group rMATS JC tables from a BGI RNAref report.

BGI ships one rMATS run *per sample* (``as_ijc_sample_2_NA``), so the report
holds per-sample inclusion levels but no between-group statistics. This script
unions the per-sample event tables, splits the samples with a user supplied
group table, and recomputes the group-level counts, PSI, p-value and FDR that
EpitopeRank's native rMATS parser expects.

    python scripts/bgi_report_to_rmats.py \
        --report "E:\\Report_F24A040009852_HUMkcvaT\\Report_F24A040009852_HUMkcvaT" \
        --groups groups.tsv --out out/bgi_rmats

``groups.tsv`` needs two columns (``sample_id``, ``group``); extra columns are
copied into the emitted ``sample_metadata.tsv``.

Statistics: the reported p-value is the *more conservative* of

* a pooled 2x2 chi-square on summed junction counts (the test EpitopeRank's own
  ``analysis.statistics`` implements), and
* a per-replicate Mann-Whitney U test on the sample-level PSI values,

because pooling counts across replicates hides within-group variance and would
otherwise call almost everything significant in a 100-sample cohort. FDR is
Benjamini-Hochberg within each event type, matching rMATS' convention.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from epitoperank.analysis.statistics import (  # noqa: E402
    benjamini_hochberg,
    chi_square_p_value,
)

EVENT_TYPES = ("SE", "A3SS", "A5SS", "MXE", "RI")

#: BGI column -> rMATS column, per event type. Coordinates use the rMATS names
#: because EpitopeRank rebuilds ``chr:start-end`` from them.
COORD_COLUMNS: dict[str, tuple[tuple[str, str], ...]] = {
    "SE": (
        ("as_exonstart_0base", "exonStart_0base"),
        ("as_exonend", "exonEnd"),
        ("as_upstreames", "upstreamES"),
        ("as_upstreamee", "upstreamEE"),
        ("as_downstreames", "downstreamES"),
        ("as_downstreamee", "downstreamEE"),
    ),
    "RI": (
        ("as_riexonstart_0base", "riExonStart_0Base"),
        ("as_riexonend", "riExonEnd"),
        ("as_upstreames", "upstreamES"),
        ("as_upstreamee", "upstreamEE"),
        ("as_downstreames", "downstreamES"),
        ("as_downstreamee", "downstreamEE"),
    ),
    "A3SS": (
        ("as_longexonstart_0base", "longExonStart_0base"),
        ("as_longexonend", "longExonEnd"),
        ("as_shortes", "shortExonStart_0base"),
        ("as_shortee", "shortExonEnd"),
        ("as_flankinges", "flankingES"),
        ("as_flankingee", "flankingEE"),
    ),
    "A5SS": (
        ("as_longexonstart_0base", "longExonStart_0base"),
        ("as_longexonend", "longExonEnd"),
        ("as_shortes", "shortExonStart_0base"),
        ("as_shortee", "shortExonEnd"),
        ("as_flankinges", "flankingES"),
        ("as_flankingee", "flankingEE"),
    ),
    "MXE": (
        ("as_1stexonstart_0base", "1stExonStart_0base"),
        ("as_1stexonend", "1stExonEnd"),
        ("as_2ndexonstart_0base", "2ndExonStart_0base"),
        ("as_2ndexonend", "2ndExonEnd"),
        ("as_upstreames", "upstreamES"),
        ("as_upstreamee", "upstreamEE"),
        ("as_downstreames", "downstreamES"),
        ("as_downstreamee", "downstreamEE"),
    ),
}


def find_as_directory(report: Path) -> Path:
    """Locate the per-sample alternative-splicing directory inside a report."""
    for candidate in [report, *sorted(report.rglob("Alternative_splicing"))]:
        if not candidate.is_dir():
            continue
        for child in sorted(candidate.iterdir()):
            if child.is_dir() and (child / f"{child.name}.SE.xls").is_file():
                return candidate
    raise FileNotFoundError(f"Cannot locate per-sample AS tables under {report}")


def read_groups(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    """Read ``sample_id``/``group`` plus any extra columns from a group table."""
    delimiter = "," if path.suffix.lower() == ".csv" else "\t"
    order: list[str] = []
    rows: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle, delimiter=delimiter):
            sample_id = str(raw.get("sample_id") or raw.get("Sample_ID") or "").strip()
            group = str(raw.get("group") or raw.get("Group") or raw.get("condition") or "").strip()
            if not sample_id or not group:
                continue
            if sample_id in rows:
                raise ValueError(f"duplicate sample_id in group table: {sample_id}")
            order.append(sample_id)
            rows[sample_id] = {k: (v or "").strip() for k, v in raw.items() if k}
    if len(order) < 2:
        raise ValueError("group table needs at least two samples")
    return order, rows


def sample_directories(as_dir: Path) -> list[str]:
    return sorted(p.name for p in as_dir.iterdir() if p.is_dir())


def event_table(as_dir: Path, sample: str, event_type: str) -> Path:
    return as_dir / sample / f"{sample}.{event_type}.xls"


def scan_counts(
    as_dir: Path,
    samples: list[str],
    event_type: str,
) -> tuple[dict[str, int], dict[str, int], int]:
    """Pass 1: per-event number of samples carrying it and pooled junction reads."""
    seen: dict[str, int] = defaultdict(int)
    reads: dict[str, int] = defaultdict(int)
    coord_names = [bgi for bgi, _ in COORD_COLUMNS[event_type]]
    rows = 0
    for sample in samples:
        path = event_table(as_dir, sample, event_type)
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8", newline="") as handle:
            header = handle.readline().rstrip("\n").split("\t")
            index = {name: i for i, name in enumerate(header)}
            missing = [name for name in coord_names if name not in index]
            if missing:
                raise KeyError(f"{path.name}: missing columns {missing}")
            coord_idx = [index[name] for name in coord_names]
            strand_idx = index["as_strand"]
            ijc_idx = index[f"as_ijc_sample_1_{sample}"]
            sjc_idx = index[f"as_sjc_sample_1_{sample}"]
            width = max(max(coord_idx), strand_idx, ijc_idx, sjc_idx) + 1
            for line in handle:
                fields = line.rstrip("\n").split("\t")
                if len(fields) < width:
                    continue
                rows += 1
                key = "\x1f".join((fields[strand_idx], *(fields[i] for i in coord_idx)))
                seen[key] += 1
                try:
                    reads[key] += int(fields[ijc_idx]) + int(fields[sjc_idx])
                except ValueError:
                    pass
    return seen, reads, rows


def _pick(index: dict[str, int], *names: str) -> str:
    """Return the first present column name (BGI drops the ``as_`` prefix on IDs)."""
    for name in names:
        if name in index:
            return name
    raise KeyError(f"none of {names} present; columns: {sorted(index)[:8]}")


def collect_events(
    as_dir: Path,
    samples: list[str],
    event_type: str,
    keys: dict[str, int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, dict[str, str]]]:
    """Pass 2: fill per-sample inclusion / exclusion / PSI matrices for kept events."""
    count = len(samples)
    ijc = np.zeros((len(keys), count), dtype=np.int32)
    sjc = np.zeros((len(keys), count), dtype=np.int32)
    psi = np.full((len(keys), count), np.nan, dtype=np.float32)
    info: dict[str, dict[str, str]] = {}
    coord_pairs = COORD_COLUMNS[event_type]
    coord_names = [bgi for bgi, _ in coord_pairs]
    for column, sample in enumerate(samples):
        path = event_table(as_dir, sample, event_type)
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8", newline="") as handle:
            header = handle.readline().rstrip("\n").split("\t")
            index = {name: i for i, name in enumerate(header)}
            coord_idx = [index[name] for name in coord_names]
            strand_idx = index["as_strand"]
            gene_idx = index[_pick(index, "gene_id", "as_gene_id", "GeneID")]
            symbol_idx = index[_pick(index, "gene_symbol", "as_gene_symbol", "geneSymbol")]
            chr_idx = index[_pick(index, "as_chr", "chr")]
            ijc_idx = index[f"as_ijc_sample_1_{sample}"]
            sjc_idx = index[f"as_sjc_sample_1_{sample}"]
            psi_idx = index[f"as_inclevel1_{sample}"]
            width = max(max(coord_idx), strand_idx, gene_idx, symbol_idx, chr_idx, ijc_idx, sjc_idx, psi_idx) + 1
            for line in handle:
                fields = line.rstrip("\n").split("\t")
                if len(fields) < width:
                    continue
                key = "\x1f".join((fields[strand_idx], *(fields[i] for i in coord_idx)))
                row = keys.get(key)
                if row is None:
                    continue
                if key not in info:
                    info[key] = {
                        "gene_id": fields[gene_idx],
                        "gene_symbol": fields[symbol_idx].strip('"'),
                        "chr": fields[chr_idx],
                        "strand": fields[strand_idx],
                        **{rmats: fields[index[bgi]] for bgi, rmats in coord_pairs},
                    }
                try:
                    ijc[row, column] = int(fields[ijc_idx])
                    sjc[row, column] = int(fields[sjc_idx])
                except ValueError:
                    pass
                level = fields[psi_idx]
                if level not in ("", "NA", "nan"):
                    try:
                        psi[row, column] = float(level)
                    except ValueError:
                        pass
    return ijc, sjc, psi, info


def write_event_file(
    path: Path,
    event_type: str,
    keys: list[str],
    info: dict[str, dict[str, str]],
    ijc: np.ndarray,
    sjc: np.ndarray,
    psi: np.ndarray,
    group1_cols: list[int],
    group2_cols: list[int],
    min_group_samples: int,
    min_reads_per_sample: int,
    method: str,
) -> dict[str, int]:
    """Emit one rMATS-native JC table with recomputed group statistics."""
    coord_names = [rmats for _, rmats in COORD_COLUMNS[event_type]]
    header = ["ID", "GeneID", "geneSymbol", "chr", "strand", *coord_names,
              "IJC_SAMPLE_1", "SJC_SAMPLE_1", "IJC_SAMPLE_2", "SJC_SAMPLE_2",
              "IncLevel1", "IncLevel2", "PValue", "FDR"]

    def join(values: np.ndarray, fmt: str) -> str:
        return ",".join(fmt % value for value in values)

    p_values: list[float | None] = []
    rows: list[list[str]] = []
    deltas: list[float] = []
    tested = 0
    for position, key in enumerate(keys):
        meta = info.get(key)
        if meta is None:
            continue
        inclusion1 = ijc[position, group1_cols]
        exclusion1 = sjc[position, group1_cols]
        inclusion2 = ijc[position, group2_cols]
        exclusion2 = sjc[position, group2_cols]
        support1 = inclusion1 + exclusion1
        support2 = inclusion2 + exclusion2
        strong1 = int((support1 >= min_reads_per_sample).sum())
        strong2 = int((support2 >= min_reads_per_sample).sum())
        if strong1 < min_group_samples or strong2 < min_group_samples:
            continue
        psi1 = psi[position, group1_cols]
        psi2 = psi[position, group2_cols]
        psi1_valid = psi1[~np.isnan(psi1)]
        psi2_valid = psi2[~np.isnan(psi2)]
        pooled = chi_square_p_value(
            float(inclusion1.sum()), float(exclusion1.sum()),
            float(inclusion2.sum()), float(exclusion2.sum()),
        )
        replicate: float | None = None
        if method in ("max", "mwu"):
            if psi1_valid.size >= 3 and psi2_valid.size >= 3:
                try:
                    replicate = float(mannwhitneyu(psi1_valid, psi2_valid, alternative="two-sided").pvalue)
                except ValueError:
                    replicate = None
        if method == "chi2":
            p_value = pooled
        elif method == "mwu":
            # Fall back to the pooled test when a group has too few PSI values.
            p_value = replicate if replicate is not None else pooled
        else:
            candidates = [value for value in (pooled, replicate) if value is not None]
            p_value = max(candidates) if candidates else None
        tested += 1
        p_values.append(p_value)
        if psi1_valid.size and psi2_valid.size:
            deltas.append(float(psi2_valid.mean() - psi1_valid.mean()))
        rows.append([
            str(len(rows) + 1), meta["gene_id"], meta["gene_symbol"], meta["chr"], meta["strand"],
            *(meta[name] for name in coord_names),
            join(inclusion1, "%d"), join(exclusion1, "%d"),
            join(inclusion2, "%d"), join(exclusion2, "%d"),
            join(psi[position, group1_cols], "%.4f"), join(psi[position, group2_cols], "%.4f"),
        ])

    adjusted = benjamini_hochberg(p_values)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        for row, p_value, fdr in zip(rows, p_values, adjusted):
            writer.writerow([
                *row,
                "NA" if p_value is None else f"{float(p_value):.6g}",
                "NA" if fdr is None else f"{float(fdr):.6g}",
            ])

    return {
        "events_written": len(rows),
        "events_tested": tested,
        "median_abs_delta_psi": round(float(np.median(np.abs(deltas))), 4) if deltas else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", required=True, help="BGI report root directory")
    parser.add_argument("--groups", required=True, help="TSV/CSV with sample_id and group columns")
    parser.add_argument("--out", required=True, help="Output directory for the rMATS tables")
    parser.add_argument("--group-a", default=None, help="Label treated as group 1 (control side of dPSI)")
    parser.add_argument("--group-b", default=None, help="Label treated as group 2 (treatment side of dPSI)")
    parser.add_argument("--min-samples", type=int, default=30, help="Keep events carried by at least this many samples")
    parser.add_argument("--min-total-reads", type=int, default=10, help="Keep events with at least this many pooled junction reads")
    parser.add_argument("--min-group-samples", type=int, default=3, help="Require this many samples per group with >= --min-reads-per-sample reads")
    parser.add_argument("--min-reads-per-sample", type=int, default=10, help="Per-sample support threshold used by --min-group-samples")
    parser.add_argument(
        "--p-value-method",
        choices=("max", "mwu", "chi2"),
        default="max",
        help=(
            "max = larger of the pooled chi-square and the per-replicate Mann-Whitney p-value "
            "(default, conservative); mwu = replicate-level PSI test only (SUPPA2-like); "
            "chi2 = pooled junction-count test only (rMATS-like, optimistic in large cohorts)"
        ),
    )
    args = parser.parse_args(argv)

    report = Path(args.report).expanduser().resolve()
    groups_path = Path(args.groups).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    as_dir = find_as_directory(report)
    available = sample_directories(as_dir)
    order, rows = read_groups(groups_path)

    unknown = [sample for sample in order if sample not in available]
    if unknown:
        raise SystemExit(f"group table lists samples with no AS directory: {unknown[:10]}")
    unused = [sample for sample in available if sample not in rows]

    labels = sorted({row["group"] for row in rows.values()})
    if args.group_a or args.group_b:
        if not (args.group_a and args.group_b):
            raise SystemExit("--group-a and --group-b must be given together")
        group1_label, group2_label = args.group_a, args.group_b
        for label in (group1_label, group2_label):
            if label not in labels:
                raise SystemExit(f"unknown group label {label!r}; available: {labels}")
    else:
        if len(labels) != 2:
            raise SystemExit(
                f"found {len(labels)} group labels {labels}; EpitopeRank compares exactly two. "
                "Pick a pair with --group-a/--group-b."
            )
        group1_label, group2_label = labels
    group1 = sorted(s for s in order if rows[s]["group"] == group1_label)
    group2 = sorted(s for s in order if rows[s]["group"] == group2_label)
    if len(group1) < 2 or len(group2) < 2:
        raise SystemExit(f"each group needs >=2 samples (got {len(group1)} vs {len(group2)})")

    samples = [*group1, *group2]
    sample_column = {sample: i for i, sample in enumerate(samples)}
    group1_cols = [sample_column[s] for s in group1]
    group2_cols = [sample_column[s] for s in group2]

    # EpitopeRank's loader sorts group labels alphabetically: the first label is
    # group 1 and dPSI is group2 - group1, so the emitted metadata must agree.
    if sorted([group1_label, group2_label]) != [group1_label, group2_label]:
        group1, group2 = group2, group1
        group1_label, group2_label = group2_label, group1_label
        group1_cols, group2_cols = group2_cols, group1_cols
        samples = [*group1, *group2]
        sample_column = {sample: i for i, sample in enumerate(samples)}

    metadata_columns = ["sample_id", "group", "condition", "tissue", "batch"]
    extra_columns = sorted({k for row in rows.values() for k in row} - set(metadata_columns))
    with (out_dir / "sample_metadata.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(metadata_columns + extra_columns)
        for sample in samples:
            row = rows[sample]
            writer.writerow([
                sample,
                row["group"],
                row.get("condition") or row["group"],
                row.get("tissue", ""),
                row.get("batch", ""),
                *(row.get(column, "") for column in extra_columns),
            ])

    summary: dict[str, object] = {
        "report": str(report),
        "as_directory": str(as_dir),
        "group1": {"label": group1_label, "samples": group1},
        "group2": {"label": group2_label, "samples": group2},
        "samples_in_report_not_in_group_table": unused,
        "filters": {
            "min_samples": args.min_samples,
            "min_total_reads": args.min_total_reads,
            "min_group_samples": args.min_group_samples,
            "min_reads_per_sample": args.min_reads_per_sample,
            "p_value_method": args.p_value_method,
        },
        "delta_psi_direction": f"{group2_label} - {group1_label}",
        "event_types": {},
    }

    started = time.perf_counter()
    for event_type in EVENT_TYPES:
        phase = time.perf_counter()
        seen, reads, scanned = scan_counts(as_dir, samples, event_type)
        kept = {
            key: position
            for position, key in enumerate(
                sorted(k for k in seen if seen[k] >= args.min_samples and reads[k] >= args.min_total_reads)
            )
        }
        ijc, sjc, psi, info = collect_events(as_dir, samples, event_type, kept)
        keys = sorted(kept, key=lambda key: kept[key])
        target = out_dir / f"{event_type}.MATS.JC.txt"
        stats = write_event_file(
            target, event_type, keys, info, ijc, sjc, psi,
            group1_cols, group2_cols,
            args.min_group_samples, args.min_reads_per_sample,
            args.p_value_method,
        )
        stats.update({
            "rows_scanned": scanned,
            "union_events": len(seen),
            "events_after_coverage_filter": len(kept),
            "seconds": round(time.perf_counter() - phase, 1),
        })
        summary["event_types"][event_type] = stats
        print(
            f"[bgi->rmats] {event_type}: scanned {scanned:,} rows, union {len(seen):,}, "
            f"coverage-filtered {len(kept):,}, written {stats['events_written']:,}, "
            f"tested {stats['events_tested']:,} ({stats['seconds']}s)",
            flush=True,
        )

    summary["elapsed_seconds"] = round(time.perf_counter() - started, 1)
    summary["caveats"] = [
        "Source tables are single-sample rMATS runs (group 2 = NA); all group statistics here were recomputed locally.",
        f"p-value method = {args.p_value_method}: "
        + {
            "max": "the larger of the pooled junction-count chi-square and the per-replicate Mann-Whitney U test on PSI, so it is conservative but may miss real effects.",
            "mwu": "per-replicate Mann-Whitney U test on PSI only (SUPPA2-like); ignores junction read depth.",
            "chi2": "pooled junction-count chi-square only (rMATS-like); ignores replicate variance and is optimistic in large cohorts.",
        }[args.p_value_method],
        "Events are unioned by strand + rMATS coordinates, so an event absent from a sample contributes 0 junction reads for it.",
        "This is not a rerun of rMATS on the alignments; for publication-grade statistics ask the vendor to rerun rMATS group-vs-group from the BAM files.",
    ]
    (out_dir / "conversion_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"[bgi->rmats] wrote {out_dir}")
    print(f"[bgi->rmats] dPSI direction: {group2_label} - {group1_label}")
    if unused:
        print(f"[bgi->rmats] WARNING {len(unused)} report samples absent from the group table: {unused[:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
