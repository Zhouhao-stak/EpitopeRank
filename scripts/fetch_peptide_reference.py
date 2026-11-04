#!/usr/bin/env python3
"""Refresh the bundled peptide reference tables from public IEDB endpoints.

Usage::

    python scripts/fetch_peptide_reference.py
    python scripts/fetch_peptide_reference.py --epitopes-per-allele 100

The script writes, under ``epitoperank/peptide/reference``:

* ``hla_class1_alleles.tsv`` — allele names the IEDB MHC-I tools accept
* ``hla_class2_alleles.tsv`` — allele names the IEDB MHC-II tools accept
* ``known_epitopes.tsv``    — a real IEDB T-cell assay extract
* ``manifest.json``         — retrieval timestamp, URLs, row counts, sha256

It deliberately does **not** download population frequencies: those depend on
the cohort and must come from AFND/IEDB for the study population.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "epitoperank" / "peptide" / "reference"

TOOLS = "https://tools-cluster-interface.iedb.org/tools_api/"
QUERY = "https://query-api.iedb.org/"
UA = "EpitopeRank-reference-fetch/1.0"

#: Alleles sampled for the known-epitope extract (common, well-studied).
EPITOPE_ALLELES = [
    "HLA-A*01:01", "HLA-A*02:01", "HLA-A*03:01", "HLA-A*11:01",
    "HLA-A*24:02", "HLA-B*07:02", "HLA-B*08:01", "HLA-B*35:01",
    "HLA-B*44:02", "HLA-B*57:01", "HLA-DRB1*01:01", "HLA-DRB1*15:01",
]


def post(url: str, payload: dict[str, str], *, timeout: float = 120.0) -> str:
    body = urlencode(payload).encode()
    request = Request(url, data=body, method="POST",
                      headers={"Content-Type": "application/x-www-form-urlencoded",
                               "User-Agent": UA})
    with urlopen(request, timeout=timeout) as response:
        return response.read(8_000_000).decode("utf-8-sig", errors="replace")


def get_json(url: str, *, timeout: float = 90.0) -> object:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": UA})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read(8_000_000).decode("utf-8", errors="replace"))


def allele_rows(text: str, mhc_class: int, method: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("Available", "*", "http")):
            continue
        if line.startswith(("HLA-", "DPA1", "DPB1", "DQA1", "DQB1")):
            allele = line if line.startswith("HLA-") else "HLA-" + line
            rows.append({"allele": allele, "mhc_class": str(mhc_class), "source": method})
    return rows


def epitope_rows(alleles: list[str], per_allele: int) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    rows: list[dict[str, str]] = []
    for allele in alleles:
        url = (
            f"{QUERY}tcell_search?mhc_allele_name=eq.{quote(allele)}"
            f"&limit={per_allele}"
            "&select=tcell_id,linear_sequence,mhc_class,mhc_restriction,"
            "qualitative_measure,assay_description,source_organism_name,pubmed_id"
            f"&order=tcell_id.asc&offset=0"
        )
        try:
            payload = get_json(url)
        except Exception as error:  # noqa: BLE001 - keep going on one failing allele
            print(f"  ! {allele}: {error}", file=sys.stderr)
            continue
        for row in payload if isinstance(payload, list) else []:
            peptide = str(row.get("linear_sequence") or "").strip().upper()
            restriction = str(row.get("mhc_restriction") or allele).strip()
            if not peptide or not peptide.isalpha():
                continue
            key = (peptide, restriction, str(row.get("qualitative_measure") or ""))
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "peptide": peptide,
                "length": str(len(peptide)),
                "mhc_class": str(row.get("mhc_class") or ""),
                "mhc_restriction": restriction,
                "qualitative_measure": str(row.get("qualitative_measure") or ""),
                "assay": str(row.get("assay_description") or "").replace("<br/>", " ")[:300],
                "source_organism": str(row.get("source_organism_name") or ""),
                "pubmed_id": str(row.get("pubmed_id") or ""),
                "source": "IEDB query API",
            })
        print(f"  {allele}: {len(payload) if isinstance(payload, list) else 0} records")
        time.sleep(0.3)
    return rows


def write_tsv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("\t".join(fields) + "\n")
        for row in rows:
            handle.write("\t".join(str(row.get(field, "")).replace("\t", " ") for field in fields) + "\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epitopes-per-allele", type=int, default=150)
    parser.add_argument("--skip-epitopes", action="store_true")
    args = parser.parse_args(argv)

    output: Path = args.output
    retrieved = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest: dict[str, object] = {
        "retrieved_at": retrieved,
        "source": {"tools_api": TOOLS, "query_api": QUERY},
        "notes": [
            "Allele lists are the names accepted by the IEDB tools, not population frequencies.",
            "Known epitopes are an assay extract for demos/regression tests, not a curated neoantigen set.",
        ],
        "files": {},
    }

    print("Fetching class-I allele catalogue...")
    class1 = allele_rows(post(TOOLS + "mhci/", {"method": "netmhcpan_el-4.1", "species": "human"}),
                         1, "netmhcpan_el-4.1")
    print(f"  {len(class1)} alleles")
    manifest["files"]["hla_class1_alleles.tsv"] = {
        "rows": len(class1),
        "sha256": write_tsv(output / "hla_class1_alleles.tsv", class1,
                            ["allele", "mhc_class", "source"]),
    }

    print("Fetching class-II allele catalogue...")
    class2 = allele_rows(post(TOOLS + "mhcii/", {"method": "netmhciipan_el-4.1"}),
                         2, "netmhciipan_el-4.1")
    print(f"  {len(class2)} alleles")
    manifest["files"]["hla_class2_alleles.tsv"] = {
        "rows": len(class2),
        "sha256": write_tsv(output / "hla_class2_alleles.tsv", class2,
                            ["allele", "mhc_class", "source"]),
    }

    if not args.skip_epitopes:
        print("Fetching known-epitope assay extract...")
        epitopes = epitope_rows(EPITOPE_ALLELES, args.epitopes_per_allele)
        print(f"  {len(epitopes)} unique assay rows")
        manifest["files"]["known_epitopes.tsv"] = {
            "rows": len(epitopes),
            "sha256": write_tsv(output / "known_epitopes.tsv", epitopes,
                                ["peptide", "length", "mhc_class", "mhc_restriction",
                                 "qualitative_measure", "assay", "source_organism",
                                 "pubmed_id", "source"]),
            "alleles_sampled": EPITOPE_ALLELES,
            "records_per_allele": args.epitopes_per_allele,
        }

    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    print(f"Wrote reference tables to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
