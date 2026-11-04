#!/usr/bin/env python3
"""Build the self-contained peptide-prediction demo.

Two datasets are produced under ``examples/peptide_demo``:

``peptides.tsv``
    Real IEDB assay records (peptide + recorded HLA restriction + outcome),
    copied from the bundled reference extract.  Use it to exercise prediction
    and ranking without inventing any sequence.

``AS_event_master.tsv`` + ``splice_orfs.tsv``
    A **synthetic positive control**: the altered CDS encodes a real,
    well-studied epitope across the novel junction, while the reference CDS
    encodes a mutated version.  Event coordinates, gene names and PSI values
    are placeholders.  This exists only to exercise the splice→peptide path
    end to end; it is not biological data and must never be reported as a
    finding.

Usage::

    python examples/make_peptide_demo.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "epitoperank" / "peptide" / "reference" / "known_epitopes.tsv"
OUTPUT = ROOT / "examples" / "peptide_demo"

#: Human-preferred codons (a fixed, deterministic choice for the demo only).
CODONS = {
    "A": "GCC", "R": "AGG", "N": "AAC", "D": "GAC", "C": "TGC",
    "E": "GAG", "Q": "CAG", "G": "GGC", "H": "CAC", "I": "ATC",
    "L": "CTG", "K": "AAG", "M": "ATG", "F": "TTC", "P": "CCC",
    "S": "AGC", "T": "ACC", "W": "TGG", "Y": "TAC", "V": "GTG",
}
PREFIX = "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGP"
SUFFIX = "GTRVRAMAIYKKSEFVTEVVRRCPHHERCSDSDGLAPPQHLIRVEGNLRVEYLDDRNTFRHSVVVPYEPPEVGSDCTTIHYNYMCNSSCMGGMNRRPILTIITLEDSSGNLLGRNSFEVRVCACPGRDRRTEEENLRKKGEPHHELPPGSTKRALPNNTSSSPQPKKKPLDGEYFTLQIRGRERFEMFRELNEALELKDAQAGKEPGGSRAHSSHLKSKKGQSTSRHKKLMFKTEGPDSD"
CORE_EVENT_FIELDS = [
    "event_id", "gene_id", "gene_symbol", "event_type", "chromosome", "strand",
    "genomic_coordinates", "coordinate_system", "source_tool", "FDR", "delta_psi",
    "total_support_reads", "valid_sample_count",
]


def back_translate(protein: str) -> str:
    return "".join(CODONS[aa] for aa in protein) + "TAA"


def build_positive_controls(limit: int = 6, hla: str = "HLA-A*02:01") -> tuple[list[dict], list[dict]]:
    if not REFERENCE.is_file():
        raise SystemExit(f"reference extract missing: {REFERENCE} (run scripts/fetch_peptide_reference.py)")
    with REFERENCE.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    chosen: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        peptide = (row.get("peptide") or "").upper()
        restriction = (row.get("mhc_restriction") or "")
        if (row.get("mhc_class") != "I" or row.get("qualitative_measure") != "Positive"
                or len(peptide) != 9 or restriction != hla):
            continue
        if peptide in seen:
            continue
        seen.add(peptide)
        chosen.append(row)
        if len(chosen) >= limit:
            break
    if not chosen:
        raise SystemExit(f"no positive 9-mers for {hla} in the reference extract")

    events: list[dict] = []
    orfs: list[dict] = []
    for index, row in enumerate(chosen, start=1):
        peptide = row["peptide"].upper()
        # Reference protein: same length, two anchor residues mutated, so the
        # candidate peptide is genuinely absent from the reference ORF.
        reference_protein = peptide[:1] + "A" + peptide[2:-1] + "A"
        altered_protein = PREFIX + peptide + SUFFIX
        # Place the junction three nucleotides into the epitope so the peptide
        # crosses it and is retained by junction_peptides().
        junction_nt = len(PREFIX) * 3 + 3
        event_id = f"DEMO:SE:{index}"
        events.append({
            "event_id": event_id, "gene_id": f"DEMO{index}", "gene_symbol": f"DEMO_GENE_{index}",
            "event_type": "SE", "chromosome": "chr17", "strand": "+",
            "genomic_coordinates": f"chr17:{1_000_000 + index * 1000}-{1_000_000 + index * 1000 + 200}",
            "coordinate_system": "1-based-inclusive", "source_tool": "synthetic_positive_control",
            "FDR": "0.01", "delta_psi": "0.35", "total_support_reads": "120",
            "valid_sample_count": "6",
        })
        orfs.append({
            "event_id": event_id,
            "reference_cds": back_translate(reference_protein),
            "altered_cds": back_translate(altered_protein),
            "junction_nt": str(junction_nt),
            "orf_source": "synthetic_positive_control",
            "frame_status": "in_frame",
            "premature_stop": "no",
            "expected_epitope": peptide,
            "expected_hla": row.get("mhc_restriction", ""),
        })
    return events, orfs


def write_tsv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    events, orfs = build_positive_controls()
    write_tsv(OUTPUT / "AS_event_master.tsv", events, CORE_EVENT_FIELDS)
    write_tsv(OUTPUT / "splice_orfs.tsv", orfs,
              ["event_id", "reference_cds", "altered_cds", "junction_nt", "orf_source",
               "frame_status", "premature_stop", "expected_epitope", "expected_hla"])

    if REFERENCE.is_file():
        with REFERENCE.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        peptides = []
        seen: set[str] = set()
        for row in rows:
            peptide = (row.get("peptide") or "").upper()
            if not peptide or peptide in seen or row.get("mhc_class") != "I":
                continue
            if not (row.get("mhc_restriction") or "").startswith("HLA-"):
                continue
            seen.add(peptide)
            peptides.append({
                "peptide": peptide,
                "known_hla": row.get("mhc_restriction", ""),
                "known_outcome": row.get("qualitative_measure", ""),
                "source_organism": row.get("source_organism", ""),
                "pubmed_id": row.get("pubmed_id", ""),
            })
            if len(peptides) >= 200:
                break
        write_tsv(OUTPUT / "peptides.tsv", peptides,
                  ["peptide", "known_hla", "known_outcome", "source_organism", "pubmed_id"])

    (OUTPUT / "README.md").write_text(
        "# Peptide prediction demo\n\n"
        "- `peptides.tsv`: real IEDB assay records (peptide, recorded HLA restriction, "
        "recorded assay outcome). The assay outcome is **not** a binding benchmark.\n"
        "- `AS_event_master.tsv` + `splice_orfs.tsv`: a **synthetic positive control**. "
        "The altered CDS encodes a real epitope across a synthetic junction; reference "
        "CDS, coordinates, gene names and PSI values are placeholders. Do not interpret "
        "these events biologically.\n\n"
        "Run prediction only:\n\n"
        "```bash\n"
        "python run.py peptide --peptides examples/peptide_demo/peptides.tsv \\\n"
        "  --alleles HLA-A*02:01 --mhc-class class1 --out out/peptide_demo\n"
        "```\n\n"
        "Run the splice -> peptide path:\n\n"
        "```bash\n"
        "python run.py peptide --input examples/peptide_demo \\\n"
        "  --cds examples/peptide_demo/splice_orfs.tsv \\\n"
        "  --alleles HLA-A*02:01 --mhc-class class1 --out out/peptide_splice_demo\n"
        "```\n",
        encoding="utf-8",
    )
    print(f"wrote demo to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
